"""ThorHub provider profile (https://llm.thormarket.site).

Thor's own LLM gateway: OpenAI-compatible ``/v1`` served from a static
``sk-thor-...`` API key (``THORHUB_API_KEY``). No OAuth, no portal tags, no
per-model reasoning overrides -- plain chat/completions for every model.

The ``nous*`` aliases are a deprecated migration bridge only: configs that
still name provider ``nous`` keep resolving to ThorHub instead of failing.
"""

from providers import register_provider
from providers.base import ProviderProfile


thor = ProviderProfile(
    name="thor", aliases=("thorhub", "nous", "nous-portal", "nousresearch"),
    env_vars=("THORHUB_API_KEY",),
    display_name="ThorHub", description="ThorHub -- Thor's own LLM gateway",
    signup_url="https://llm.thormarket.site",
    fallback_models=("deepseek-v4-pro", "glm-5.3-flash"),
    base_url="https://llm.thormarket.site/v1", auth_type="api_key",
)

register_provider(thor)
