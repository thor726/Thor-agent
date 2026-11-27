"""``save_env_value(..., env_path=...)`` for ``thor gateway migrate --backends`` (Fase 2, A4).

Behaviour contract only: with ``env_path`` the value lands in that private file —
the migration's staged ``.env`` copy — never in the live ``.env``.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from thor_cli.config import save_env_value


def test_save_env_value_writes_to_a_given_private_copy(tmp_path):
    staged = tmp_path / "staged.env"
    staged.write_text("OLD_KEY=old\n")
    with patch.dict(os.environ, {"THOR_HOME": str(tmp_path)}, clear=False):
        save_env_value("THOR_DASHBOARD_BASIC_AUTH_SECRET", "staged-secret-value",
                       env_path=staged)
    content = staged.read_text(encoding="utf-8")
    assert "THOR_DASHBOARD_BASIC_AUTH_SECRET=staged-secret-value" in content
    assert "OLD_KEY=old" in content
    assert not (tmp_path / ".env").exists()
