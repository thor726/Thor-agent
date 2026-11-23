"""Tests for the billing:manage scope step-up — retired with the Nous Portal.

ThorHub has no billing API and no step-up flow: a static key cannot gain a
``billing:manage`` scope, and credits are topped up at the ThorHub store instead.
Both step-up surfaces therefore decline honestly: the CLI mixin points at the
top-up page, the TUI ``billing.step_up`` RPC returns ``granted: False``.
"""

from __future__ import annotations

from thor_cli.cli_billing_mixin import CLIBillingMixin
from thor_cli.thorhub_account import THORHUB_TOPUP_URL


class _Cli(CLIBillingMixin):
    def __init__(self, choice: str = "yes"):
        self.choice, self.asked = choice, []
        self._app = object()

    def _modal_choice(self, title, detail, choices):
        self.asked.append((title, [c[0] for c in choices]))
        return self.choice


def _step_up(cli, **kw):
    return cli._step_up_remote_spending(
        explain="Remote spending lets Thor buy credits on your behalf.",
        noninteractive_msg="non-interactive: cannot confirm remote spending",
        declined_msg="declined",
        not_granted_msg="not granted",
        **kw,
    )


def test_step_up_noninteractive_declines_without_a_modal(capsys):
    cli = _Cli("yes")
    cli._app = None  # non-interactive: the modal can't run
    assert _step_up(cli) is False
    assert cli.asked == []
    assert "non-interactive: cannot confirm remote spending" in capsys.readouterr().out


def test_step_up_yes_points_at_the_topup_page(capsys):
    cli = _Cli("yes")
    assert _step_up(cli) is False
    assert cli.asked != []
    out = capsys.readouterr().out
    assert f"Top up at {THORHUB_TOPUP_URL}" in out


def test_step_up_declined_at_the_modal(capsys):
    cli = _Cli("cancel")
    assert _step_up(cli) is False
    assert "declined" in capsys.readouterr().out
    assert THORHUB_TOPUP_URL not in capsys.readouterr().out


def test_no_billing_token_cache_on_thorhub():
    """ThorHub keys are static: there is no billing token cache to drop after a grant."""
    from thor_cli import thorhub_billing

    assert not hasattr(thorhub_billing, "_token_cache")
    thorhub_billing.invalidate_cached_token()  # no-op, must not raise
