---
sidebar_position: 8
title: "Backup & Transfer"
description: "Back up your whole agent, or replace a Thor Cloud agent with it, from Settings"
---

# Backup & Transfer

**Settings ▸ Backup & Transfer** in Thor Desktop (and the Webapp) does two things:

- **Back up** saves your whole agent to one file.
- **Transfer to Thor Cloud** replaces one of your Thor Cloud agents with this agent. You can undo it.

On a Webapp that Thor Cloud itself serves, the section is called **Backup** and has only the backup. That tab already is a cloud agent.

## Back up

**Back up** runs [`thor backup`](../reference/cli-commands.md#thor-backup) on the agent Settings is showing, then asks where to save the zip. The zip holds the whole Thor home: every profile, memory, persona, skills, conversations, scheduled jobs, settings, and your keys and logins (`.env`, `auth.json`). Keep it private. To restore it, run `thor import <zip>`.

## Transfer to Thor Cloud

1. Sign in to Thor Portal if the section asks you to. It then lists your Thor Cloud agents.
2. Pick the agent to replace.
3. Read what gets replaced and what the agent keeps, tick **I understand this replaces &lt;agent&gt;**, and click **Replace &lt;agent&gt;**.

Thor checks that the cloud agent can receive a transfer (one older than this feature says it needs a Thor update), backs up this agent, copies the backup to the cloud agent a few megabytes at a time, and the cloud agent restores it with `thor import --keep-host --messaging-off`. Once its gateway has finished what it was doing, and before it changes anything, the cloud agent backs itself up. That backup is the undo point. **Cancel** is there while backing up and copying; once the restore has started it cannot be stopped, so the button goes away.

**What comes over:** memory, persona (SOUL.md), skills, conversations, scheduled jobs, every profile, settings, and your API keys and logins (other than Thor Portal). It replaces the agent: what the backup does not have is removed. A profile only the cloud agent has stays as it is. Never removed: the cloud agent's workspace and its own dotfiles (`.ssh`, `.gitconfig`, `.config`).

**What the cloud agent keeps:** its Thor Portal sign-in, its model and provider, its Thor Cloud tools (web, images, voice), its dashboard sign-in, and its scheduler settings. Thor Cloud set these up, and they already work there.

**Messaging bots** (Telegram, Discord, Slack…) come over with their tokens, allowlists and settings, but switched off on the cloud agent: a bot token can only be used by one running Thor at a time, so this computer keeps answering. The done screen names the bots that came over switched off. When you're ready, switch each one over on the **Messaging** page: off on this computer, on for the cloud agent. Undo puts the cloud agent's own bots back as they were.

**Undo** on the done screen restores the cloud agent from its undo point, and removes what the transfer added. If a transfer fails part-way, the error screen offers **Undo** as well as **Retry**; Undo always uses the first undo point, taken before anything changed. **Start again** goes back to the agent list.

**Signing in from the Webapp:** the Webapp uses this install's own Thor Portal sign-in (Settings ▸ Providers). If the browser is on another computer, the sign-in to the cloud agent ends on an address that computer can't open; paste that address into the field the section shows to finish.

**New cloud agent** opens Thor Portal, where you create one. Thor Desktop cannot create agents yet.

## From the command line

```bash
thor backup -o my-agent.zip                 # on this computer
# copy my-agent.zip to the cloud agent, then on it:
thor import my-agent.zip --keep-host        # prints the undo point
thor import <undo point> --force --keep-host   # undo
```

[`thor import --keep-host`](../reference/cli-commands.md#--keep-host-replace-an-agent-but-keep-its-hosts-setup) lists exactly what it keeps.
