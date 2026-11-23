"""First-party gateway bearer auth (ThorHub era).

There is no managed vendor gateway anymore: the only origins that may
receive a bearer are ones the user explicitly configured
(``TOOL_GATEWAY_URL`` / ``CONNECTOR_GATEWAY_URL``), authenticated with the
static ThorHub key. Everything else gets ``{}``.
"""

import logging
from typing import Callable, Optional
from urllib.parse import urlsplit

from tools.managed_tool_gateway import build_vendor_gateway_url, read_thorhub_api_key

logger = logging.getLogger(__name__)


def connector_gateway_origin() -> str:
    """Explicit ``CONNECTOR_GATEWAY_URL``, or "" (no managed connectors host)."""
    return build_vendor_gateway_url("connector")


def is_managed_thorhub_gateway_url(
    url: object,
    gateway_builder: Optional[Callable[[str], str]] = None,
) -> bool:
    """True when ``url`` is on an explicitly configured gateway origin.

    Compared as an exact ``(scheme, netloc)`` pair — never as a name or a
    domain suffix — so a lookalike host and an ``http`` downgrade of a real
    host both stay outside the set. Unconfigured origins (empty string) never
    match anything.

    Anything granting a URL extra trust — our bearer, reading files off disk to
    upload — must gate on this, so an arbitrary URL can never inherit it.
    """
    if not isinstance(url, str) or not url.strip():
        return False

    build_origin = gateway_builder or build_vendor_gateway_url
    try:
        expected = {
            urlsplit(build_origin(label))[:2]
            for label in ("tool", "connector")
        }
        actual = urlsplit(url.strip())
    except ValueError:
        return False
    expected.discard(("", ""))

    return bool(actual.scheme) and (actual.scheme, actual.netloc) in expected


def managed_gateway_auth_headers(
    url: object,
    gateway_builder: Optional[Callable[[str], str]] = None,
    token_reader: Optional[Callable[[], Optional[str]]] = None,
) -> dict:
    """Live auth headers for a managed gateway URL, or ``{}`` when not managed.

    Read fresh on every call rather than cached. Returns ``{}`` rather than
    raising when no token is available, so a caller can report "sign in"
    instead of sending an unauthenticated request.
    """
    if not is_managed_thorhub_gateway_url(url, gateway_builder):
        return {}

    resolved_token_reader = token_reader or read_thorhub_api_key
    try:
        token = resolved_token_reader()
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug("Managed gateway token read failed for %s: %s", url, exc)
        return {}
    if not isinstance(token, str) or not token.strip():
        return {}

    from tools.managed_gateway_identity import user_agent

    return {"Authorization": f"Bearer {token.strip()}", "User-Agent": user_agent()}
