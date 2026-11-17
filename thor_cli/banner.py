"""Welcome banner, ASCII art, skills summary, and update check for the CLI."""
import logging
import os
import sys
import threading
from pathlib import Path
from thor_cli import source_check
# Historical updater import (tests/compat/old_updater_surface.json). In-tree callers use the owner.
from thor_cli.source_check import _github_compare_behind
from thor_constants import get_thor_home
from typing import Any, Dict, List, Optional
from thor_cli._startup_fast import project_root_str

# rich and prompt_toolkit are imported lazily: this module sits on the TUI gateway's critical
# startup path purely for the lightweight update-check helpers, and eager rich/prompt_toolkit
# imports cost ~50ms before ``gateway.ready`` could fire.
logger = logging.getLogger(__name__)

# ANSI building blocks for conversation display (``_DIM``/``_RST`` are imported by callbacks.py).
_DIM = "\033[2m"
_RST = "\033[0m"


def _check_via_pypi() -> Optional[int]:
    # Shim to stop the old updater doing work until relaunch. no registry query.
    return None


def check_via_pypi() -> Optional[int]:
    # Shim to stop the old updater doing work until relaunch. status is unknown.
    return None


def _quiet(fn, default=None):
    """``fn()``, or ``default`` on any exception — for best-effort display inputs."""
    try:
        return fn()
    except Exception:
        return default


def cprint(text: str):
    """Print ANSI-colored text through prompt_toolkit's renderer."""
    from prompt_toolkit import print_formatted_text as _pt_print
    from prompt_toolkit.formatted_text import ANSI as _PT_ANSI
    # prompt_toolkit needs a real console: on Windows a redirected/absent stdout raises
    # NoConsoleScreenBufferError, and display helpers must never crash the caller over that.
    if _quiet(lambda: _pt_print(_PT_ANSI(text)) or True) is None:
        print(text)




from thor_cli import __release_date__ as RELEASE_DATE
from thor_cli.version_info import get_version_info





def compute_toolset_availability(enabled_toolsets: list[str] | None = None) -> dict[str, Any]:
    """Compute ``{"unavailable_toolsets", "lazy_tools", "disabled_tools"}``.

    Used by the gateway session inventory (the TUI banner's data) to colour
    lazy/disabled tools; the classic banner render is gone, this stays.
    """
    from model_tools import check_tool_availability, TOOLSET_REQUIREMENTS
    enabled_toolsets = enabled_toolsets or []
    _, unavailable_toolsets = check_tool_availability(quiet=True)
    # The availability check walks the GLOBAL registry, so it includes toolsets outside this
    # agent's platform set (e.g. `discord` on a CLI session) which must never surface in
    # "Available Tools". Restrict to enabled toolsets; an enabled toolset with unmet deps
    # legitimately shows as disabled/lazy below.
    _enabled_ts = {str(t) for t in enabled_toolsets}
    if _enabled_ts:
        unavailable_toolsets = [
            item for item in unavailable_toolsets if str(item.get("id", item.get("name", ""))) in _enabled_ts]
    # Toolsets with a check_fn are lazy-initialized (e.g. honcho): unavailable at banner time
    # because the check hasn't run yet, but not misconfigured.
    lazy_tools, disabled_tools = set(), set()
    for item in unavailable_toolsets:
        is_lazy = TOOLSET_REQUIREMENTS.get(item.get("name", ""), {}).get("check_fn")
        (lazy_tools if is_lazy else disabled_tools).update(item.get("tools", []))
    return {"unavailable_toolsets": unavailable_toolsets, "lazy_tools": sorted(lazy_tools),
            "disabled_tools": sorted(disabled_tools)}

# === Skills scanning ===

# Per-process caches: ``None`` until computed, then a 1-tuple ``(value,)`` so a computed ``None``
# is distinguishable from "not yet computed". Reset by assigning ``None`` (tests, ``thor skills``).
_available_skills_cache: Optional[tuple] = None
_git_banner_state_cache: Optional[tuple] = None
_latest_release_cache: Optional[tuple] = None

_UNCACHED = object()  # compute() result that must not be memoized


def _memo(cache_name: str, compute):
    """Return the cached value under module global ``cache_name``, computing (and storing) it once.

    Not consulted under a routed profile (THOR_HOME override): every memo here is derived from the
    launch home (its skills tree, its checkout), and the TUI gateway calls these per profile."""
    from thor_constants import get_thor_home_override
    if get_thor_home_override() is not None:
        return compute()
    cached = globals()[cache_name]
    if cached is not None:
        return cached[0]
    value = compute()
    if value is not _UNCACHED:
        globals()[cache_name] = (value,)
    return value


def get_available_skills() -> dict[str, list[str]]:
    """Return skills grouped by category, filtered by platform and disabled state.

    Cached per-process (the skills-tree walk costs ~100ms and feeds only the startup banner);
    ``prefetch_banner_data()`` pays it off-thread. A failed scan yields ``{}`` and is not cached.
    """
    def _scan():
        from tools.skills_tool import find_all_skills
        return find_all_skills()  # already filtered

    def _compute():
        all_skills = _quiet(_scan)
        if all_skills is None:
            return _UNCACHED
        skills_by_category: dict[str, list[str]] = {}
        for skill in all_skills:
            skills_by_category.setdefault(skill.get("category") or "general", []).append(skill["name"])
        return skills_by_category
    result = _memo("_available_skills_cache", _compute)
    return {} if result is _UNCACHED else result


def _resolve_repo_dir() -> Optional[Path]:
    """The active Thor git checkout, or None if this isn't a git install.

    Prefers the running code's location: ``$THOR_HOME/thor-agent/`` may be a stale copy
    carried over by ``--clone-all``.
    """
    repo_dir = Path(project_root_str())
    if not (repo_dir / ".git").exists():
        repo_dir = get_thor_home() / "thor-agent"
    return repo_dir if (repo_dir / ".git").exists() else None


def get_git_banner_state(repo_dir: Optional[Path] = None) -> Optional[dict]:
    """Return upstream/local git hashes for the startup banner.

    Cached per-process (default ``repo_dir`` only): 2-3 git subprocesses (~100ms) whose result
    cannot change under a running CLI. The cache lets ``prefetch_banner_data()`` pay it off-thread.
    """
    if repo_dir is not None:
        return _compute_git_banner_state(repo_dir)
    return _memo("_git_banner_state_cache", _compute_git_banner_state)


def _baked_banner_state() -> Optional[dict]:
    """Banner state from the baked build SHA (Docker image path), or None."""
    def _baked():
        from thor_cli.version_info import get_code_identity
        return get_code_identity().get("short_sha")
    baked = _quiet(_baked)
    return {"upstream": baked, "local": baked, "ahead": 0} if baked else None


def _compute_git_banner_state(repo_dir: Optional[Path] = None) -> Optional[dict]:
    repo_dir = repo_dir or _resolve_repo_dir()
    if repo_dir is None:
        return _baked_banner_state()
    upstream, local = (source_check._git_stdout(["rev-parse", "--short=8", rev], cwd=repo_dir) for rev in ("origin/main", "HEAD"))
    if not upstream or not local:
        # Live-git lookup failed (e.g. shallow clone without origin/main).
        return _baked_banner_state()
    ahead = source_check._git_count(["rev-list", "--count", "origin/main..HEAD"], cwd=repo_dir) or 0
    return {"upstream": upstream, "local": local, "ahead": max(ahead, 0)}


_RELEASE_URL_BASE = "https://github.com/thor726/thor-agent/releases/tag"


def get_latest_release_tag(repo_dir: Optional[Path] = None) -> Optional[tuple]:
    """Return ``(tag, release_url)`` for the latest local git tag, or None (a miss is cached too).

    Release URL always points at the canonical thor726/thor-agent repo (forks get no link).
    """
    def _compute():
        rd = repo_dir or _resolve_repo_dir()
        tag = source_check._git_stdout(["describe", "--tags", "--abbrev=0"], cwd=rd, timeout=3) if rd else None
        return (tag, f"{_RELEASE_URL_BASE}/{tag}") if tag else None
    return _memo("_latest_release_cache", _compute)


def format_banner_version_label() -> str:
    """Return the version label shown in the startup banner title."""
    from thor_cli.config import get_project_root
    from thor_cli.steward import read_install_stamp
    from thor_cli.update_channel import is_canary_tag

    stamp = read_install_stamp(get_project_root())
    if stamp.get("distribution") == "desktop-app":
        label = f"Thor Agent v{get_version_info().derived_version}"
        if stamp.get("source") == "commit-build":
            return f"{label} · commit-build · {str(stamp.get('commit') or '')[:12]}"
        if stamp.get("tag"):
            channel = "canary" if is_canary_tag(stamp["tag"]) else "stable"
            return f"{label} · {channel}"
        if stamp.get("payload") == "bootstrap":
            # The old installer shell's CLI backend: the shell never updates
            # itself (`self`), the managed checkout under it does. Name the
            # shell so it doesn't read as a plain packaged build.
            return f"{label} · installer"
        return label

    base = f"Thor Agent v{get_version_info().derived_version} ({RELEASE_DATE})"
    from thor_cli.config import load_config
    from thor_cli.update_channel import resolve_update_channel

    channel = resolve_update_channel(_quiet(load_config), get_project_root())
    if channel != "main":
        head = source_check._git_stdout(["rev-parse", "HEAD"], cwd=get_project_root())
        return f"{base} · {channel}" + (f" · local {head[:12]}" if head else "")
    state = get_git_banner_state()
    if not state:
        return base
    upstream, local = state["upstream"], state["local"]
    ahead = int(state.get("ahead") or 0)
    if ahead <= 0 or upstream == local:
        return f"{base} · upstream {upstream}"
    return f"{base} · upstream {upstream} · local {local} (+{ahead} carried {_plural(ahead, 'commit')})"


# === Non-blocking update check ===

_update_result: Optional[int] = None
_update_check_done = threading.Event()


def _daemon(name: Optional[str], target) -> None:
    """Start a daemon thread running ``target`` with any exception swallowed."""
    threading.Thread(target=lambda: _quiet(target), name=name, daemon=True).start()


def _skip_background_prefetch() -> bool:
    """True when the banner's background prefetch threads must not start.

    Under pytest the prefetch daemon threads shell out to git (``rev-parse``,
    ``remote get-url``, the banner's git state) at an arbitrary point after
    import, and any test that patches the process-wide ``subprocess`` singleton
    (``patch("subprocess.run")`` / ``patch("subprocess.Popen")``) can record
    that stray spawn in place of the call it meant to pin.  Importing
    ``tui_gateway.server`` starts this prefetch, which is what flaked
    tests/tui_gateway/test_bot_relay_methods.py.
    Nothing under pytest needs a live update check; tests that exercise the
    prefetch itself monkeypatch this predicate to False.

    ``PYTEST_CURRENT_TEST`` is only set while a test runs, not during
    collection-time imports, hence the ``sys.modules`` check as well.
    """
    return "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules


def prefetch_update_check():
    """Kick off update check in a background daemon thread.

    No-op under pytest — see ``_skip_background_prefetch``.
    """
    if _skip_background_prefetch():
        _update_check_done.set()
        return

    def _run():
        global _update_result
        _update_result = source_check.check_for_updates(passive=True).get("behind")
        _update_check_done.set()
    _daemon(None, _run)


_banner_data_prefetch_started = False


def prefetch_banner_data():
    """Warm the banner's subprocess/I/O-heavy inputs in a daemon thread.

    Git state (~130ms) and the skills index (~110ms) are cached per-process by their own modules,
    so warming them while the main thread pays the CPU-bound imports overlaps GIL-releasing I/O
    with import work. Idempotent; failures don't matter because the banner recomputes anything missing.
    """
    global _banner_data_prefetch_started
    if _banner_data_prefetch_started:
        return
    if _skip_background_prefetch():
        # Same stray-git-spawn cross-talk class as prefetch_update_check:
        # get_git_banner_state() shells out via the shared subprocess
        # singleton from a daemon thread, poisoning process-wide subprocess
        # mocks in unrelated tests.
        _banner_data_prefetch_started = True
        return
    _banner_data_prefetch_started = True
    _daemon("banner-data-prefetch", lambda: [_quiet(warm) for warm in (
        get_git_banner_state, get_latest_release_tag, get_available_skills)])


def get_update_result(timeout: float = 0.5) -> Optional[int]:
    """Get result of prefetched check. Returns None if not ready."""
    _update_check_done.wait(timeout=timeout)
    return _update_result


def _format_update_notice(behind: int) -> str:
    """Render the update warning line for a non-zero ``behind`` result."""
    from thor_cli.config import get_managed_update_command, recommended_update_command
    if behind > 0:
        return (
            f"[bold yellow]⚠ {behind} {_plural(behind, 'commit')} behind[/]"
            f"[dim yellow] — run [bold]{recommended_update_command()}[/bold] to update[/]")
    # UPDATE_AVAILABLE_NO_COUNT (nix): an update exists but we don't know by how much, nor how
    # the user installed (nix run, profile, system flake, home-manager).
    managed_cmd = get_managed_update_command()
    suffix = f"[dim yellow] — run [bold]{managed_cmd}[/bold][/]" if managed_cmd else ""
    return f"[bold yellow]⚠ update available[/]{suffix}"


_deferred_update_notice_started = False


def _render_markup_to_ansi(markup: str) -> str:
    """Rich markup → ANSI string, for output that must go through prompt_toolkit's renderer.

    Under ``patch_stdout`` (the interactive CLI), a plain ``Console.print`` writes ESC bytes into
    the StdoutProxy, which sanitizes them into visible ``?[1;33m…`` artifacts (#83969).
    """
    from io import StringIO
    from rich.console import Console as _Console
    buf = StringIO()
    _Console(file=buf, force_terminal=True, color_system="truecolor", highlight=False).print(markup)
    return buf.getvalue().rstrip("\n")


def _defer_update_notice(max_wait: float = 30.0) -> None:
    """Print the update warning once the prefetched check completes (at most once per process).

    Used when the banner rendered before the update prefetch finished so startup never blocks on
    git/network. The notice lands after prompt_toolkit owns the terminal, so it is routed through
    ``cprint`` (prompt_toolkit's renderer prints above a running application from any thread).
    """
    global _deferred_update_notice_started
    if _deferred_update_notice_started:
        return
    _deferred_update_notice_started = True

    def _wait_and_print() -> None:
        if _update_check_done.wait(timeout=max_wait) and _update_result:
            cprint(_render_markup_to_ansi(_format_update_notice(_update_result)))
    _daemon("update-notice", _wait_and_print)  # never break the session over an update notice


# === Welcome banner ===

def _plural(n: int, word: str) -> str:
    return word if n == 1 else f"{word}s"


def _format_context_length(tokens: int) -> str:
    """Format a token count for display (e.g. 128000 → '128K', 1048576 → '1M')."""
    for unit, div in (("M", 1_000_000), ("K", 1_000)):
        if tokens >= div:
            val = tokens / div
            rounded = round(val)
            return f"{rounded}{unit}" if abs(val - rounded) < 0.05 else f"{val:.1f}{unit}"
    return str(tokens)






















