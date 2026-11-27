// Backend-migration plan payloads, captured from Thor's own engine (Fase 5, adaptasi A13).
// Do not hand-edit the payloads: re-run the capture script instead:
//   scripts/capture_backend_migration_fixtures.py [--check | --write DIR]

export const containerPlans = {
  "running": {
    "held": {
      "applied": false,
      "dry_run": true,
      "exit_code": 3,
      "plan": {
        "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-running",
        "old_backend": null,
        "old_address": null,
        "new_address": null,
        "keep_webapp_address": false,
        "copy_env_keys": [],
        "generate_secret": false,
        "public_url": null,
        "auth_before": null,
        "gateway": {},
        "linger": null,
        "webapp_bundle_missing": null,
        "running_turns": 1,
        "blockers": [
          "1 turn(s) are running on the old backend. Wait for them to finish, or re-run with --force-interrupt (they are interrupted)."
        ],
        "forceable_blockers": [
          "1 turn(s) are running on the old backend. Wait for them to finish, or re-run with --force-interrupt (they are interrupted)."
        ],
        "takes_over": [
          "Cuts off the 1 reply(ies) being written on the old backend."
        ],
        "unsupported": [
          {
            "supervisor": "container",
            "unit": "thor-dashboard.service",
            "pid": 4242,
            "instructions": "The backend runs in a container (Compose sidecar or docker run). Set webapp.enabled/host/port (below) in the mounted Thor home, drop the dashboard service from the Compose file, publish the same port on the gateway container, then `docker compose up -d`. Its Thor version could not be checked from outside its container, and a Thor older than v2026.7.30 does not record running chats: check inside the container that no reply is being written before you stop it. 1 turn(s) are running on it now: stopping it interrupts them, so let them finish first.",
            "steps": []
          }
        ],
        "notices": [],
        "nothing_to_do": false,
        "steps": [],
        "text": [
          "Backend migration plan (dry run — nothing changed)",
          "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-running",
          "  ✗ container thor-dashboard.service cannot be migrated automatically. Nothing changed.",
          "    The backend runs in a container (Compose sidecar or docker run). Set webapp.enabled/host/port (below) in the mounted Thor home, drop the dashboard service from the Compose file, publish the same port on the gateway container, then `docker compose up -d`. Its Thor version could not be checked from outside its container, and a Thor older than v2026.7.30 does not record running chats: check inside the container that no reply is being written before you stop it. 1 turn(s) are running on it now: stopping it interrupts them, so let them finish first.",
          "    Steps, in this order (one command per line):",
          "",
          "  The move also:",
          "    • Cuts off the 1 reply(ies) being written on the old backend.",
          "",
          "  ✗ Blockers (nothing will be changed):",
          "    • 1 turn(s) are running on the old backend. Wait for them to finish, or re-run with --force-interrupt (they are interrupted)."
        ],
        "expect_token": null,
        "found": true
      },
      "report": [
        {
          "supervisor": "container",
          "running": true,
          "pid": 4242,
          "unit": "thor-dashboard.service",
          "scope": "user",
          "state": "enabled",
          "this_home": true,
          "not_applied": "",
          "notes": []
        }
      ],
      "run": {
        "state": "none",
        "step": "",
        "steps": [],
        "message": "",
        "old_address": "",
        "new_address": "",
        "started_at": 0.0,
        "finished_at": null,
        "manual_steps": [],
        "reason": null
      },
      "profile": "default",
      "commands": {
        "status": "thor -p default gateway migrate --backends --status",
        "restore": "thor -p default gateway migrate --backends --restore"
      }
    },
    "forced": {
      "applied": false,
      "dry_run": true,
      "exit_code": 6,
      "plan": {
        "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-running",
        "old_backend": null,
        "old_address": null,
        "new_address": null,
        "keep_webapp_address": false,
        "copy_env_keys": [],
        "generate_secret": false,
        "public_url": null,
        "auth_before": null,
        "gateway": {},
        "linger": null,
        "webapp_bundle_missing": null,
        "running_turns": 1,
        "blockers": [],
        "forceable_blockers": [],
        "takes_over": [
          "Cuts off the 1 reply(ies) being written on the old backend."
        ],
        "unsupported": [
          {
            "supervisor": "container",
            "unit": "thor-dashboard.service",
            "pid": 4242,
            "instructions": "The backend runs in a container (Compose sidecar or docker run). Set webapp.enabled/host/port (below) in the mounted Thor home, drop the dashboard service from the Compose file, publish the same port on the gateway container, then `docker compose up -d`. Its Thor version could not be checked from outside its container, and a Thor older than v2026.7.30 does not record running chats: check inside the container that no reply is being written before you stop it. 1 turn(s) are running on it now: stopping it interrupts them, so let them finish first.",
            "steps": [
              "# in the mounted Thor home's config.yaml set webapp.enabled: true, webapp.host: 0.0.0.0, webapp.port: 9119",
              "# copy every THOR_DASHBOARD_* line from the old launcher's environment that /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-running/.env does not already set, if any, into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-running/.env (chmod 600)",
              "# remove the dashboard: recreate the container without THOR_DASHBOARD=1, or drop the Compose `dashboard` service and run: docker compose up -d --remove-orphans",
              "# publish 9119 on the gateway's container and restart it, so its gateway serves the address"
            ]
          }
        ],
        "notices": [],
        "nothing_to_do": false,
        "steps": [],
        "text": [
          "Backend migration plan (dry run — nothing changed)",
          "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-running",
          "  ✗ container thor-dashboard.service cannot be migrated automatically. Nothing changed.",
          "    The backend runs in a container (Compose sidecar or docker run). Set webapp.enabled/host/port (below) in the mounted Thor home, drop the dashboard service from the Compose file, publish the same port on the gateway container, then `docker compose up -d`. Its Thor version could not be checked from outside its container, and a Thor older than v2026.7.30 does not record running chats: check inside the container that no reply is being written before you stop it. 1 turn(s) are running on it now: stopping it interrupts them, so let them finish first.",
          "    Steps, in this order (one command per line):",
          "      # in the mounted Thor home's config.yaml set webapp.enabled: true, webapp.host: 0.0.0.0, webapp.port: 9119",
          "      # copy every THOR_DASHBOARD_* line from the old launcher's environment that /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-running/.env does not already set, if any, into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-running/.env (chmod 600)",
          "      # remove the dashboard: recreate the container without THOR_DASHBOARD=1, or drop the Compose `dashboard` service and run: docker compose up -d --remove-orphans",
          "      # publish 9119 on the gateway's container and restart it, so its gateway serves the address",
          "",
          "  The move also:",
          "    • Cuts off the 1 reply(ies) being written on the old backend."
        ],
        "expect_token": null,
        "found": true
      },
      "report": [
        {
          "supervisor": "container",
          "running": true,
          "pid": 4242,
          "unit": "thor-dashboard.service",
          "scope": "user",
          "state": "enabled",
          "this_home": true,
          "not_applied": "",
          "notes": []
        }
      ],
      "run": {
        "state": "none",
        "step": "",
        "steps": [],
        "message": "",
        "old_address": "",
        "new_address": "",
        "started_at": 0.0,
        "finished_at": null,
        "manual_steps": [],
        "reason": null
      },
      "profile": "default",
      "commands": {
        "status": "thor -p default gateway migrate --backends --status",
        "restore": "thor -p default gateway migrate --backends --restore"
      }
    }
  },
  "unknown": {
    "held": {
      "applied": false,
      "dry_run": true,
      "exit_code": 3,
      "plan": {
        "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown",
        "old_backend": null,
        "old_address": null,
        "new_address": null,
        "keep_webapp_address": false,
        "copy_env_keys": [],
        "generate_secret": false,
        "public_url": null,
        "auth_before": null,
        "gateway": {},
        "linger": null,
        "webapp_bundle_missing": null,
        "running_turns": null,
        "blockers": [
          "Cannot tell whether turns are running on the old backend: these turn-marker files cannot be read, or hold a marker whose writer cannot be checked: /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown/desktop/interrupted_turns.json. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted)."
        ],
        "forceable_blockers": [
          "Cannot tell whether turns are running on the old backend: these turn-marker files cannot be read, or hold a marker whose writer cannot be checked: /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown/desktop/interrupted_turns.json. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted)."
        ],
        "takes_over": [
          "Cuts off any reply being written on the old backend (its chat activity cannot be read)."
        ],
        "unsupported": [
          {
            "supervisor": "container",
            "unit": "thor-dashboard.service",
            "pid": 4242,
            "instructions": "The backend runs in a container (Compose sidecar or docker run). Set webapp.enabled/host/port (below) in the mounted Thor home, drop the dashboard service from the Compose file, publish the same port on the gateway container, then `docker compose up -d`. Its Thor version could not be checked from outside its container, and a Thor older than v2026.7.30 does not record running chats: check inside the container that no reply is being written before you stop it.",
            "steps": []
          }
        ],
        "notices": [],
        "nothing_to_do": false,
        "steps": [],
        "text": [
          "Backend migration plan (dry run — nothing changed)",
          "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown",
          "  ✗ container thor-dashboard.service cannot be migrated automatically. Nothing changed.",
          "    The backend runs in a container (Compose sidecar or docker run). Set webapp.enabled/host/port (below) in the mounted Thor home, drop the dashboard service from the Compose file, publish the same port on the gateway container, then `docker compose up -d`. Its Thor version could not be checked from outside its container, and a Thor older than v2026.7.30 does not record running chats: check inside the container that no reply is being written before you stop it.",
          "    Steps, in this order (one command per line):",
          "",
          "  The move also:",
          "    • Cuts off any reply being written on the old backend (its chat activity cannot be read).",
          "",
          "  ✗ Blockers (nothing will be changed):",
          "    • Cannot tell whether turns are running on the old backend: these turn-marker files cannot be read, or hold a marker whose writer cannot be checked: /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown/desktop/interrupted_turns.json. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted)."
        ],
        "expect_token": null,
        "found": true
      },
      "report": [
        {
          "supervisor": "container",
          "running": true,
          "pid": 4242,
          "unit": "thor-dashboard.service",
          "scope": "user",
          "state": "enabled",
          "this_home": true,
          "not_applied": "",
          "notes": []
        }
      ],
      "run": {
        "state": "none",
        "step": "",
        "steps": [],
        "message": "",
        "old_address": "",
        "new_address": "",
        "started_at": 0.0,
        "finished_at": null,
        "manual_steps": [],
        "reason": null
      },
      "profile": "default",
      "commands": {
        "status": "thor -p default gateway migrate --backends --status",
        "restore": "thor -p default gateway migrate --backends --restore"
      }
    },
    "forced": {
      "applied": false,
      "dry_run": true,
      "exit_code": 6,
      "plan": {
        "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown",
        "old_backend": null,
        "old_address": null,
        "new_address": null,
        "keep_webapp_address": false,
        "copy_env_keys": [],
        "generate_secret": false,
        "public_url": null,
        "auth_before": null,
        "gateway": {},
        "linger": null,
        "webapp_bundle_missing": null,
        "running_turns": null,
        "blockers": [],
        "forceable_blockers": [],
        "takes_over": [
          "Cuts off any reply being written on the old backend (its chat activity cannot be read)."
        ],
        "unsupported": [
          {
            "supervisor": "container",
            "unit": "thor-dashboard.service",
            "pid": 4242,
            "instructions": "The backend runs in a container (Compose sidecar or docker run). Set webapp.enabled/host/port (below) in the mounted Thor home, drop the dashboard service from the Compose file, publish the same port on the gateway container, then `docker compose up -d`. Its Thor version could not be checked from outside its container, and a Thor older than v2026.7.30 does not record running chats: check inside the container that no reply is being written before you stop it. Its turn activity could not be read, so turns may be running on it now: stopping it interrupts them.",
            "steps": [
              "# in the mounted Thor home's config.yaml set webapp.enabled: true, webapp.host: 0.0.0.0, webapp.port: 9119",
              "# copy every THOR_DASHBOARD_* line from the old launcher's environment that /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown/.env does not already set, if any, into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown/.env (chmod 600)",
              "# remove the dashboard: recreate the container without THOR_DASHBOARD=1, or drop the Compose `dashboard` service and run: docker compose up -d --remove-orphans",
              "# publish 9119 on the gateway's container and restart it, so its gateway serves the address"
            ]
          }
        ],
        "notices": [],
        "nothing_to_do": false,
        "steps": [],
        "text": [
          "Backend migration plan (dry run — nothing changed)",
          "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown",
          "  ✗ container thor-dashboard.service cannot be migrated automatically. Nothing changed.",
          "    The backend runs in a container (Compose sidecar or docker run). Set webapp.enabled/host/port (below) in the mounted Thor home, drop the dashboard service from the Compose file, publish the same port on the gateway container, then `docker compose up -d`. Its Thor version could not be checked from outside its container, and a Thor older than v2026.7.30 does not record running chats: check inside the container that no reply is being written before you stop it. Its turn activity could not be read, so turns may be running on it now: stopping it interrupts them.",
          "    Steps, in this order (one command per line):",
          "      # in the mounted Thor home's config.yaml set webapp.enabled: true, webapp.host: 0.0.0.0, webapp.port: 9119",
          "      # copy every THOR_DASHBOARD_* line from the old launcher's environment that /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown/.env does not already set, if any, into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/container-unknown/.env (chmod 600)",
          "      # remove the dashboard: recreate the container without THOR_DASHBOARD=1, or drop the Compose `dashboard` service and run: docker compose up -d --remove-orphans",
          "      # publish 9119 on the gateway's container and restart it, so its gateway serves the address",
          "",
          "  The move also:",
          "    • Cuts off any reply being written on the old backend (its chat activity cannot be read)."
        ],
        "expect_token": null,
        "found": true
      },
      "report": [
        {
          "supervisor": "container",
          "running": true,
          "pid": 4242,
          "unit": "thor-dashboard.service",
          "scope": "user",
          "state": "enabled",
          "this_home": true,
          "not_applied": "",
          "notes": []
        }
      ],
      "run": {
        "state": "none",
        "step": "",
        "steps": [],
        "message": "",
        "old_address": "",
        "new_address": "",
        "started_at": 0.0,
        "finished_at": null,
        "manual_steps": [],
        "reason": null
      },
      "profile": "default",
      "commands": {
        "status": "thor -p default gateway migrate --backends --status",
        "restore": "thor -p default gateway migrate --backends --restore"
      }
    }
  }
};

export const systemSystemdPlans = {
  "running": {
    "held": {
      "applied": false,
      "dry_run": true,
      "exit_code": 3,
      "plan": {
        "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-running",
        "old_backend": null,
        "old_address": null,
        "new_address": null,
        "keep_webapp_address": false,
        "copy_env_keys": [],
        "generate_secret": false,
        "public_url": null,
        "auth_before": null,
        "gateway": {},
        "linger": null,
        "webapp_bundle_missing": null,
        "running_turns": 1,
        "blockers": [
          "1 turn(s) are running on the old backend. Wait for them to finish, or re-run with --force-interrupt (they are interrupted)."
        ],
        "forceable_blockers": [
          "1 turn(s) are running on the old backend. Wait for them to finish, or re-run with --force-interrupt (they are interrupted)."
        ],
        "takes_over": [
          "Cuts off the 1 reply(ies) being written on the old backend."
        ],
        "unsupported": [
          {
            "supervisor": "systemd",
            "unit": "thor-dashboard.service",
            "pid": 4242,
            "instructions": "The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root. 1 turn(s) are running on it now: stopping it interrupts them, so let them finish first.",
            "steps": []
          }
        ],
        "notices": [],
        "nothing_to_do": false,
        "steps": [],
        "text": [
          "Backend migration plan (dry run — nothing changed)",
          "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-running",
          "  ✗ systemd thor-dashboard.service cannot be migrated automatically. Nothing changed.",
          "    The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root. 1 turn(s) are running on it now: stopping it interrupts them, so let them finish first.",
          "    Steps, in this order (one command per line):",
          "",
          "  The move also:",
          "    • Cuts off the 1 reply(ies) being written on the old backend.",
          "",
          "  ✗ Blockers (nothing will be changed):",
          "    • 1 turn(s) are running on the old backend. Wait for them to finish, or re-run with --force-interrupt (they are interrupted)."
        ],
        "expect_token": null,
        "found": true
      },
      "report": [
        {
          "supervisor": "systemd",
          "running": true,
          "pid": 4242,
          "unit": "thor-dashboard.service",
          "scope": "system",
          "state": "enabled",
          "this_home": true,
          "not_applied": "",
          "notes": []
        }
      ],
      "run": {
        "state": "none",
        "step": "",
        "steps": [],
        "message": "",
        "old_address": "",
        "new_address": "",
        "started_at": 0.0,
        "finished_at": null,
        "manual_steps": [],
        "reason": null
      },
      "profile": "default",
      "commands": {
        "status": "thor -p default gateway migrate --backends --status",
        "restore": "thor -p default gateway migrate --backends --restore"
      }
    },
    "forced": {
      "applied": false,
      "dry_run": true,
      "exit_code": 6,
      "plan": {
        "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-running",
        "old_backend": null,
        "old_address": null,
        "new_address": null,
        "keep_webapp_address": false,
        "copy_env_keys": [],
        "generate_secret": false,
        "public_url": null,
        "auth_before": null,
        "gateway": {},
        "linger": null,
        "webapp_bundle_missing": null,
        "running_turns": 1,
        "blockers": [],
        "forceable_blockers": [],
        "takes_over": [
          "Cuts off the 1 reply(ies) being written on the old backend."
        ],
        "unsupported": [
          {
            "supervisor": "systemd",
            "unit": "thor-dashboard.service",
            "pid": 4242,
            "instructions": "The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root. 1 turn(s) are running on it now: stopping it interrupts them, so let them finish first.",
            "steps": [
              "thor -p default webapp --build-only",
              "thor -p default config set webapp.enabled true",
              "thor -p default config set webapp.host 0.0.0.0",
              "thor -p default config set webapp.port 9119",
              "# copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old launcher's environment into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-running/.env, then: chmod 600 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-running/.env  (values are never printed here)",
              "sudo systemctl disable --now thor-dashboard.service",
              "systemctl is-active thor-dashboard.service  # must print inactive (or failed) before the next line",
              "thor -p default gateway status",
              "# then by what it prints: 'Gateway is not running' (no service installed) -> thor -p default gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> thor -p default gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> thor -p default gateway restart",
              "# the gateway takes a few seconds to serve the address: if the next line prints 'The gateway is not running', wait 5 seconds and run it again",
              "thor -p default webapp --status"
            ]
          }
        ],
        "notices": [],
        "nothing_to_do": false,
        "steps": [],
        "text": [
          "Backend migration plan (dry run — nothing changed)",
          "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-running",
          "  ✗ systemd thor-dashboard.service cannot be migrated automatically. Nothing changed.",
          "    The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root. 1 turn(s) are running on it now: stopping it interrupts them, so let them finish first.",
          "    Steps, in this order (one command per line):",
          "      thor -p default webapp --build-only",
          "      thor -p default config set webapp.enabled true",
          "      thor -p default config set webapp.host 0.0.0.0",
          "      thor -p default config set webapp.port 9119",
          "      # copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old launcher's environment into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-running/.env, then: chmod 600 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-running/.env  (values are never printed here)",
          "      sudo systemctl disable --now thor-dashboard.service",
          "      systemctl is-active thor-dashboard.service  # must print inactive (or failed) before the next line",
          "      thor -p default gateway status",
          "      # then by what it prints: 'Gateway is not running' (no service installed) -> thor -p default gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> thor -p default gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> thor -p default gateway restart",
          "      # the gateway takes a few seconds to serve the address: if the next line prints 'The gateway is not running', wait 5 seconds and run it again",
          "      thor -p default webapp --status",
          "",
          "  The move also:",
          "    • Cuts off the 1 reply(ies) being written on the old backend."
        ],
        "expect_token": null,
        "found": true
      },
      "report": [
        {
          "supervisor": "systemd",
          "running": true,
          "pid": 4242,
          "unit": "thor-dashboard.service",
          "scope": "system",
          "state": "enabled",
          "this_home": true,
          "not_applied": "",
          "notes": []
        }
      ],
      "run": {
        "state": "none",
        "step": "",
        "steps": [],
        "message": "",
        "old_address": "",
        "new_address": "",
        "started_at": 0.0,
        "finished_at": null,
        "manual_steps": [],
        "reason": null
      },
      "profile": "default",
      "commands": {
        "status": "thor -p default gateway migrate --backends --status",
        "restore": "thor -p default gateway migrate --backends --restore"
      }
    }
  },
  "unknown": {
    "held": {
      "applied": false,
      "dry_run": true,
      "exit_code": 3,
      "plan": {
        "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown",
        "old_backend": null,
        "old_address": null,
        "new_address": null,
        "keep_webapp_address": false,
        "copy_env_keys": [],
        "generate_secret": false,
        "public_url": null,
        "auth_before": null,
        "gateway": {},
        "linger": null,
        "webapp_bundle_missing": null,
        "running_turns": null,
        "blockers": [
          "Cannot tell whether turns are running on the old backend: these turn-marker files cannot be read, or hold a marker whose writer cannot be checked: /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown/desktop/interrupted_turns.json. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted)."
        ],
        "forceable_blockers": [
          "Cannot tell whether turns are running on the old backend: these turn-marker files cannot be read, or hold a marker whose writer cannot be checked: /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown/desktop/interrupted_turns.json. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted)."
        ],
        "takes_over": [
          "Cuts off any reply being written on the old backend (its chat activity cannot be read)."
        ],
        "unsupported": [
          {
            "supervisor": "systemd",
            "unit": "thor-dashboard.service",
            "pid": 4242,
            "instructions": "The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root.",
            "steps": []
          }
        ],
        "notices": [],
        "nothing_to_do": false,
        "steps": [],
        "text": [
          "Backend migration plan (dry run — nothing changed)",
          "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown",
          "  ✗ systemd thor-dashboard.service cannot be migrated automatically. Nothing changed.",
          "    The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root.",
          "    Steps, in this order (one command per line):",
          "",
          "  The move also:",
          "    • Cuts off any reply being written on the old backend (its chat activity cannot be read).",
          "",
          "  ✗ Blockers (nothing will be changed):",
          "    • Cannot tell whether turns are running on the old backend: these turn-marker files cannot be read, or hold a marker whose writer cannot be checked: /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown/desktop/interrupted_turns.json. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted)."
        ],
        "expect_token": null,
        "found": true
      },
      "report": [
        {
          "supervisor": "systemd",
          "running": true,
          "pid": 4242,
          "unit": "thor-dashboard.service",
          "scope": "system",
          "state": "enabled",
          "this_home": true,
          "not_applied": "",
          "notes": []
        }
      ],
      "run": {
        "state": "none",
        "step": "",
        "steps": [],
        "message": "",
        "old_address": "",
        "new_address": "",
        "started_at": 0.0,
        "finished_at": null,
        "manual_steps": [],
        "reason": null
      },
      "profile": "default",
      "commands": {
        "status": "thor -p default gateway migrate --backends --status",
        "restore": "thor -p default gateway migrate --backends --restore"
      }
    },
    "forced": {
      "applied": false,
      "dry_run": true,
      "exit_code": 6,
      "plan": {
        "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown",
        "old_backend": null,
        "old_address": null,
        "new_address": null,
        "keep_webapp_address": false,
        "copy_env_keys": [],
        "generate_secret": false,
        "public_url": null,
        "auth_before": null,
        "gateway": {},
        "linger": null,
        "webapp_bundle_missing": null,
        "running_turns": null,
        "blockers": [],
        "forceable_blockers": [],
        "takes_over": [
          "Cuts off any reply being written on the old backend (its chat activity cannot be read)."
        ],
        "unsupported": [
          {
            "supervisor": "systemd",
            "unit": "thor-dashboard.service",
            "pid": 4242,
            "instructions": "The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root. Its turn activity could not be read, so turns may be running on it now: stopping it interrupts them.",
            "steps": [
              "thor -p default webapp --build-only",
              "thor -p default config set webapp.enabled true",
              "thor -p default config set webapp.host 0.0.0.0",
              "thor -p default config set webapp.port 9119",
              "# copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old launcher's environment into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown/.env, then: chmod 600 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown/.env  (values are never printed here)",
              "sudo systemctl disable --now thor-dashboard.service",
              "systemctl is-active thor-dashboard.service  # must print inactive (or failed) before the next line",
              "thor -p default gateway status",
              "# then by what it prints: 'Gateway is not running' (no service installed) -> thor -p default gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> thor -p default gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> thor -p default gateway restart",
              "# the gateway takes a few seconds to serve the address: if the next line prints 'The gateway is not running', wait 5 seconds and run it again",
              "thor -p default webapp --status"
            ]
          }
        ],
        "notices": [],
        "nothing_to_do": false,
        "steps": [],
        "text": [
          "Backend migration plan (dry run — nothing changed)",
          "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown",
          "  ✗ systemd thor-dashboard.service cannot be migrated automatically. Nothing changed.",
          "    The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root. Its turn activity could not be read, so turns may be running on it now: stopping it interrupts them.",
          "    Steps, in this order (one command per line):",
          "      thor -p default webapp --build-only",
          "      thor -p default config set webapp.enabled true",
          "      thor -p default config set webapp.host 0.0.0.0",
          "      thor -p default config set webapp.port 9119",
          "      # copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old launcher's environment into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown/.env, then: chmod 600 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/system-unknown/.env  (values are never printed here)",
          "      sudo systemctl disable --now thor-dashboard.service",
          "      systemctl is-active thor-dashboard.service  # must print inactive (or failed) before the next line",
          "      thor -p default gateway status",
          "      # then by what it prints: 'Gateway is not running' (no service installed) -> thor -p default gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> thor -p default gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> thor -p default gateway restart",
          "      # the gateway takes a few seconds to serve the address: if the next line prints 'The gateway is not running', wait 5 seconds and run it again",
          "      thor -p default webapp --status",
          "",
          "  The move also:",
          "    • Cuts off any reply being written on the old backend (its chat activity cannot be read)."
        ],
        "expect_token": null,
        "found": true
      },
      "report": [
        {
          "supervisor": "systemd",
          "running": true,
          "pid": 4242,
          "unit": "thor-dashboard.service",
          "scope": "system",
          "state": "enabled",
          "this_home": true,
          "not_applied": "",
          "notes": []
        }
      ],
      "run": {
        "state": "none",
        "step": "",
        "steps": [],
        "message": "",
        "old_address": "",
        "new_address": "",
        "started_at": 0.0,
        "finished_at": null,
        "manual_steps": [],
        "reason": null
      },
      "profile": "default",
      "commands": {
        "status": "thor -p default gateway migrate --backends --status",
        "restore": "thor -p default gateway migrate --backends --restore"
      }
    }
  }
};

export const refusedUrlPlans = {
  "held": {
    "applied": false,
    "dry_run": true,
    "exit_code": 3,
    "plan": {
      "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/refused-url",
      "old_backend": null,
      "old_address": null,
      "new_address": null,
      "keep_webapp_address": false,
      "copy_env_keys": [],
      "generate_secret": false,
      "public_url": null,
      "auth_before": null,
      "gateway": {},
      "linger": null,
      "webapp_bundle_missing": null,
      "running_turns": null,
      "blockers": [
        "The old backend's public URL (dashboard.public_url) is not one the gateway accepts as webapp.public_url: it must be http:// or https:// with no credentials, query or fragment. Fix it, or set webapp.public_url yourself (its value is not printed here)."
      ],
      "forceable_blockers": [],
      "takes_over": [],
      "unsupported": [
        {
          "supervisor": "systemd",
          "unit": "thor-dashboard.service",
          "pid": 4242,
          "instructions": "The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root.",
          "steps": []
        }
      ],
      "notices": [],
      "nothing_to_do": false,
      "steps": [],
      "text": [
        "Backend migration plan (dry run — nothing changed)",
        "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/refused-url",
        "  ✗ systemd thor-dashboard.service cannot be migrated automatically. Nothing changed.",
        "    The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root.",
        "    Steps, in this order (one command per line):",
        "",
        "  ✗ Blockers (nothing will be changed):",
        "    • The old backend's public URL (dashboard.public_url) is not one the gateway accepts as webapp.public_url: it must be http:// or https:// with no credentials, query or fragment. Fix it, or set webapp.public_url yourself (its value is not printed here)."
      ],
      "expect_token": null,
      "found": true
    },
    "report": [
      {
        "supervisor": "systemd",
        "running": true,
        "pid": 4242,
        "unit": "thor-dashboard.service",
        "scope": "system",
        "state": "enabled",
        "this_home": true,
        "not_applied": "",
        "notes": []
      }
    ],
    "run": {
      "state": "none",
      "step": "",
      "steps": [],
      "message": "",
      "old_address": "",
      "new_address": "",
      "started_at": 0.0,
      "finished_at": null,
      "manual_steps": [],
      "reason": null
    },
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  },
  "forced": {
    "applied": false,
    "dry_run": true,
    "exit_code": 3,
    "plan": {
      "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/refused-url",
      "old_backend": null,
      "old_address": null,
      "new_address": null,
      "keep_webapp_address": false,
      "copy_env_keys": [],
      "generate_secret": false,
      "public_url": null,
      "auth_before": null,
      "gateway": {},
      "linger": null,
      "webapp_bundle_missing": null,
      "running_turns": null,
      "blockers": [
        "The old backend's public URL (dashboard.public_url) is not one the gateway accepts as webapp.public_url: it must be http:// or https:// with no credentials, query or fragment. Fix it, or set webapp.public_url yourself (its value is not printed here)."
      ],
      "forceable_blockers": [],
      "takes_over": [],
      "unsupported": [
        {
          "supervisor": "systemd",
          "unit": "thor-dashboard.service",
          "pid": 4242,
          "instructions": "The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root.",
          "steps": []
        }
      ],
      "notices": [],
      "nothing_to_do": false,
      "steps": [],
      "text": [
        "Backend migration plan (dry run — nothing changed)",
        "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/refused-url",
        "  ✗ systemd thor-dashboard.service cannot be migrated automatically. Nothing changed.",
        "    The backend is a systemd SYSTEM unit: this command changes no system unit, and thor -p default cannot run as root on a per-user install. Run the steps below as yourself; only the one `sudo systemctl` line needs root.",
        "    Steps, in this order (one command per line):",
        "",
        "  ✗ Blockers (nothing will be changed):",
        "    • The old backend's public URL (dashboard.public_url) is not one the gateway accepts as webapp.public_url: it must be http:// or https:// with no credentials, query or fragment. Fix it, or set webapp.public_url yourself (its value is not printed here)."
      ],
      "expect_token": null,
      "found": true
    },
    "report": [
      {
        "supervisor": "systemd",
        "running": true,
        "pid": 4242,
        "unit": "thor-dashboard.service",
        "scope": "system",
        "state": "enabled",
        "this_home": true,
        "not_applied": "",
        "notes": []
      }
    ],
    "run": {
      "state": "none",
      "step": "",
      "steps": [],
      "message": "",
      "old_address": "",
      "new_address": "",
      "started_at": 0.0,
      "finished_at": null,
      "manual_steps": [],
      "reason": null
    },
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  }
};
