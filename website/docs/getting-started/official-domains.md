---
title: Official Domains & Phishing Safety
description: How to verify you are using genuine Thor Agent resources, and how to spot impersonation scams.
---

# Official Domains & Phishing Safety

Thor Agent's popularity can attract impersonation campaigns: fake "Thor" websites, GitHub accounts that mass-mention contributors with shortlinks, and cold emails offering "credits" on lookalike products. This page lists the official sources so you can check anything that claims to be Thor Agent.

## Official sources

This project is maintained in the `thor726` GitHub account. The sources Thor Agent uses:

| Address | What it is |
|---|---|
| [thor726.github.io/Thor-agent](https://thor726.github.io/Thor-agent/) | Documentation and the docs-hosted catalogs (skills index, plugin catalog) |
| [github.com/thor726/Thor-agent](https://github.com/thor726/Thor-agent) | Source code, releases, issue tracker |
| `raw.githubusercontent.com/thor726/Thor-agent/...` | Raw files from the same repository — including the `install.sh` / `install.ps1` installers — not a separate source |
| [github.com/thor726/Thor-agent/releases](https://github.com/thor726/Thor-agent/releases) | Release artifacts: Desktop packages and updates when published |

Outside GitHub:

- **Docker Hub:** the [`thorlabs/thor-agent`](https://hub.docker.com/r/thorlabs/thor-agent) image, published by the repository's release workflow (see [Docker](../user-guide/docker.md)). Only the `thorlabs` namespace is official; images under other names or registries are not.
- **X (Twitter):** [@thor726](https://x.com/thor726)
- **Discord:** [discord.gg/thor726](https://discord.gg/thor726)

## Installing from an official source

The script installers are served from this repository:

```bash
# Linux / macOS / WSL2
curl -fsSL https://raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.sh | bash
```

```powershell
# Windows (native)
iex (irm https://raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.ps1)
```

The other supported routes also stay on official sources: Desktop packages download from GitHub Releases, Nix builds from the GitHub repository (see [Nix & NixOS](./nix-setup.md)), and Docker pulls `thorlabs/thor-agent` from Docker Hub.

If an installer, download, image, or "portal" is hosted anywhere other than the sources listed on this page, treat it as untrusted.

## Not official

- **Any domain that is not `github.com/thor726`, `thor726.github.io`, or `raw.githubusercontent.com/thor726`** (apart from the accounts listed above), even when it contains "thor" or "thor-agent" (`.icu`, `.org`, `.ai`, `.local` and other variants), copies the branding, or says it "points to official docs". Read the whole host name: `thor-agent.example.net` and `thor-agent.thor-agent.local` are not this project's domains.
- **Cryptocurrency tokens.** There is **no Thor Agent token**. Any account or site promoting one is a scam.
- **GitHub accounts that mass-mention users** in discussions or issues with "community notice" posts and URL-shortener links (`goo.su`, `bit.ly`, etc.). Genuine project announcements never arrive as mass @-mentions with shortlinks.
- **Unsolicited emails** offering credits, hosted "multiplayer Thor" products, or partnership deals that name-drop the project to build trust.

## If you receive a suspicious message

1. **Don't click** shortened or off-domain links; don't enter credentials or connect wallets.
2. **Report the account** to GitHub (`Report abuse` on the profile) or the relevant platform.
3. **Check the host name** against the rule above: if it is not one of the sources listed here, it isn't ours.
4. Optionally flag it in the [Discord](https://discord.gg/thor726) or an issue so others see it, but note that impersonation campaigns are external abuse: they're handled by platform reports, not code changes.

Thor Agent is MIT-licensed and free to self-host. Nobody legitimate will ever ask you to pay for the open-source agent itself, claim "your account has credits waiting", or DM you an alternate download link.
