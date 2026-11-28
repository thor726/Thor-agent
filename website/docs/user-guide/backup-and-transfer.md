---
sidebar_position: 8
title: "Backup & Transfer"
description: "Back up your whole agent, or replace a Thor Cloud agent with it, from Settings"
---

# Backup & Transfer

**Settings ▸ Backup & Transfer** in Thor Desktop (and the Webapp) backs up your whole
agent to one file. Transfer to Thor Cloud used to replace one of your Thor Cloud
agents with this agent; that is retired with the Thor Portal (see below).

## Back up

**Back up** runs [`thor backup`](../reference/cli-commands.md#thor-backup) on the agent Settings is showing, then asks where to save the zip. The zip holds the whole Thor home: every profile, memory, persona, skills, conversations, scheduled jobs, settings, and your keys and logins (`.env`, `auth.json`). Keep it private. To restore it, run `thor import <zip>`.

## Transfer to Thor Cloud — retired

Transfer to Thor Cloud is retired with the Thor Portal: cloud agents lived on the
Portal, and ThorHub has no cloud-agents API, so there is no cloud agent to list or
replace anymore. The **Back up** part above still works, and you can still move an
agent to another machine yourself with `thor backup` on this computer and
`thor import <zip> --keep-host` on the other one (see [From the command line](#from-the-command-line)).

## From the command line

```bash
thor backup -o my-agent.zip                 # on this computer
# copy my-agent.zip to the cloud agent, then on it:
thor import my-agent.zip --keep-host        # prints the undo point
thor import <undo point> --force --keep-host   # undo
```

[`thor import --keep-host`](../reference/cli-commands.md#--keep-host-replace-an-agent-but-keep-its-hosts-setup) lists exactly what it keeps.
