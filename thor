#!/usr/bin/env python3
"""
Thor Agent CLI launcher.

This wrapper should behave like the installed `thor` command, including
subcommands such as `gateway`, `cron`, and `doctor`.
"""

if __name__ == "__main__":
    from thor_cli.main import main
    main()
