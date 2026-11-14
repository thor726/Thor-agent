"""Shared guard for the live-site probes (docs search, skills index, catalog CORS).

The docs URL was rebranded to ``thor-agent.thor-agent.local`` — a placeholder
host that will never resolve until the project's docs domain actually exists.
Upstream's workflows probe the *deployed* site, so until a real docs host is
configured these probes have nothing honest to check: every run would fail on
``getaddrinfo ENOTFOUND`` and page whoever watches the repository.

Usage (first line of the probe's entry point)::

    from scripts.ci.live_site_guard import guard as live_site_guard

    live_site_guard()  # exits 0 with a visible "skipped" notice when the host is a placeholder

The guard resolves the effective URL exactly like each probe does (the
``DOCS_URL`` environment variable, else the built-in default). When the host
is a placeholder (unresolvable ``.local`` name) the process exits 0 after
printing one clear line, so scheduled runs stay green instead of paging for a
site that does not exist yet. When a real domain is configured the guard is a
no-op and the probe runs as before.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit

# Placeholder hosts that will never resolve in public DNS. Extending this list
# is how future placeholder domains get covered without touching the probes.
PLACEHOLDER_SUFFIXES = (".local",)

DEFAULT_DOCS_URL = "https://thor-agent.thor-agent.local/docs"


def effective_docs_url() -> str:
    """The URL the probes would fetch: ``$DOCS_URL`` or the built-in default."""
    return os.environ.get("DOCS_URL") or DEFAULT_DOCS_URL


def is_placeholder_host(url: str) -> bool:
    """True when the URL's host is a placeholder that public DNS cannot resolve."""
    host = urlsplit(url).hostname or ""
    return any(host == suffix.lstrip(".") or host.endswith(suffix) for suffix in PLACEHOLDER_SUFFIXES)


def guard() -> None:
    """Exit 0 with a visible notice when the live-site host is still a placeholder."""
    url = effective_docs_url()
    if not is_placeholder_host(url):
        return
    host = urlsplit(url).hostname
    notice = (
        f"SKIP: live-site probes are disabled because the docs host '{host}' is a "
        "placeholder (.local) — there is no deployed site to check yet. Set the "
        "DOCS_URL environment variable (or replace the default in "
        "scripts/ci/live_site_guard.py) to the real docs domain to enable them."
    )
    print(notice)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
            summary.write(f"### Live-site probes\n- {notice}\n")
    sys.exit(0)


if __name__ == "__main__":
    guard()
