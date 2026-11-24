"""Backend-neutral persistence contracts for Thor (Fase 7, partial port).

Upstream Hermes keeps the full store behind this package (``persistence`` +
``persistence_assembly``: conversation store, authority/subagents, gateway
hosted rooms, workers, admin/recovery). Thor still runs its live state
through the ``thor_state_*`` split modules, so this package currently holds
only the small, backend-neutral contract leaves that are safe to port
standalone (see ``persistence/core`` and ``persistence/authority``).

The full ``persistence/sqlite/*`` move is a recorded divergence: Thor's
``thor_state_*.py`` files already are the equivalent split, and moving them
would rewire every importer (``run_agent.py`` + dozens of tools) with no
behaviour change. See ``persistence/README.md``.
"""
