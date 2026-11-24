"""Owner-handle cleanup for cron fires, including gates that never construct an agent."""
import logging

logger = logging.getLogger(__name__)


def _end_suppressed_cron_session(db, job: dict, job_id: str, job_name: str, cron_session_id: str) -> None:
    """End the admission's row without acquiring, releasing or closing its lent store.

    End BEFORE cosmetic writes: a timeout disables the shared bounded proxy, so a stalled
    title must not prevent the lifecycle write. At most one abandoned worker uses this handle.
    Receipts and terminal admissions remain available for exact retry and lazy resume.

    Thor adaptation: upstream takes a persistence facade whose session store lives under
    ``.sessions`` with ``end``/``update_cwd``; Thor's monolith SessionDB *is* the store, with
    ``end_session``/``update_session_cwd``. Either shape is accepted; a store of neither shape
    (e.g. a test authority) ends nothing and never raises.
    """
    from cron.scheduler import (
        _BoundedCronSessionDB, _set_cron_session_title, _thor_now, safe_strftime,
    )

    if db is None:
        return
    store = getattr(db, "sessions", db)
    bounded = _BoundedCronSessionDB(store, job_id)
    try:
        end = getattr(bounded, "end_session", None) or getattr(bounded, "end", None)
        if end is None:
            return
        end(cron_session_id, "cron_suppressed")
        title = " ".join(job_name.split())[:60].strip() or f"cron {job_id}"
        _set_cron_session_title(bounded, cron_session_id,
                               f"{title} · {safe_strftime(_thor_now(), '%b %d %H:%M')}")
        # No filesystem validation during teardown: this is the admission's configured cwd,
        # not a directory we are about to execute in. A disconnected mount must not block end.
        workdir = (job.get("workdir") or "").strip()
        if workdir:
            update_cwd = getattr(bounded, "update_session_cwd", None) or getattr(bounded, "update_cwd", None)
            if update_cwd is not None:
                update_cwd(cron_session_id, workdir)
    except (Exception, KeyboardInterrupt):
        logger.debug("Job '%s': suppressed session cleanup failed", job_id, exc_info=True)


def finish_cron_run(job, job_name, session_id, owner_execution, scope, session_db,
                    agent, worker_future, defer_agent_teardown):
    """One cleanup decision: a live worker owns teardown, otherwise finalize this fire now."""
    from cron.scheduler import _finalize_cron_session, _teardown_cron_agent
    from cron.scheduler_detached_worker import defer_teardown_to_running_worker

    job_id = job["id"]
    workdir = scope.workdir if scope is not None else None
    deferred = defer_teardown_to_running_worker(
        worker_future, session_db, agent, job_id, job_name, session_id, workdir=workdir)
    try:
        if scope is not None:
            scope.exit()
    finally:
        if not deferred:
            if session_db is not None:
                _finalize_cron_session(session_db, agent, job_id, job_name, session_id, workdir=workdir)
            elif owner_execution is not None:
                # Upstream authorities carry a persistence facade; Thor's carry the SessionDB
                # itself under ``.db``. Either shape ends the suppressed row; neither shape (a
                # test double) skips it instead of raising out of the ``finally``.
                authority = owner_execution[0]
                store = getattr(authority, "persistence", None)
                if store is None:
                    store = getattr(authority, "db", None)
                if store is not None:
                    _end_suppressed_cron_session(store, job, job_id, job_name, session_id)
            if scope is not None:
                if defer_agent_teardown is None:
                    _teardown_cron_agent(agent, job_id)
                elif agent is not None:
                    defer_agent_teardown.append(agent)
