"""``thor dashboard register`` — retired with the Thor Portal.

Registering a self-hosted dashboard OAuth client (``POST {portal}/api/oauth/self-hosted-client``)
only existed on the Nous Portal. ThorHub has no OAuth clients (static API keys only), so the
command fails honestly instead of posting to a dead host. The module shape is kept so the CLI
entry still resolves.
"""

from __future__ import annotations

import sys


def cmd_dashboard_register(args) -> None:
    """Retired: dashboard OAuth client registration lived on the Thor Portal."""
    print("✗ `thor dashboard register` is retired — the Thor Portal is gone.\n"
          "  ThorHub uses static API keys and has no OAuth client registration.\n"
          "  Add your ThorHub key with `thor auth add thor` instead.")
    sys.exit(1)
