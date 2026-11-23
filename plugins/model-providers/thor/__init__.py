"""ThorHub provider profile (https://llm.thormarket.site).

Thor's own LLM gateway: OpenAI-compatible ``/v1`` served from a static
``sk-thor-...`` API key (``THORHUB_API_KEY``). No OAuth, no device-code login.

The ``nous*`` aliases are a deprecated migration bridge only: configs that
still name provider ``nous`` keep resolving to ThorHub instead of failing.

Wire behavior kept from the old Nous Portal profile: product tags on every call
(``product=thor-agent`` + client + conversation tags, plus a sticky
``session_id`` so cache breakpoints stay warm on one upstream instance), the
``provider: {data_collection: deny}`` routing field only when an outgoing
connector result requires it, and the reasoning wire shape ThorHub honors
(``reasoning: {enabled, effort}``; a disable is omitted for reasoning-mandatory
or unknown routes, which would 400 on it).
"""

from typing import Any

from agent.portal_tags import get_affinity_scope, get_conversation_context, nous_portal_tags
from agent.transports.codex import _cache_scope_from_session_id
from providers import register_provider
from providers.base import ProviderProfile


class ThorHubProfile(ProviderProfile):
    """ThorHub — product tags, reasoning with ThorHub-specific omission."""

    def resolve_aux_model(self, *, vision: bool = False) -> str:
        """ThorHub's tier-aware aux pick (cached, offline-safe). ThorHub has no
        recommendations feed, so this is always empty for now."""
        try:
            from thor_cli.models import get_thorhub_recommended_aux_model

            return get_thorhub_recommended_aux_model(vision=vision) or ""
        except Exception:
            return ""

    def build_extra_body(
        self, *, session_id: str | None = None, data_use: frozenset[str] = frozenset(), **context,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"tags": nous_portal_tags(session_id=session_id)}
        # Top-level session_id = sticky routing key, so Anthropic-style cache
        # breakpoints stay warm on one upstream instance. Resolved like the
        # ``conversation=`` tag: declared scope, then the ambient lineage ROOT
        # (covers aux call sites that pass no session_id), then the explicit argument.
        sticky_key = _cache_scope_from_session_id(get_affinity_scope() or get_conversation_context() or session_id)
        if sticky_key:
            body["session_id"] = sticky_key
        # ThorHub routes centrally and 400s on caller routing fields, except data_collection and
        # zdr: sent only when an outgoing connector result requires them (``data_use``), never from config.
        if data_use:
            body["provider"] = {"data_collection": "deny", **({"zdr": True} if "zero_retention" in data_use else {})}
        return body

    @staticmethod
    def _cannot_disable_reasoning(model: str | None) -> bool:
        """True when ``reasoning: {enabled: false}`` would 400 on *model*. Cache-only catalog
        lookup; unknown/cold (warmer kicked) and no-reasoning routes both answer True (omit > 400)."""
        try:
            from thor_cli.models_reasoning_caps import thorhub_model_reasoning_capabilities, warm_thorhub_reasoning_caps_async

            caps = thorhub_model_reasoning_capabilities(model)
            if caps is None:
                warm_thorhub_reasoning_caps_async()
                return True
        except Exception:
            return True
        return not caps.get("supports_reasoning") or bool(caps.get("mandatory"))

    def build_api_kwargs_extras(
        self, *, reasoning_config: dict | None = None, supports_reasoning: bool = False,
        model: str | None = None, **context,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Pass the full reasoning_config, disable included (ThorHub honors it;
        omitting it means the upstream default, thinking ON for V4-class models)."""
        if not supports_reasoning:
            return {}, {}
        if reasoning_config is None:
            return {"reasoning": {"enabled": True, "effort": "medium"}}, {}
        rc = dict(reasoning_config)
        if rc.get("enabled") is False and self._cannot_disable_reasoning(model):
            return {}, {}
        return {"reasoning": rc}, {}


thor = ThorHubProfile(
    name="thor", aliases=("thorhub", "nous", "nous-portal", "nousresearch"),
    env_vars=("THORHUB_API_KEY",),
    display_name="ThorHub", description="ThorHub — Thor's own LLM gateway",
    signup_url="https://llm.thormarket.site",
    fallback_models=("deepseek-v4-pro", "glm-5.3-flash"),
    base_url="https://llm.thormarket.site/v1", auth_type="api_key",
    # ThorHub's upstream currently drops 1h cache entries after ~7 minutes and bills them at the
    # 5m rate, so asking for 1h only pays the 2x write. Lift with config
    # ``prompt_caching.route_ttl_ceilings: {thor: 1h}`` (or delete this line) once that is fixed.
    prompt_cache_max_ttl="5m",
)

register_provider(thor)
