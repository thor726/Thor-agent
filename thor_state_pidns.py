"""PID-namespace identity for state.db lock/lease holders.

Canonical home moved to :mod:`process_identity` (Fase 7 persistence
refactor): this module re-exports its names so existing ``thor_state_pidns``
imports keep working. New code should import from :mod:`process_identity`
directly.
"""

from process_identity import (
    LocalPidNamespace,
    _PIDNS_TOKEN_RE,
    _UNSUPPORTED,
    _local_pid_namespace,
    _qualify,
    _recorded_namespace,
    _resolve_local_pid_namespace,
    holder_namespace_token,
    holder_pid_checkable,
    persistent_record_pidns_checkable,
    pid_namespace_id,
)

__all__ = [
    "LocalPidNamespace",
    "holder_namespace_token",
    "holder_pid_checkable",
    "persistent_record_pidns_checkable",
    "pid_namespace_id",
]
