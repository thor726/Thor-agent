// Engine outputs, captured from Thor's own engine (Fase 5, adaptasi A13).
// Do not hand-edit the payloads: re-run the capture script instead:
//   scripts/capture_backend_migration_fixtures.py [--check | --write DIR]

export const unknownActivityBlocker = "Cannot tell whether turns are running on the old backend: these turn-marker files cannot be read, or hold a marker whose writer cannot be checked: /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/unknown-activity/desktop/interrupted_turns.json. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted).";

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

export const refusalBlockers = {
  "configBackend": "THOR_CONFIG_BACKEND=remote keeps the settings outside config.yaml, but the migration backs up, rolls back and restores only config.yaml, so it needs the file config backend. Move this home by hand with the steps in the docs. Nothing changed.",
  "providers": "The old backend requires sign-in but its sign-in providers could not be read (127.0.0.1:9119/api/auth/providers did not answer), so the move could not check that the gateway offers the same ones. Check that the old backend answers there, then run this again. Nothing changed.",
  "managed": "The managed config /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/managed/config.yaml sets webapp.port, which the gateway applies after this home's config.yaml: after the move its Webapp would serve 0.0.0.0:8000 instead of serving 0.0.0.0:9119, so the old backend would be stopped for nothing. Have the administrator change that setting, then run this again. Nothing changed.",
  "guardPath": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/refuse-guard/systemd-user/thor-dashboard.service.d/thor-migrated.conf already exists; move it aside before migrating this backend."
};

export const relativeLauncherStatus = {
  "state": "failed",
  "step": "preflight",
  "steps": [
    {
      "name": "preflight",
      "state": "failed"
    }
  ],
  "message": "the background migration did not start (exit 3): the old backend was started by a relative path and its working directory could not be read; nothing changed",
  "old_address": "",
  "new_address": "",
  "started_at": 1795766770.593347,
  "finished_at": 1795766770.593347,
  "manual_steps": [],
  "refused": true,
  "reason": null,
  "log_tail": [],
  "launcher": null,
  "served_by": "dashboard",
  "now": 1795766770.604277,
  "profile": "default",
  "commands": {
    "status": "thor -p default gateway migrate --backends --status",
    "restore": "thor -p default gateway migrate --backends --restore"
  }
};

export const lateTurnStatus = {
  "running": {
    "state": "rolled_back",
    "step": "gateway_service",
    "steps": [
      {
        "name": "preflight",
        "state": "done"
      },
      {
        "name": "manifest",
        "state": "done"
      },
      {
        "name": "webapp_bundle",
        "state": "undone"
      },
      {
        "name": "write_config",
        "state": "undone"
      },
      {
        "name": "gateway_service",
        "state": "undone"
      },
      {
        "name": "stop_old_backend",
        "state": "pending"
      },
      {
        "name": "start_gateway",
        "state": "pending"
      },
      {
        "name": "verify",
        "state": "pending"
      }
    ],
    "message": "gateway_service failed: 1 turn(s) are running on the old backend. Wait for them to finish, or re-run with --force-interrupt (they are interrupted). The old backend has not been stopped.; rolled back, old backend verified on 0.0.0.0:9119",
    "old_address": "0.0.0.0:9119",
    "new_address": "0.0.0.0:9119",
    "started_at": 1795766770.6198583,
    "finished_at": 1795766770.6612804,
    "manual_steps": [],
    "reason": "gateway_service failed: 1 turn(s) are running on the old backend. Wait for them to finish, or re-run with --force-interrupt (they are interrupted). The old backend has not been stopped.",
    "log_tail": [],
    "launcher": null,
    "served_by": "dashboard",
    "now": 1795766770.6859434,
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  },
  "unknown": {
    "state": "rolled_back",
    "step": "gateway_service",
    "steps": [
      {
        "name": "preflight",
        "state": "done"
      },
      {
        "name": "manifest",
        "state": "done"
      },
      {
        "name": "webapp_bundle",
        "state": "undone"
      },
      {
        "name": "write_config",
        "state": "undone"
      },
      {
        "name": "gateway_service",
        "state": "undone"
      },
      {
        "name": "stop_old_backend",
        "state": "pending"
      },
      {
        "name": "start_gateway",
        "state": "pending"
      },
      {
        "name": "verify",
        "state": "pending"
      }
    ],
    "message": "gateway_service failed: Cannot tell whether turns are running on the old backend: its turn activity could not be read. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted). The old backend has not been stopped.; rolled back, old backend verified on 0.0.0.0:9119",
    "old_address": "0.0.0.0:9119",
    "new_address": "0.0.0.0:9119",
    "started_at": 1795766770.7142057,
    "finished_at": 1795766770.7624867,
    "manual_steps": [],
    "reason": "gateway_service failed: Cannot tell whether turns are running on the old backend: its turn activity could not be read. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted). The old backend has not been stopped.",
    "log_tail": [],
    "launcher": null,
    "served_by": "dashboard",
    "now": 1795766770.7800562,
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  }
};

export const killedWhileWritingStatus = {
  "config": {
    "state": "failed",
    "step": "write_config",
    "steps": [
      {
        "name": "preflight",
        "state": "done"
      },
      {
        "name": "manifest",
        "state": "done"
      },
      {
        "name": "webapp_bundle",
        "state": "done"
      },
      {
        "name": "write_config",
        "state": "done"
      },
      {
        "name": "gateway_service",
        "state": "pending"
      },
      {
        "name": "stop_old_backend",
        "state": "pending"
      },
      {
        "name": "start_gateway",
        "state": "pending"
      },
      {
        "name": "verify",
        "state": "pending"
      }
    ],
    "message": "interrupted at write_config; rollback incomplete: restored config.yaml: the migration stopped while writing /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/killed-config/config.yaml, so it may hold the migration's changes; it was not written back; did not start the old backend again: the migrated gateway may still own its address",
    "old_address": "0.0.0.0:9119",
    "new_address": "0.0.0.0:9119",
    "started_at": 1795766770.8073704,
    "finished_at": 1795766770.827576,
    "manual_steps": [
      "thor -p default gateway stop",
      "the migration stopped while writing /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/killed-config/config.yaml, so it may hold the migration's changes: compare it with /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/killed-config/backend_migration/config.yaml.bak and put back by hand what the migration changed, before you start the old backend",
      "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/killed-config/.env was restored from its backup (nothing to do for it)",
      "thor -p default gateway uninstall",
      "systemctl --user enable thor-dashboard.service",
      "systemctl --user start thor-dashboard.service"
    ],
    "reason": "interrupted at write_config",
    "log_tail": [],
    "launcher": null,
    "served_by": "dashboard",
    "now": 1795766770.839078,
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  },
  "env": {
    "state": "failed",
    "step": "write_config",
    "steps": [
      {
        "name": "preflight",
        "state": "done"
      },
      {
        "name": "manifest",
        "state": "done"
      },
      {
        "name": "webapp_bundle",
        "state": "done"
      },
      {
        "name": "write_config",
        "state": "done"
      },
      {
        "name": "gateway_service",
        "state": "pending"
      },
      {
        "name": "stop_old_backend",
        "state": "pending"
      },
      {
        "name": "start_gateway",
        "state": "pending"
      },
      {
        "name": "verify",
        "state": "pending"
      }
    ],
    "message": "interrupted at write_config; rollback incomplete: restored .env: the migration stopped while writing /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/killed-env/.env, so it may hold the migration's changes; it was not written back; did not start the old backend again: the migrated gateway may still own its address",
    "old_address": "0.0.0.0:9119",
    "new_address": "0.0.0.0:9119",
    "started_at": 1795766770.8538814,
    "finished_at": 1795766770.860607,
    "manual_steps": [
      "thor -p default gateway stop",
      "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/killed-env/config.yaml was restored from its backup (nothing to do for it)",
      "the migration stopped while writing /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/killed-env/.env, so it may hold the migration's changes: compare it with /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/killed-env/backend_migration/env.bak and put back by hand what the migration changed, before you start the old backend",
      "thor -p default gateway uninstall",
      "systemctl --user enable thor-dashboard.service",
      "systemctl --user start thor-dashboard.service"
    ],
    "reason": "interrupted at write_config",
    "log_tail": [],
    "launcher": null,
    "served_by": "dashboard",
    "now": 1795766770.887378,
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  }
};

export const restoreRefusedStatus = {
  "envMissing": {
    "state": "failed",
    "step": "preflight",
    "steps": [
      {
        "name": "preflight",
        "state": "failed"
      }
    ],
    "message": "the background restore did not start (exit 3): the backup of .env (/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-envMissing/backend_migration/env.bak) cannot be read: No such file or directory; a restore would overwrite it, so nothing was written: your edits were kept and the gateway keeps serving; nothing changed",
    "old_address": "",
    "new_address": "",
    "started_at": 1795766770.950568,
    "finished_at": 1795766770.950568,
    "manual_steps": [
      "thor -p default gateway stop",
      "cp /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-envMissing/backend_migration/config.yaml.bak /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-envMissing/config.yaml",
      "the backup /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-envMissing/backend_migration/env.bak of .env is missing or cannot be read: recover it, or put /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-envMissing/.env back as it was before the migration by hand, before you start the old backend",
      "thor -p default gateway uninstall",
      "systemctl --user enable thor-dashboard.service",
      "systemctl --user start thor-dashboard.service"
    ],
    "refused": true,
    "reason": null,
    "log_tail": [],
    "launcher": null,
    "served_by": "dashboard",
    "now": 1795766770.9610124,
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  },
  "configMissing": {
    "state": "failed",
    "step": "preflight",
    "steps": [
      {
        "name": "preflight",
        "state": "failed"
      }
    ],
    "message": "the background restore did not start (exit 3): the backup of config.yaml (/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-configMissing/backend_migration/config.yaml.bak) cannot be read: No such file or directory; a restore would overwrite it, so nothing was written: your edits were kept and the gateway keeps serving; nothing changed",
    "old_address": "",
    "new_address": "",
    "started_at": 1795766771.009588,
    "finished_at": 1795766771.009588,
    "manual_steps": [
      "thor -p default gateway stop",
      "the backup /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-configMissing/backend_migration/config.yaml.bak of config.yaml is missing or cannot be read: recover it, or put /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-configMissing/config.yaml back as it was before the migration by hand, before you start the old backend",
      "cp /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-configMissing/backend_migration/env.bak /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-configMissing/.env && chmod 660 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-configMissing/.env",
      "thor -p default gateway uninstall",
      "systemctl --user enable thor-dashboard.service",
      "systemctl --user start thor-dashboard.service"
    ],
    "refused": true,
    "reason": null,
    "log_tail": [],
    "launcher": null,
    "served_by": "dashboard",
    "now": 1795766771.022473,
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  },
  "bothMissing": {
    "state": "failed",
    "step": "preflight",
    "steps": [
      {
        "name": "preflight",
        "state": "failed"
      }
    ],
    "message": "the background restore did not start (exit 3): the backup of config.yaml (/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-bothMissing/backend_migration/config.yaml.bak) cannot be read: No such file or directory; a restore would overwrite it, so nothing was written: your edits were kept and the gateway keeps serving; nothing changed",
    "old_address": "",
    "new_address": "",
    "started_at": 1795766771.0711417,
    "finished_at": 1795766771.0711417,
    "manual_steps": [
      "thor -p default gateway stop",
      "the backup /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-bothMissing/backend_migration/config.yaml.bak of config.yaml is missing or cannot be read: recover it, or put /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-bothMissing/config.yaml back as it was before the migration by hand, before you start the old backend",
      "the backup /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-bothMissing/backend_migration/env.bak of .env is missing or cannot be read: recover it, or put /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/restore-bothMissing/.env back as it was before the migration by hand, before you start the old backend",
      "thor -p default gateway uninstall",
      "systemctl --user enable thor-dashboard.service",
      "systemctl --user start thor-dashboard.service"
    ],
    "refused": true,
    "reason": null,
    "log_tail": [],
    "launcher": null,
    "served_by": "dashboard",
    "now": 1795766771.0812335,
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  }
};

export const unknownStateStatus = {
  "state": "failed",
  "step": "",
  "steps": [],
  "message": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/unknown-state/backend_migration.json has an unrecognized migration state; nothing can be undone automatically",
  "old_address": "",
  "new_address": "",
  "started_at": 0.0,
  "finished_at": null,
  "manual_steps": [],
  "reason": null,
  "log_tail": [],
  "launcher": null,
  "served_by": "dashboard",
  "now": 1795766771.1043203,
  "profile": "default",
  "commands": {
    "status": "thor -p default gateway migrate --backends --status",
    "restore": "thor -p default gateway migrate --backends --restore"
  }
};

export const changedBackendStatus = {
  "state": "rolled_back",
  "step": "gateway_service",
  "steps": [
    {
      "name": "preflight",
      "state": "done"
    },
    {
      "name": "manifest",
      "state": "done"
    },
    {
      "name": "webapp_bundle",
      "state": "undone"
    },
    {
      "name": "write_config",
      "state": "undone"
    },
    {
      "name": "gateway_service",
      "state": "undone"
    },
    {
      "name": "stop_old_backend",
      "state": "pending"
    },
    {
      "name": "start_gateway",
      "state": "pending"
    },
    {
      "name": "verify",
      "state": "pending"
    }
  ],
  "message": "gateway_service failed: the old backend changed since the check (it was pid 4242 at the check and is pid 5242 now), so the stop would reach a process the checks never saw. The old backend has not been stopped; run this command again.; rolled back, old backend verified on 0.0.0.0:9119",
  "old_address": "0.0.0.0:9119",
  "new_address": "0.0.0.0:9119",
  "started_at": 1795766771.1204386,
  "finished_at": 1795766771.1553779,
  "manual_steps": [],
  "reason": "gateway_service failed: the old backend changed since the check (it was pid 4242 at the check and is pid 5242 now), so the stop would reach a process the checks never saw. The old backend has not been stopped; run this command again.",
  "log_tail": [],
  "launcher": null,
  "served_by": "dashboard",
  "now": 1795766771.1667619,
  "profile": "default",
  "commands": {
    "status": "thor -p default gateway migrate --backends --status",
    "restore": "thor -p default gateway migrate --backends --restore"
  }
};

export const nonFileBackendApply = {
  "precheck": {
    "ok": false,
    "error": "blocked",
    "message": "The move cannot start yet.",
    "blockers": [
      "THOR_CONFIG_BACKEND=remote keeps the settings outside config.yaml, but the migration backs up, rolls back and restores only config.yaml, so it needs the file config backend. Move this home by hand with the steps in the docs. Nothing changed."
    ]
  },
  "launcher": {
    "ok": false,
    "error": "not_started",
    "message": "THOR_CONFIG_BACKEND=remote keeps the settings outside config.yaml, but the migration backs up, rolls back and restores only config.yaml, so it needs the file config backend. Move this home by hand with the steps in the docs. Nothing changed.",
    "status_command": "thor -p default gateway migrate --backends --status"
  }
};

export const exit5BundleStatus = {
  "systemd": {
    "state": "failed",
    "step": "webapp_bundle",
    "steps": [
      {
        "name": "preflight",
        "state": "done"
      },
      {
        "name": "manifest",
        "state": "done"
      },
      {
        "name": "webapp_bundle",
        "state": "done"
      },
      {
        "name": "write_config",
        "state": "pending"
      },
      {
        "name": "gateway_service",
        "state": "pending"
      },
      {
        "name": "stop_old_backend",
        "state": "pending"
      },
      {
        "name": "start_gateway",
        "state": "pending"
      },
      {
        "name": "verify",
        "state": "pending"
      }
    ],
    "message": "webapp_bundle failed: the Webapp bundle is still missing after the build: dist/index.html is missing; rollback incomplete: old backend not verified: thor-dashboard.service is not active",
    "old_address": "0.0.0.0:9119",
    "new_address": "0.0.0.0:9119",
    "started_at": 1795766771.2291396,
    "finished_at": 1795766831.2520297,
    "manual_steps": [
      "thor -p default gateway stop",
      "cp /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-systemd/backend_migration/config.yaml.bak /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-systemd/config.yaml",
      "cp /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-systemd/backend_migration/env.bak /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-systemd/.env && chmod 660 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-systemd/.env",
      "thor -p default gateway uninstall",
      "systemctl --user enable thor-dashboard.service",
      "systemctl --user start thor-dashboard.service"
    ],
    "reason": "webapp_bundle failed: the Webapp bundle is still missing after the build: dist/index.html is missing",
    "log_tail": [],
    "launcher": null,
    "served_by": "dashboard",
    "now": 1795766831.2645605,
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  },
  "manual": {
    "state": "failed",
    "step": "webapp_bundle",
    "steps": [
      {
        "name": "preflight",
        "state": "done"
      },
      {
        "name": "manifest",
        "state": "done"
      },
      {
        "name": "webapp_bundle",
        "state": "done"
      },
      {
        "name": "write_config",
        "state": "pending"
      },
      {
        "name": "gateway_service",
        "state": "pending"
      },
      {
        "name": "stop_old_backend",
        "state": "pending"
      },
      {
        "name": "start_gateway",
        "state": "pending"
      },
      {
        "name": "verify",
        "state": "pending"
      }
    ],
    "message": "webapp_bundle failed: the Webapp bundle is still missing after the build: dist/index.html is missing; rollback incomplete: old backend not verified: thor-dashboard.service is not active",
    "old_address": "0.0.0.0:9119",
    "new_address": "0.0.0.0:9119",
    "started_at": 1795766831.2798154,
    "finished_at": 1795766891.299881,
    "manual_steps": [
      "thor -p default gateway stop",
      "cp /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-manual/backend_migration/config.yaml.bak /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-manual/config.yaml",
      "cp /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-manual/backend_migration/env.bak /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-manual/.env && chmod 660 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/exit5-manual/.env",
      "thor -p default gateway uninstall",
      "start the old backend again the way you started it before (it was pid 4242), so it serves 0.0.0.0:9119 again"
    ],
    "reason": "webapp_bundle failed: the Webapp bundle is still missing after the build: dist/index.html is missing",
    "log_tail": [],
    "launcher": null,
    "served_by": "dashboard",
    "now": 1795766891.3123229,
    "profile": "default",
    "commands": {
      "status": "thor -p default gateway migrate --backends --status",
      "restore": "thor -p default gateway migrate --backends --restore"
    }
  }
};

export const flagInPathBlockers = {
  "symlink": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/--force-interrupt/, then re-run with --force-interrupt (any running turn is interrupted)./h/config.yaml is a symbolic link: the migration would change the file it points to, which may be shared. Replace the link with a copy of the file (or move this home off the shared file), then run this again.",
  "unknown": "Cannot tell whether turns are running on the old backend: these turn-marker files cannot be read, or hold a marker whose writer cannot be checked: /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/--force-interrupt/, then re-run with --force-interrupt (any running turn is interrupted)./h/desktop/interrupted_turns.json. To move it, confirm it is idle, then re-run with --force-interrupt (any running turn is interrupted)."
};

export const engineStepStrings = [
  "# (an 'already exists' error from mkdir is fine)",
  "# The old backend's public URL (dashboard.public_url) is not a URL the gateway accepts (http:// or https://, no credentials, query or fragment): set webapp.public_url yourself (the value is not printed here)",
  "# and remove whatever starts it at sign-in",
  "# copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old backend's environment into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/w h/.env (values are never printed here)",
  "# copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old backend's environment into C:/Users/u/.thor/.env (values are never printed here)",
  "# copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old launcher's environment into /h/.env, then: chmod 600 /h/.env  (values are never printed here)",
  "# copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old launcher's environment into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env, then: chmod 600 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env  (values are never printed here)",
  "# copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old launcher's environment into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h/.env, then: chmod 600 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h/.env  (values are never printed here)",
  "# copy THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME from the old launcher's environment into C:/Users/u/.thor/.env, then: chmod 600 C:/Users/u/.thor/.env  (values are never printed here)",
  "# copy every THOR_DASHBOARD_* line from the old launcher's environment that /h/.env does not already set, if any, into /h/.env (chmod 600)",
  "# copy every THOR_DASHBOARD_* line from the old launcher's environment that /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env does not already set, if any, into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env (chmod 600)",
  "# copy every THOR_DASHBOARD_* line from the old launcher's environment that /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h/.env does not already set, if any, into /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h/.env (chmod 600)",
  "# copy the old backend's public URL (dashboard.public_url, or THOR_DASHBOARD_PUBLIC_URL in its environment) into webapp.public_url: open config.yaml with $env:THOR_HOME='C:/Users/u/.thor'; thor -p default config edit",
  "# enable the gateway service there, then run home-manager switch",
  "# enable the gateway service there, then run nixos-rebuild switch or home-manager switch",
  "# give the gateway every THOR_DASHBOARD_* variable the backend had through the environment file your Nix configuration provides (values are never printed here)",
  "# in the mounted Thor home's config.yaml set webapp.enabled: true, webapp.host: 0.0.0.0, webapp.port: 9119",
  "# in your Nix configuration: disable the thor backend service and set webapp.enabled: true, webapp.host: 0.0.0.0, webapp.port: 9119 in the Thor settings",
  "# publish 9119 on the gateway's container and restart it, so its gateway serves the address",
  "# remove the dashboard: recreate the container without THOR_DASHBOARD=1, or drop the Compose `dashboard` service and run: docker compose up -d --remove-orphans",
  "# run the next line from your own supervisor (restart on exit and at boot):",
  "# set the old backend's address: $env:THOR_HOME='C:/Users/u/.thor'; thor -p default config set webapp.host HOST, then webapp.port PORT",
  "# set the old backend's address: THOR_HOME=/h thor config set webapp.host HOST, then webapp.port PORT",
  "# stop the old backend (Ctrl+C in its window)",
  "# stop the old backend through its supervisor and keep it from starting at boot",
  "# the gateway takes a few seconds to serve the address: if the next line prints 'The gateway is not running', wait 5 seconds and run it again",
  "# then by what it prints: 'Gateway is not running' (no service installed) -> $env:THOR_HOME='C:/Users/u/.thor'; thor -p default gateway install; 'No gateway process detected' -> $env:THOR_HOME='C:/Users/u/.thor'; thor -p default gateway start; 'Gateway process running' or 'Running manually' -> $env:THOR_HOME='C:/Users/u/.thor'; thor -p default gateway restart",
  "# then by what it prints: 'Gateway is not running' (no service installed) -> $env:THOR_HOME='\\var\\tmp\\thor-pytest-0\\r-hl2j8uj1\\pytest-of-root\\pytest-0\\test_capture_backend_migration0\\probe\\w h'; thor -p default gateway install; 'No gateway process detected' -> $env:THOR_HOME='\\var\\tmp\\thor-pytest-0\\r-hl2j8uj1\\pytest-of-root\\pytest-0\\test_capture_backend_migration0\\probe\\w h'; thor -p default gateway start; 'Gateway process running' or 'Running manually' -> $env:THOR_HOME='\\var\\tmp\\thor-pytest-0\\r-hl2j8uj1\\pytest-of-root\\pytest-0\\test_capture_backend_migration0\\probe\\w h'; thor -p default gateway restart",
  "# then by what it prints: 'Gateway is not running' (no service installed) -> THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor -p default gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor -p default gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor -p default gateway restart",
  "# then by what it prints: 'Gateway is not running' (no service installed) -> THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor gateway restart",
  "# then by what it prints: 'Gateway is not running' (no service installed) -> THOR_HOME=/h thor gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> THOR_HOME=/h thor gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> THOR_HOME=/h thor gateway restart",
  "# then by what it prints: 'Gateway is not running' (no service installed) -> THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor gateway restart",
  "# then by what it prints: 'Gateway is not running' (no service installed) -> THOR_HOME=/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home thor gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> THOR_HOME=/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home thor gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> THOR_HOME=/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home thor gateway restart",
  "# then by what it prints: 'Gateway is not running' (no service installed) -> thor -p default gateway install; 'service is stopped', 'service is not loaded' or 'registered with launchd' -> thor -p default gateway start; 'service is running', 'supervised by launchd' or 'Running manually' -> thor -p default gateway restart",
  "# these lines set THOR_HOME for this Thor root: run them in PowerShell, not Command Prompt",
  "# this Startup-folder entry starts the same command; if it is what starts this backend at sign-in, move it out of the Startup folder (Windows tries to open any file left there, even a renamed one):",
  "# to undo later: move \"/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/w h\\backend_migration\\Thor Dashboard.lnk\" \"C:\\Users\\u\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\Thor Dashboard.lnk\"",
  "# to undo later: move \"C:/Users/u/.thor\\backend_migration\\Thor Dashboard.lnk\" \"C:\\Users\\u\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\Thor Dashboard.lnk\"",
  "# to undo later: move \"C:/Users/u/.thor\\backend_migration\\thor-dashboard.service\" \"/home/u/.config/systemd/user/thor-dashboard.service\"",
  "$env:THOR_HOME='C:/Users/u/.thor'; thor -p default config set webapp.enabled true",
  "$env:THOR_HOME='C:/Users/u/.thor'; thor -p default config set webapp.host 0.0.0.0",
  "$env:THOR_HOME='C:/Users/u/.thor'; thor -p default config set webapp.host 127.0.0.1",
  "$env:THOR_HOME='C:/Users/u/.thor'; thor -p default config set webapp.port 9119",
  "$env:THOR_HOME='C:/Users/u/.thor'; thor -p default gateway status",
  "$env:THOR_HOME='C:/Users/u/.thor'; thor -p default webapp --build-only",
  "$env:THOR_HOME='C:/Users/u/.thor'; thor -p default webapp --status",
  "$env:THOR_HOME='\\var\\tmp\\thor-pytest-0\\r-hl2j8uj1\\pytest-of-root\\pytest-0\\test_capture_backend_migration0\\probe\\w h'; thor -p default config set webapp.enabled true",
  "$env:THOR_HOME='\\var\\tmp\\thor-pytest-0\\r-hl2j8uj1\\pytest-of-root\\pytest-0\\test_capture_backend_migration0\\probe\\w h'; thor -p default config set webapp.host 0.0.0.0",
  "$env:THOR_HOME='\\var\\tmp\\thor-pytest-0\\r-hl2j8uj1\\pytest-of-root\\pytest-0\\test_capture_backend_migration0\\probe\\w h'; thor -p default config set webapp.port 9119",
  "$env:THOR_HOME='\\var\\tmp\\thor-pytest-0\\r-hl2j8uj1\\pytest-of-root\\pytest-0\\test_capture_backend_migration0\\probe\\w h'; thor -p default gateway status",
  "$env:THOR_HOME='\\var\\tmp\\thor-pytest-0\\r-hl2j8uj1\\pytest-of-root\\pytest-0\\test_capture_backend_migration0\\probe\\w h'; thor -p default webapp --build-only",
  "$env:THOR_HOME='\\var\\tmp\\thor-pytest-0\\r-hl2j8uj1\\pytest-of-root\\pytest-0\\test_capture_backend_migration0\\probe\\w h'; thor -p default webapp --status",
  "/h/.env was restored from its backup (nothing to do for it)",
  "/h/config.yaml was restored from its backup (nothing to do for it)",
  "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env was restored from its backup (nothing to do for it)",
  "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/config.yaml was restored from its backup (nothing to do for it)",
  "C:/Users/u/.thor/.env was restored from its backup (nothing to do for it)",
  "C:/Users/u/.thor/config.yaml was restored from its backup (nothing to do for it)",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor -p default config set webapp.enabled true",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor -p default config set webapp.host 127.0.0.1",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor -p default config set webapp.port 9119",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor -p default gateway status",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor -p default webapp --build-only",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor -p default webapp --status",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor config set webapp.enabled true",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor config set webapp.host 0.0.0.0",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor config set webapp.host 127.0.0.1",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor config set webapp.port 9119",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor gateway status",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor webapp --build-only",
  "THOR_HOME='/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/x h' thor webapp --status",
  "THOR_HOME=/h thor config set webapp.enabled true",
  "THOR_HOME=/h thor config set webapp.host 127.0.0.1",
  "THOR_HOME=/h thor config set webapp.port 9119",
  "THOR_HOME=/h thor gateway status",
  "THOR_HOME=/h thor gateway stop",
  "THOR_HOME=/h thor gateway uninstall",
  "THOR_HOME=/h thor webapp --build-only",
  "THOR_HOME=/h thor webapp --status",
  "THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor config set webapp.enabled true",
  "THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor config set webapp.host 127.0.0.1",
  "THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor config set webapp.port 9119",
  "THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor gateway status",
  "THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor gateway stop",
  "THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor gateway uninstall",
  "THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor webapp --build-only",
  "THOR_HOME=/home/hatch/workspace/thor-port-migrate/C:/Users/u/.thor thor webapp --status",
  "THOR_HOME=/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home thor config set webapp.enabled true",
  "THOR_HOME=/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home thor config set webapp.host 127.0.0.1",
  "THOR_HOME=/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home thor config set webapp.port 9119",
  "THOR_HOME=/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home thor gateway status",
  "THOR_HOME=/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home thor webapp --build-only",
  "THOR_HOME=/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home thor webapp --status",
  "cp /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/backend_migration/config.yaml.bak /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/config.yaml",
  "cp /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/backend_migration/env.bak /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env && chmod 600 /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env",
  "keep /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env as it is (it was edited after the migration wrote it): merge the lines you need from /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/backend_migration/env.bak into it by hand before you start the old backend",
  "keep /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env as it is (it was edited after the migration wrote it): merge the lines you need from nothing (it did not exist before the migration) into it by hand before you start the old backend",
  "keep /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/config.yaml as it is (it was edited after the migration wrote it): merge the lines you need from /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/backend_migration/config.yaml.bak into it by hand before you start the old backend",
  "keep /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/config.yaml as it is (it was edited after the migration wrote it): merge the lines you need from nothing (it did not exist before the migration) into it by hand before you start the old backend",
  "mkdir \"/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/w h\\backend_migration\"",
  "mkdir \"C:/Users/u/.thor\\backend_migration\"",
  "move \"/home/u/.config/systemd/user/thor-dashboard.service\" \"C:/Users/u/.thor\\backend_migration\\thor-dashboard.service\"",
  "move \"C:\\Users\\u\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\Thor Dashboard.lnk\" \"/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/w h\\backend_migration\\Thor Dashboard.lnk\"",
  "move \"C:\\Users\\u\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\Thor Dashboard.lnk\" \"C:/Users/u/.thor\\backend_migration\\Thor Dashboard.lnk\"",
  "mv /Users/u/Library/LaunchAgents/ai.thor.dashboard.plist.disabled /Users/u/Library/LaunchAgents/ai.thor.dashboard.plist; launchctl enable gui/501/ai.thor.dashboard; launchctl bootstrap gui/501 /Users/u/Library/LaunchAgents/ai.thor.dashboard.plist",
  "rm -f /home/u/.config/systemd/user/thor-dashboard.service.d/thor-migrated.conf && systemctl --user daemon-reload",
  "rm /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env",
  "rm /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/config.yaml",
  "schtasks /Change /TN \"Thor Dashboard\" /DISABLE",
  "schtasks /Change /TN \"thor-dashboard.service\" /DISABLE",
  "schtasks /End /TN \"Thor Dashboard\"",
  "schtasks /End /TN \"thor-dashboard.service\"",
  "start the old backend again the way you started it before (it was pid 4242), so it serves 0.0.0.0:9119 again",
  "start the old backend again the way you started it before, so it serves 0.0.0.0:9119 again",
  "sudo systemctl disable --now thor-dashboard.service",
  "systemctl --user enable --runtime thor-dashboard.service",
  "systemctl --user enable thor-dashboard.service",
  "systemctl --user start thor-dashboard.service",
  "systemctl enable thor-dashboard.service",
  "systemctl is-active thor-dashboard.service  # must print inactive (or failed) before the next line",
  "systemctl start thor-dashboard.service",
  "taskkill /PID 4242 /T /F",
  "the backup /h/backend_migration/config.yaml.bak of config.yaml is missing or cannot be read: recover it, or put /h/config.yaml back as it was before the migration by hand, before you start the old backend",
  "the backup /h/backend_migration/env.bak of .env is missing or cannot be read: recover it, or put /h/.env back as it was before the migration by hand, before you start the old backend",
  "the backup /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/gone-env.bak of .env is missing or cannot be read: recover it, or put /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env back as it was before the migration by hand, before you start the old backend",
  "the backup /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/gone.bak of config.yaml is missing or cannot be read: recover it, or put /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/config.yaml back as it was before the migration by hand, before you start the old backend",
  "the backup C:/Users/u/.thor/backend_migration/config.yaml.bak of config.yaml is missing or cannot be read: recover it, or put C:/Users/u/.thor/config.yaml back as it was before the migration by hand, before you start the old backend",
  "the backup C:/Users/u/.thor/backend_migration/env.bak of .env is missing or cannot be read: recover it, or put C:/Users/u/.thor/.env back as it was before the migration by hand, before you start the old backend",
  "the migration stopped while writing /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/.env, so it may hold the migration's changes: compare it with /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/backend_migration/env.bak and put back by hand what the migration changed, before you start the old backend",
  "the migration stopped while writing /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/config.yaml, so it may hold the migration's changes: compare it with /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/probe/home/backend_migration/config.yaml.bak and put back by hand what the migration changed, before you start the old backend",
  "thor -p default config set webapp.enabled true",
  "thor -p default config set webapp.host 0.0.0.0",
  "thor -p default config set webapp.host 127.0.0.1",
  "thor -p default config set webapp.port 9119",
  "thor -p default config set webapp.public_url https://thor.example/",
  "thor -p default gateway run",
  "thor -p default gateway start",
  "thor -p default gateway status",
  "thor -p default gateway stop",
  "thor -p default gateway uninstall",
  "thor -p default webapp --build-only",
  "thor -p default webapp --status"
];

export const planWhileRunning = {
  "applied": false,
  "dry_run": true,
  "exit_code": 0,
  "plan": {
    "home": "/var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/plan-while-running",
    "old_backend": {
      "supervisor": "systemd",
      "unit": "thor-dashboard.service",
      "scope": "user",
      "pid": 4242,
      "unit_file_state": "enabled",
      "was_active": true
    },
    "old_address": "0.0.0.0:9119",
    "new_address": "0.0.0.0:9119",
    "keep_webapp_address": false,
    "copy_env_keys": [
      "THOR_DASHBOARD_BASIC_AUTH_PASSWORD",
      "THOR_DASHBOARD_BASIC_AUTH_SECRET",
      "THOR_DASHBOARD_BASIC_AUTH_USERNAME"
    ],
    "generate_secret": false,
    "public_url": null,
    "auth_before": {
      "auth_required": false,
      "providers": []
    },
    "gateway": {
      "kind": "systemd",
      "unit": "thor-gateway",
      "installed": true,
      "enabled": true,
      "active": false,
      "running_pid": null
    },
    "linger": true,
    "webapp_bundle_missing": null,
    "running_turns": 0,
    "blockers": [],
    "forceable_blockers": [],
    "takes_over": [],
    "unsupported": [],
    "notices": [],
    "nothing_to_do": false,
    "steps": [
      {
        "name": "preflight",
        "title": "check that the move can run (nothing changed yet)"
      },
      {
        "name": "manifest",
        "title": "record the current state in backend_migration.json (backups of config.yaml and .env)"
      },
      {
        "name": "webapp_bundle",
        "title": "check the Webapp bundle (built)"
      },
      {
        "name": "write_config",
        "title": "write .env and webapp.* (webapp.enabled, webapp.host, webapp.port)"
      },
      {
        "name": "gateway_service",
        "title": "make sure the gateway runs as a user service"
      },
      {
        "name": "stop_old_backend",
        "title": "stop the old backend and disable it (its unit file is kept)"
      },
      {
        "name": "start_gateway",
        "title": "start or restart the gateway"
      },
      {
        "name": "verify",
        "title": "verify 127.0.0.1:9119: /api/status 200 from the gateway and the Webapp page served, within 300 s"
      }
    ],
    "text": [
      "Backend migration plan (dry run — nothing changed)",
      "  home:          /var/tmp/thor-pytest-0/r-hl2j8uj1/pytest-of-root/pytest-0/test_capture_backend_migration0/plan-while-running",
      "  old backend:   systemd user unit thor-dashboard.service, pid 4242 on 0.0.0.0:9119",
      "  new backend:   the gateway's Webapp on 0.0.0.0:9119 (same bind and port: exposure unchanged)",
      "  sign-in:       not required",
      "  .env copies:   THOR_DASHBOARD_BASIC_AUTH_PASSWORD, THOR_DASHBOARD_BASIC_AUTH_SECRET, THOR_DASHBOARD_BASIC_AUTH_USERNAME (names only; values are never printed)",
      "  gateway:       installed, stopped (thor-gateway) → start it",
      "  webapp bundle: present",
      "  running turns: 0",
      "",
      "  Steps:",
      "    1. record the current state in backend_migration.json (backups of config.yaml and .env)",
      "    2. check the Webapp bundle (built)",
      "    3. write .env and webapp.* (webapp.enabled, webapp.host, webapp.port)",
      "    4. make sure the gateway runs as a user service",
      "    5. stop the old backend and disable it (its unit file is kept)",
      "    6. start or restart the gateway",
      "    7. verify 127.0.0.1:9119: /api/status 200 from the gateway and the Webapp page served, within 300 s",
      "  Any failure after step 1 undoes what was changed and verifies the old backend answers again.",
      "  After a move, clients notice: one re-sign-in (new cookies); the browser gets the Webapp instead of the old dashboard UI; old-protocol WebSocket clients and loopback page-token clients stop working."
    ],
    "expect_token": "b79b7fd5d86d5e654804c3c9094eef1a",
    "found": true
  },
  "report": [
    {
      "supervisor": "systemd",
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
    "state": "running",
    "step": "gateway_service",
    "steps": [
      {
        "name": "preflight",
        "state": "done"
      },
      {
        "name": "manifest",
        "state": "done"
      },
      {
        "name": "webapp_bundle",
        "state": "done"
      },
      {
        "name": "write_config",
        "state": "done"
      },
      {
        "name": "gateway_service",
        "state": "running"
      },
      {
        "name": "stop_old_backend",
        "state": "done"
      },
      {
        "name": "start_gateway",
        "state": "pending"
      },
      {
        "name": "verify",
        "state": "pending"
      }
    ],
    "message": "",
    "old_address": "0.0.0.0:9119",
    "new_address": "0.0.0.0:9119",
    "started_at": 1795766891.4633155,
    "finished_at": null,
    "manual_steps": [],
    "alive": true,
    "reason": null
  },
  "profile": "default",
  "commands": {
    "status": "thor -p default gateway migrate --backends --status",
    "restore": "thor -p default gateway migrate --backends --restore"
  }
};
