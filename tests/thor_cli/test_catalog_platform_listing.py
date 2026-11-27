"""Catalog platforms a home does not have yet: listed by every setup surface, installed on pick.

Ported from upstream hermes-agent (tests/hermes_cli/test_catalog_platform_listing.py).
"""

import pytest

from thor_constants import get_thor_home


LABS = "https://github.com/NousResearch/hermes-labs-plugins"


@pytest.fixture
def fixture_catalog(monkeypatch):
    """A small catalog, one entry per rule the list applies, instead of the shipped one."""
    from thor_cli import plugin_catalog
    from thor_cli.plugin_catalog import PluginCatalogEntry

    def entry(name, tier, repo="https://github.com/NousResearch/hermes-official-plugins", category="platform"):
        return PluginCatalogEntry(name=name, repo=repo, sha="1" * 40, description=f"{name} platform. More words.",
                                  maintainer="Nous Research", tier=tier, category=category)

    entries = [entry("chatone", "official"), entry("chattwo", "verified"), entry("labschat", "community", repo=LABS),
               entry("commchat", "community", repo="https://github.com/someone/commchat"),
               entry("toolx", "official", category="desktop")]
    monkeypatch.setattr(plugin_catalog, "load_catalog_live", lambda: list(entries))
    monkeypatch.setattr(plugin_catalog, "load_catalog", lambda *a, **k: list(entries))
    monkeypatch.delenv("THOR_DISABLE_LAZY_INSTALLS", raising=False)  # the suite's opt-out; config decides here


def test_only_supported_catalog_platforms_are_offered_not_labs_or_community(fixture_catalog):
    from thor_cli.catalog_platform_listing import available_catalog_platforms, install_catalog_platform

    rows = {row.name: row for row in available_catalog_platforms(provided=())}
    # Hermes Labs, community and non-platform entries are not setup picks: the plugin browser has them.
    assert set(rows) == {"chatone", "chattwo"}
    assert rows["chatone"].badge == "official" and rows["chattwo"].badge == "verified"
    assert rows["chatone"].install_command == "thor plugins install chatone"
    assert rows["chatone"].summary == "chatone platform." and rows["chatone"].blocked == ""
    assert "chatone" not in {row.name for row in available_catalog_platforms(provided={"chatone"})}
    for name in ("labschat", "commchat"):  # a hand-crafted request does not get past the list's rule
        refused = install_catalog_platform(name)
        assert refused["ok"] is False and "not a catalog platform this home can add" in refused["error"]
    assert not (get_thor_home() / "plugins" / "labschat").exists()


def test_setup_menu_lists_catalog_platforms_and_lazy_off_says_why(fixture_catalog):
    from thor_cli import gateway

    rows = gateway._all_platforms(catalog=True)
    pick = next(p for p in rows if p["key"] == "chatone" and p.get("_catalog_platform"))
    assert gateway._platform_status(pick) == "not installed · official"
    assert not any(p["key"] == "labschat" and p.get("_catalog_platform") for p in rows)
    assert not any(p.get("_catalog_platform") for p in gateway._all_platforms())  # summaries: no progress

    (get_thor_home() / "config.yaml").write_text("security:\n  allow_lazy_installs: false\n", encoding="utf-8")
    from thor_cli.catalog_platform_listing import install_catalog_platform
    refused = install_catalog_platform("chatone")
    assert refused["ok"] is False and "allow_lazy_installs is off" in refused["error"]
    assert refused["install_command"] == "thor plugins install chatone"


def _install_late_platform(dir_name: str, platform: str, *, catalog_name: str = "",
                           repo: str = "https://github.com/NousResearch/hermes-official-plugins") -> None:
    """What an installer running in another process leaves behind: the tree, its install record when
    it came from the catalog, and the enable in config.yaml."""
    import json

    home = get_thor_home()
    plugin_dir = home / "plugins" / dir_name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(f"name: {dir_name}\nkind: platform\nversion: 1.0.0\n", encoding="utf-8")
    (plugin_dir / "__init__.py").write_text(
        "def register(ctx):\n"
        f"    ctx.register_platform(name={platform!r}, label='Late', adapter_factory=lambda cfg: None,\n"
        "                          check_fn=lambda: True, required_env=['LATE_TOKEN'])\n", encoding="utf-8")
    if catalog_name:
        record = {"catalog": {"name": catalog_name, "repo": repo, "tier": "official" if repo != LABS else "community",
                              "sha": "0" * 40, "pin": "0" * 40}}
        (home / "plugins" / ".install-metadata.json").write_text(json.dumps({dir_name: record}), encoding="utf-8")
    (home / "config.yaml").write_text(f"plugins:\n  enabled:\n    - {dir_name}\n", encoding="utf-8")


def test_channels_page_poll_signature_moves_when_a_platform_plugin_lands_elsewhere():
    import asyncio

    from thor_cli.web_routers.messaging import get_messaging_platforms_signature

    def poll():
        return asyncio.run(get_messaging_platforms_signature())["signature"]

    loaded = poll()
    assert poll() == loaded  # nothing moved: the page does not reload
    _install_late_platform("lateplug", "lateplug")  # the background default install lands
    assert poll() != loaded
