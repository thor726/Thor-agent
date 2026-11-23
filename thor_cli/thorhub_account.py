"""Klien saldo ThorHub (llm.thormarket.site) — pengganti portal Nous untuk ``/topup``.

Dipakai ``/topup`` (agent, via ``agent.account_usage_nous``) dan CLI ``_show_billing``.
Hanya membaca saldo lewat ``GET /portal/member/me`` dengan header
``Authorization: Bearer <key ThorHub>``. Key dibaca dari env ``THORHUB_API_KEY``
(alias ``thorhub`` di config Thor). Fungsi di sini tidak pernah melempar:
gagal (tidak ada key, jaringan, key salah) -> ``None``, pemanggil jatuh ke
alur lama.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

THORHUB_BASE_URL = "https://llm.thormarket.site"
THORHUB_TOPUP_URL = f"{THORHUB_BASE_URL}/beli/topup"
THORHUB_PORTAL_URL = f"{THORHUB_BASE_URL}/portal"
THORHUB_PACKAGES_URL = f"{THORHUB_BASE_URL}/beli"


def thorhub_api_key() -> str:
    """Key ThorHub dari env (alias thorhub). String kosong bila tidak ada."""
    return (os.environ.get("THORHUB_API_KEY") or "").strip()


def _fmt_id(n: object) -> str:
    """1234567 -> "1.234.567" (format Indonesia); gagal -> str apa adanya."""
    try:
        return f"{int(n):,}".replace(",", ".")  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return str(n)


def fetch_thorhub_balance(*, timeout: float = 10.0) -> dict | None:
    """Saldo key ThorHub (dict dari ``/portal/member/me``) atau None bila gagal."""
    key = thorhub_api_key()
    if not key:
        return None
    req = urllib.request.Request(
        f"{THORHUB_BASE_URL}/portal/member/me",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except Exception:
        return None
    data = payload.get("data") if isinstance(payload, dict) else None
    return data if isinstance(data, dict) else None


def format_thorhub_balance_lines(data: dict) -> tuple[str, ...]:
    """Baris saldo (token, bukan USD) untuk ditampilkan di /topup."""
    limit = data.get("token_limit")
    used = data.get("tokens_used")
    remaining = data.get("tokens_remaining")
    if remaining is None and limit is not None and used is not None:
        try:
            remaining = max(0, int(limit) - int(used))
        except (TypeError, ValueError):
            remaining = None
    lines = ["Saldo ThorHub (token AI):"]
    if limit is not None and used is not None:
        lines.append(f"  Terpakai: {_fmt_id(used)} / {_fmt_id(limit)} token")
    if remaining is not None:
        lines.append(f"  Sisa kuota: {_fmt_id(remaining)} token")
    days = data.get("key_days_left")
    if days is not None:
        lines.append(f"  Masa aktif key: {days} hari lagi")
    if data.get("is_active") is False:
        lines.append("  Key sedang nonaktif — hubungi admin ThorHub.")
    lines.append(f"  Top-up: {THORHUB_TOPUP_URL}")
    lines.append(f"  Portal member: {THORHUB_PORTAL_URL}")
    return tuple(lines)
