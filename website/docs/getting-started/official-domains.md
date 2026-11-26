---
title: Official Domains & Phishing Safety
description: How to verify you are using genuine Thor Agent resources, and how to spot impersonation scams.
---

# Official Domains & Phishing Safety

Thor Agent's popularity has attracted impersonation campaigns: fake "Thor" websites, GitHub accounts that mass-mention contributors with shortlinks, and cold emails offering "credits" on lookalike products. This page lists the official sources so you can check anything that claims to be Thor Agent.

## Official sources

Thor Labs publishes Thor Agent through GitHub and ThorHub. The official addresses are:

| Address | What it is |
|---|---|
| [thor726.github.io/Thor-agent/docs](https://thor726.github.io/Thor-agent/docs/) | Documentation (this site) |
| [github.com/thor726/Thor-agent](https://github.com/thor726/Thor-agent) | Source code, Desktop downloads, releases, and the `install.sh` / `install.ps1` installers |
| [thor726.github.io/thor-agent-releases](https://thor726.github.io/thor-agent-releases/) | Release artifacts: Desktop update channels, the Termux APT repository, installer mirrors |
| [llm.thormarket.site](https://llm.thormarket.site) | ThorHub — API access, billing and top-up |

The old Nous Portal and the Nous inference API are gone; nothing under them is official anymore. Billing and top-up live at ThorHub (above).

Accounts:

- **GitHub:** the [thor726 organization](https://github.com/thor726) and its [Thor-agent repository](https://github.com/thor726/Thor-agent) (source, releases, the Nix flake). Raw files from that repository are served from `raw.githubusercontent.com/thor726/Thor-agent/...`; that is the same repository, not a separate source. Any other account or repository is not ours.
- **Docker Hub:** the [`thorlabs29/thor-agent`](https://hub.docker.com/r/thorlabs29/thor-agent) image, published by the repository's release workflow (see [Docker](../user-guide/docker.md)). Only the `thorlabs29` namespace is official; images under other names or registries are not.
- **X (Twitter):** [@thor726](https://x.com/thor726)

## Installing from an official source

The script installers are served from the GitHub repository:

```bash
# Linux / macOS / WSL2
curl -fsSL https://raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.sh | bash
```

```powershell
# Windows (native)
iex (irm https://raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.ps1)
```

The other supported routes also stay on official sources: Desktop packages download from the [GitHub repository](https://github.com/thor726/Thor-agent/), Termux uses the signed APT repository on `thor726.github.io/thor-agent-releases` (see the [Termux guide](./termux.md), not the script above), Nix builds from the GitHub repository (see [Nix & NixOS](./nix-setup.md)), and Docker pulls `thorlabs29/thor-agent` from Docker Hub. Some guides fetch `install.ps1` straight from the repository at `raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.ps1`; it is the same script.

If an installer, download, image, or "portal" is hosted anywhere other than the sources listed on this page, treat it as untrusted.

## Not official

- **Any domain that is not listed on this page**, even when it contains "thor" or "thor-agent" (`.icu`, `.org`, `.ai` and other variants), copies the branding, or says it "points to official docs". Read the whole host name: `thor726.github.io.example.net` is not our GitHub Pages site.
- **Cryptocurrency tokens.** There is **no Thor Agent or Thor Labs token**. Any account or site promoting one is a scam.
- **GitHub accounts that mass-mention users** in discussions or issues with "community notice" posts and URL-shortener links (`goo.su`, `bit.ly`, etc.). Genuine project announcements never arrive as mass @-mentions with shortlinks.
- **Unsolicited emails** offering credits, hosted "multiplayer Thor" products, or partnership deals that name-drop the project to build trust.

## If you receive a suspicious message

1. **Don't click** shortened or off-domain links; don't enter credentials or connect wallets.
2. **Report the account** to GitHub (`Report abuse` on the profile) or the relevant platform.
3. **Check the host name** against the rule above: if it is not one of the addresses or accounts listed here, it isn't ours.
4. Optionally flag it in an issue so others see it, but note that impersonation campaigns are external abuse: they're handled by platform reports, not code changes.

Thor Agent is MIT-licensed and free to self-host. Nobody legitimate will ever ask you to pay for the open-source agent itself, claim "your account has credits waiting", or DM you an alternate download link.
