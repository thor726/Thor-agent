# persistence/ — Fase 7 (partial port)

Upstream Hermes keeps the whole SQLite state store behind `persistence/`
(+ `persistence_assembly.py`): conversation store, authority/subagents,
gateway hosted rooms, workers, admin/recovery — ~170 files. Thor still
runs its live state through the `thor_state_*.py` split modules, which
already ARE that code in a different layout (verified file by file
against the upstream audit clone).

## What is ported here

- `core/errors.py` — backend-neutral error taxonomy (`PersistenceError`,
  `StoreQuarantined`, `AuthorityRefusal`, …). New code should raise/
  catch these; `thor_state_errors.py` keeps serving the live store.
- `core/identity.py` — opaque identifiers, paging primitives.
- `core/conventions.py` — stored-instant decoding, `RowVisibility`.
- `core/keys.py` — profile encoded in an `agent:<ns>:...` session key.
- `authority/vocabulary.py` — admission/authority constants (`OwnerRule`,
  `LEGACY_*`, …).
- Top-level helpers: `process_identity.py`, `session_rescue.py`,
  `storage_limits.py`, `session_keys.py` (repo root, same as upstream).
- Checkpoints moved to `agent/checkpoints/` with `tools/checkpoint_*`
  compat shims (upstream did the same move).

## Accepted divergence (NOT ported in this phase)

- **`persistence/sqlite/*` (~150 files).** A mechanical move of
  `thor_state_*.py` into `persistence/sqlite/...` would rewire every
  importer (`run_agent.py` + dozens of tools) with zero behaviour
  change and high regression risk. Thor's split already carries the
  same logic; the move stays open for a later phase that can rewire
  callers incrementally behind the contracts ported here.
- **`session_rules/` (18 files).** Every rule already exists in Thor,
  spread across `agent/`, `gateway/` and `thor_state_*` (e.g.
  `bound_activity_description` in `agent/session_activity.py`,
  `validate_import_payload` in `thor_state_portability.py`,
  `GoalContract` in `gateway/session_viewer_automation.py`). Thor
  even did the onboarding extraction already under `agent/`
  (`agent/onboarding_first_tasks.py` is byte-identical to upstream's
  `session_rules/onboarding_first_tasks.py` modulo the docs URL).
  Extracting the rest means moving code out of ~15 live files;
  porting them as dead duplicates would only create drift. The
  genuinely missing pieces are tiny (`RowVisibility`, `OwnerRule` —
  ported above; `compacted_api_payload`, `automation_descriptor`,
  `folded_payload`, `normalize_task_payload` — small helpers whose
  files otherwise already exist in Thor).
- **`session_retention.py`, `lineage_adoption.py`,
  `persistence_assembly.py`, `sqlite_support.py`, `storage_errors.py`.**
  These need the full store contracts (or already live in Thor:
  `sqlite_support` ≈ `thor_state_dbfile.py` + `thor_state_wal.py`,
  `storage_errors` predicates ≈ `thor_state_errors.py`).
- **`persistence/conversation/messages.py`, `gateway/hosted_rooms.py`,
  `housekeeping/maintenance.py`** (the big contract surfaces): not
  ported without a store implementing them; the next step if the
  sqlite move is ever attempted.

## Rules for this package

- No upstream-vendor naming, no Nous Portal / OAuth, no portal host
  under the old `.thor-agent.local` suffix. Legacy data labels that must keep matching
  stored rows (e.g. a `nous:` login stamp) stay in `thor_state_*` where
  they already are; they are data compatibility, not an integration.
- New persistence code imports from `persistence.*`; the live store
  keeps using `thor_state_*` until a later phase rewires it.
