---
title: Official Domains & Phishing Safety
description: How to verify you are using genuine Thor Agent resources, and how to spot impersonation scams.
---

# Official Domains & Phishing Safety

Thor Agent's popularity has attracted impersonation campaigns: fake "Thor" websites, GitHub accounts that mass-mention contributors with shortlinks, and cold emails offering "credits" on lookalike products. This page lists the official sources so you can check anything that claims to be Thor Agent.

## Official sources

Nous Research operates `nousresearch.com` and its subdomains. The ones Thor Agent uses:

| Address | What it is |
|---|---|
| [thor-agent.nousresearch.com](https://thor-agent.nousresearch.com/) | Documentation, Desktop downloads, and the `install.sh` / `install.ps1` installers |
| `thor-assets.nousresearch.com` | Release artifacts: Desktop packages and updates, the Termux APT repository, installer mirrors |
| [portal.nousresearch.com](https://portal.nousresearch.com/) | Nous Portal: account sign-in, subscriptions, billing |
| `inference-api.nousresearch.com` | The Nous inference API Thor calls when you use the Nous provider (no web page) |
| [nousresearch.com](https://nousresearch.com/) | Nous Research website |

Outside `nousresearch.com`:

- **GitHub:** the [NousResearch organization](https://github.com/NousResearch) and its [thor-agent repository](https://github.com/NousResearch/thor-agent) (source, releases, the Nix flake). Raw files from that repository are served from `raw.githubusercontent.com/NousResearch/thor-agent/...`; that is the same repository, not a separate source. Any other account or repository is not ours.
- **Docker Hub:** the [`nousresearch/thor-agent`](https://hub.docker.com/r/nousresearch/thor-agent) image, published by the repository's release workflow (see [Docker](../user-guide/docker.md)). Only the `nousresearch` namespace is official; images under other names or registries are not.
- **X (Twitter):** [@NousResearch](https://x.com/NousResearch)
- **Discord:** [discord.gg/NousResearch](https://discord.gg/NousResearch)

## Installing from an official source

The script installers are served from `thor-agent.nousresearch.com`:

```bash
# Linux / macOS / WSL2
curl -fsSL https://thor-agent.nousresearch.com/install.sh | bash
```

```powershell
# Windows (native)
iex (irm https://thor-agent.nousresearch.com/install.ps1)
```

The other supported routes also stay on official sources: Desktop packages download from the [Thor website](https://thor-agent.nousresearch.com/), Termux uses the signed APT repository on `thor-assets.nousresearch.com` (see the [Termux guide](./termux.md), not the script above), Nix builds from the GitHub repository (see [Nix & NixOS](./nix-setup.md)), and Docker pulls `nousresearch/thor-agent` from Docker Hub. Some guides fetch `install.ps1` straight from the repository at `raw.githubusercontent.com/NousResearch/thor-agent/main/scripts/install.ps1`; it is the same script.

If an installer, download, image, or "portal" is hosted anywhere other than the sources listed on this page, treat it as untrusted.

## Not official

- **Any domain that is not `nousresearch.com` or one of its subdomains** (apart from the accounts listed above), even when it contains "thor" or "thor-agent" (`.icu`, `.org`, `.ai` and other variants), copies the branding, or says it "points to official docs". Read the whole host name: `thor-agent.nousresearch.com.example.net` is not a Nous Research subdomain.
- **Cryptocurrency tokens.** There is **no Thor Agent or Nous Research token**. Any account or site promoting one is a scam.
- **GitHub accounts that mass-mention users** in discussions or issues with "community notice" posts and URL-shortener links (`goo.su`, `bit.ly`, etc.). Genuine project announcements never arrive as mass @-mentions with shortlinks.
- **Unsolicited emails** offering credits, hosted "multiplayer Thor" products, or partnership deals that name-drop the project to build trust.

## If you receive a suspicious message

1. **Don't click** shortened or off-domain links; don't enter credentials or connect wallets.
2. **Report the account** to GitHub (`Report abuse` on the profile) or the relevant platform.
3. **Check the host name** against the rule above: if it is not `nousresearch.com` or a subdomain of it, and not one of the accounts listed here, it isn't ours.
4. Optionally flag it in the [Nous Research Discord](https://discord.gg/NousResearch) or an issue so others see it, but note that impersonation campaigns are external abuse: they're handled by platform reports, not code changes.

Thor Agent is MIT-licensed and free to self-host. Nobody legitimate will ever ask you to pay for the open-source agent itself, claim "your account has credits waiting", or DM you an alternate download link.
