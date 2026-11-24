"""ThorHub error identity: a 401/429 is the same for every credential — there is no
anonymous identity anymore, so no error may offer anonymous recovery (#111970, ThorHub era).

Replaces ``test_welcome_error_identity.py``: the welcome-tier classifier is deleted,
so the tests assert the ThorHub 401 diagnostics copy and that no welcome context
is ever emitted.
"""

from types import SimpleNamespace

import pytest

from agent.error_classifier import classify_api_error
from agent.error_surface import build_error_surface_from_result
from agent.turn_recovery import max_retries_exhausted_result, nonretryable_client_error_result

THORHUB = "https://llm.thormarket.site/v1"


def agent_for(key, base_url):
    return SimpleNamespace(
        provider="thor", api_key=key, base_url=base_url, model="deepseek-v4-pro",
        log_prefix="", _rate_limit_state=None, _has_pending_fallback=lambda: False,
        _dump_api_request_debug=lambda *a, **kw: None, _flush_status_buffer=lambda: None,
        _summarize_api_error=lambda e: str(e), _emit_status=lambda *a, **kw: None,
        _persist_session=lambda *a, **kw: None, _plines=lambda *a, **kw: None, _vprint=lambda *a, **kw: None,
        _buffer_status=lambda *a, **kw: None, _buffer_vprint=lambda *a, **kw: None,
        _emit_diagnostic_status=lambda *a, **kw: None, _buffer_diagnostic_status=lambda *a, **kw: None,
        _try_activate_fallback=lambda: False,
    )


@pytest.mark.parametrize("api_key", ["sk-thor-a", "sk-thor-x"],
                         ids=["key-a", "key-b"])
@pytest.mark.parametrize("base_url", [THORHUB])
@pytest.mark.parametrize("case", ["rate_limited", "model_not_free", "403"])
def test_thorhub_errors_do_not_offer_anonymous_recovery(api_key, base_url, case):
    """A shared fairshare body cannot establish anonymous identity: ThorHub has no free tier."""
    status = 403 if case == "403" else 429
    message = ("You tried to access something that you don't have permissions for." if case == "403"
               else "The service refused this request.")
    body = {"status": status, "message": message, "reason": case, "retry_after": 158}
    error = Exception(message)
    error.status_code, error.body = status, body
    agent = agent_for(api_key, base_url)
    classified = classify_api_error(error, provider="thor", model=agent.model, base_url=base_url, api_key=api_key)
    common = dict(api_kwargs=None, api_messages=[], messages=[], conversation_history=[],
                  api_call_count=1, approx_tokens=10, provider="thor", base_url=base_url, model=agent.model)
    if status == 403:
        result = nonretryable_client_error_result(agent, error, classified, status_code=status, **common)
    else:
        result = max_retries_exhausted_result(agent, error, classified, attempts=3,
                                             is_rate_limited=status == 429, error_msg=message, **common)
    assert "welcome_refusal" not in classified.error_context
    assert "welcome_route" not in classified.error_context
    assert "free_tier" not in result
    surface = build_error_surface_from_result(result, provider="thor", model=agent.model)
    assert surface["code"] == {403: "auth", 429: "rate_limit"}[status]
    assert "without signing in" not in result["final_response"]


def test_thorhub_401_diagnostics_name_the_key_and_topup(capsys, monkeypatch):
    """A ThorHub 401 prints the same copy for any credential: revoked key or out of credits."""
    import agent.conversation_loop as loop
    from agent.turn_recovery import _print_thorhub_401_diagnostics

    monkeypatch.setattr(loop, "_print_thorhub_entitlement_guidance", lambda *a: False)
    _print_thorhub_401_diagnostics(agent_for("sk-thor-x", THORHUB), Exception("unauthorized"))
    output = capsys.readouterr().out
    assert "ThorHub 401" in output
    assert "thor auth add thor" in output
    assert "https://llm.thormarket.site/beli/topup" in output
    assert "portal.thor-agent.local" not in output
    assert "Thor couldn't start a new one" not in output


def test_anonymous_claim_does_not_classify_other_providers_as_thorhub():
    error = Exception("refused")
    error.status_code = 429
    error.body = {"reason": "rate_limited", "retry_after": 600}
    classified = classify_api_error(error, provider="custom", api_key="sk-thor-x", base_url=THORHUB)
    assert "welcome_refusal" not in classified.error_context


def test_thorhub_429_is_a_plain_rate_limit_for_any_credential():
    """A fairshare 429 body is an ordinary rate limit now: the welcome tier that made it
    terminal is gone, so both a JWT and a static key stay retryable."""
    from agent.error_surface import build_error_surface_from_exception
    error = Exception("refused")
    error.status_code = 429
    error.body = {"status": 429, "message": "refused", "reason": "model_not_free", "alternates": ["thor/welcome"]}
    jwt = build_error_surface_from_exception(error, provider="thor", model="gpt-5", api_key="sk-thor-a")
    key = build_error_surface_from_exception(error, provider="thor", model="gpt-5", api_key="sk-thor-b")
    assert jwt["retryable"] is True
    assert key["retryable"] is True
    assert jwt["code"] == key["code"] == "rate_limit"
