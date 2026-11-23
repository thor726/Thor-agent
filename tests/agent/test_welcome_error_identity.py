"""The anonymous UI is a property of the request credential, not a free model or host (#111970)."""

from types import SimpleNamespace

import pytest

from agent.error_classifier import classify_api_error
from tests.thor_cli.anon_portal import make_jwt
from agent.error_surface import build_error_surface_from_result
from agent.turn_recovery import max_retries_exhausted_result, nonretryable_client_error_result

WELCOME = "https://welcome-api.thor-agent.local/v1"
NAMED = "https://inference-api.thor-agent.local/v1"


def agent_for(api_key, base_url):
    return SimpleNamespace(
        provider="nous", api_key=api_key, base_url=base_url, model="stepfun/step-3.7-flash:free",
        log_prefix="", _rate_limit_state=None, _has_pending_fallback=lambda: False,
        _dump_api_request_debug=lambda *a, **kw: None, _flush_status_buffer=lambda: None,
        _summarize_api_error=lambda e: str(e), _emit_status=lambda *a, **kw: None,
        _persist_session=lambda *a, **kw: None, _plines=lambda *a, **kw: None, _vprint=lambda *a, **kw: None,
        _buffer_status=lambda *a, **kw: None, _buffer_vprint=lambda *a, **kw: None,
        _emit_diagnostic_status=lambda *a, **kw: None, _buffer_diagnostic_status=lambda *a, **kw: None,
        _try_activate_fallback=lambda: False,
    )


@pytest.mark.parametrize("api_key", [make_jwt(account_tier="free", client_id="thor-cli"), "sk-named"],
                         ids=["named-free", "api-key"])
@pytest.mark.parametrize("base_url", [NAMED, WELCOME])
@pytest.mark.parametrize("case", ["rate_limited", "model_not_free", "403"])
def test_named_errors_do_not_offer_anonymous_recovery(api_key, base_url, case):
    """A shared fairshare body or wrong welcome URL cannot establish anonymous identity."""
    status = 403 if case == "403" else 429
    message = ("You tried to access something that you don't have permissions for." if case == "403"
               else "The service refused this request.")
    body = {"status": status, "message": message, "reason": case, "retry_after": 158}
    error = Exception(message)
    error.status_code, error.body = status, body
    agent = agent_for(api_key, base_url)
    classified = classify_api_error(error, provider="nous", model=agent.model, base_url=base_url, api_key=api_key)
    common = dict(api_kwargs=None, api_messages=[], messages=[], conversation_history=[],
                  api_call_count=1, approx_tokens=10, provider="nous", base_url=base_url, model=agent.model)
    if status == 403:
        result = nonretryable_client_error_result(agent, error, classified, status_code=status, **common)
    else:
        result = max_retries_exhausted_result(agent, error, classified, attempts=3,
                                             is_rate_limited=status == 429, error_msg=message, **common)
    assert "welcome_refusal" not in classified.error_context
    assert "welcome_route" not in classified.error_context
    assert "free_tier" not in result
    surface = build_error_surface_from_result(result, provider="nous", model=agent.model)
    assert surface["code"] == {403: "auth", 429: "rate_limit"}[status]
    assert "without signing in" not in result["final_response"]


@pytest.mark.parametrize("tier", ["anonymous", "free"])
def test_401_diagnostics_follow_request_identity_on_welcome_host(tier, capsys, monkeypatch):
    import agent.conversation_loop as loop
    from agent.turn_recovery import _print_nous_401_diagnostics

    monkeypatch.setattr(loop, "_print_nous_entitlement_guidance", lambda *a: False)
    _print_nous_401_diagnostics(agent_for(make_jwt(account_tier=tier), WELCOME), Exception("unauthorized"))
    output = capsys.readouterr().out
    assert ("Thor couldn't start a new one" in output) == (tier == "anonymous")
    assert ("thor auth add nous" in output) == (tier != "anonymous")


def test_anonymous_claim_does_not_classify_other_providers_as_nous():
    error = Exception("refused")
    error.status_code = 429
    error.body = {"reason": "rate_limited", "retry_after": 600}
    classified = classify_api_error(error, provider="custom", api_key=make_jwt(), base_url=WELCOME)
    assert "welcome_refusal" not in classified.error_context


def test_named_account_on_welcome_host_gets_reconnect_copy_without_signin_card():
    """The gateway's mirror 400 keeps its reconnect copy for a signed-in user; the sign-in card would
    ask for a sign-in that already happened."""
    message = "This endpoint serves anonymous Thor Agent accounts only. Use https://inference-api.thor-agent.local with your API key or signed-in account."
    error = Exception(message)
    error.status_code, error.body = 400, {"status": 400, "message": message}
    agent = agent_for(make_jwt(account_tier="free", client_id="thor-cli"), WELCOME)
    classified = classify_api_error(error, provider="nous", model=agent.model, base_url=WELCOME, api_key=agent.api_key)
    result = nonretryable_client_error_result(
        agent, error, classified, status_code=400, api_kwargs=None, api_messages=[], messages=[],
        conversation_history=[], api_call_count=1, approx_tokens=10, provider="nous", base_url=WELCOME, model=agent.model)
    assert "needs to reconnect" in result["final_response"]
    assert "free_tier" not in result
    assert "sign in" not in result["final_response"].lower()


def test_escaped_exception_surface_keeps_the_anonymous_verdict():
    """The desktop's escaped-exception card classifies with the request credential too."""
    from agent.error_surface import build_error_surface_from_exception
    error = Exception("refused")
    error.status_code = 429
    error.body = {"status": 429, "message": "refused", "reason": "model_not_free", "alternates": ["nous/welcome"]}
    anonymous = build_error_surface_from_exception(error, provider="nous", model="gpt-5", api_key=make_jwt())
    named = build_error_surface_from_exception(error, provider="nous", model="gpt-5", api_key=make_jwt(account_tier="free"))
    assert anonymous["retryable"] is False
    assert named["retryable"] is True
