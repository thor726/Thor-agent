"""``thor_import_sites`` records every Thor core import of a plugin, public or not, with its
``try``/``except ImportError`` shape intact (the index ``catalog_core_imports`` reads)."""

from __future__ import annotations

from pathlib import Path

import thor_yaml as yaml

from thor_cli.plugin_validate_private_imports import (
    CoreImports,
    ImportBranch,
    ImportChoice,
    ImportSite,
    is_public_import,
    thor_import_sites,
)


def _plugin(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True)
    (root / "plugin.yaml").write_text(
        yaml.safe_dump({"name": root.name, "version": "1.0.0", "description": "x"}), encoding="utf-8")
    files = {"__init__.py": "def register(ctx):\n    pass\n", **files}
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def test_plain_thor_imports_are_recorded_with_file_and_line(tmp_path):
    plugin = _plugin(tmp_path / "sites", {"lib/agent_runner.py": (
        "import json\n"
        "def run():\n"
        "    from tools.tirith_security import ensure_installed\n"
        "    from thor_cli.config import _private_helper\n"
        "    return ensure_installed, _private_helper\n"
    )})

    found = thor_import_sites(plugin)

    assert found == CoreImports((
        ImportSite("lib/agent_runner.py", 3, "tools.tirith_security", "ensure_installed"),
        ImportSite("lib/agent_runner.py", 4, "thor_cli.config", "_private_helper"),
    ), ())


def test_try_except_import_error_becomes_a_choice_with_body_and_handler_branches(tmp_path):
    plugin = _plugin(tmp_path / "fallback", {"adapter.py": (
        "try:\n"
        "    from thor_cli.config import _private_helper\n"
        "except ImportError:\n"
        "    from thor_cli import config\n"
    )})

    found = thor_import_sites(plugin)

    assert found.plain == ()
    assert found.choices == (ImportChoice((
        # The body branch: the import the plugin prefers.
        ImportBranch((ImportSite("adapter.py", 2, "thor_cli.config", "_private_helper"),)),
        # The handler branch: the import it falls back to.
        ImportBranch((ImportSite("adapter.py", 4, "thor_cli", "config"),)),
    )),)


def test_type_checking_imports_are_not_recorded(tmp_path):
    plugin = _plugin(tmp_path / "typing", {"__init__.py": (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from run_agent import AIAgent\n"
        "    from thor_cli.config import _private_helper\n"
        "def register(ctx):\n"
        "    pass\n"
    )})

    assert thor_import_sites(plugin) == CoreImports((), ())


def test_own_package_imports_are_not_recorded(tmp_path):
    plugin = _plugin(tmp_path / "own", {
        "__init__.py": (
            "from clean_lib.helpers import local_helper\n"
            "from .client import Client\n"
            "import thor_cli.config\n"
        ),
        "clean_lib/__init__.py": "",
        "clean_lib/helpers.py": "def local_helper():\n    pass\n",
        "client.py": "class Client:\n    pass\n",
    })

    found = thor_import_sites(plugin)

    assert found == CoreImports((ImportSite("__init__.py", 3, "thor_cli.config", ""),), ())


def test_is_public_import_judges_the_published_api():
    assert is_public_import("gateway.platforms", "base") is True
    assert is_public_import("thor_cli.config", "_private_helper") is False
