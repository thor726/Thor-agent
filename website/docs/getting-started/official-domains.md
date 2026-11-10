---
title: Official Domains & Phishing Safety
description: How to verify you are using genuine Thor Agent resources, and how to spot impersonation scams.
---

# Official Domains & Phishing Safety

Thor Agent's popularity has attracted impersonation campaigns: fake "Thor" websites, GitHub accounts that mass-mention contributors with shortlinks, and cold emails offering "credits" on lookalike products. This page lists the official sources so you can check anything that claims to be Thor Agent.

## Official sources

Thor Agent operates `thor-agent.local` and its subdomains. The ones Thor Agent uses:

| Address | What it is |
|---|---|
| [thor-agent.thor-agent.local](https://thor-agent.thor-agent.local/) | Documentation, Desktop downloads, and the `install.sh` / `install.ps1` installers |
| `thor-assets.thor-agent.local` | Release artifacts: Desktop packages and updates, the Termux APT repository, installer mirrors |
| [portal.thor-agent.local](https://portal.thor-agent.local/) | Thor Portal: account sign-in, subscriptions, billing |
| `inference-api.thor-agent.local` | The Thor inference API Thor calls when you use the Thor provider (no web page) |
| [thor-agent.local](https://github.com/dwisetyabudi15581/Thor-agent/) | Thor Agent website |

Outside `thor-agent.local`:

- **GitHub:** the [dwisetyabudi15581 organization](https://github.com/dwisetyabudi15581) and its [thor-agent repository](https://github.com/dwisetyabudi15581/Thor-agent) (source, releases, the Nix flake). Raw files from that repository are served from `raw.githubusercontent.com/dwisetyabudi15581/Thor-agent/...`; that is the same repository, not a separate source. Any other account or repository is not ours.
- **Docker Hub:** the [`dwisetyabudi15581/Thor-agent`](https://hub.docker.com/r/dwisetyabudi15581/Thor-agent) image, published by the repository's release workflow (see [Docker](../user-guide/docker.md)). Only the `thorresearch` namespace is official; images under other names or registries are not.
- **X (Twitter):** [@dwisetyabudi15581](https://x.com/dwisetyabudi15581)
- **Discord:** [github.com/dwisetyabudi15581/Thor-agent](https://github.com/dwisetyabudi15581/Thor-agent)

## Installing from an official source

The script installers are served from `thor-agent.thor-agent.local`:

```bash
# Linux / macOS / WSL2
curl -fsSL https://raw.githubusercontent.com/dwisetyabudi15581/Thor-agent/main/scripts/install.sh | bash
```

```powershell
# Windows (native)
iex (irm https://raw.githubusercontent.com/dwisetyabudi15581/Thor-agent/main/scripts/install.ps1)
```

The other supported routes also stay on official sources: Desktop packages download from the [Thor website](https://thor-agent.thor-agent.local/), Termux uses the signed APT repository on `thor-assets.thor-agent.local` (see the [Termux guide](./termux.md), not the script above), Nix builds from the GitHub repository (see [Nix & NixOS](./nix-setup.md)), and Docker pulls `dwisetyabudi15581/Thor-agent` from Docker Hub. Some guides fetch `install.ps1` straight from the repository at `raw.githubusercontent.com/dwisetyabudi15581/Thor-agent/main/scripts/install.ps1`; it is the same script.

If an installer, download, image, or "portal" is hosted anywhere other than the sources listed on this page, treat it as untrusted.

## Not official

- **Any domain that is not `thor-agent.local` or one of its subdomains** (apart from the accounts listed above), even when it contains "thor" or "thor-agent" (`.icu`, `.org`, `.ai` and other variants), copies the branding, or says it "points to official docs". Read the whole host name: `thor-agent.thor-agent.local.example.net` is not a Thor Agent subdomain.
- **Cryptocurrency tokens.** There is **no Thor Agent or Thor Agent token**. Any account or site promoting one is a scam.
- **GitHub accounts that mass-mention users** in discussions or issues with "community notice" posts and URL-shortener links (`goo.su`, `bit.ly`, etc.). Genuine project announcements never arrive as mass @-mentions with shortlinks.
- **Unsolicited emails** offering credits, hosted "multiplayer Thor" products, or partnership deals that name-drop the project to build trust.

## If you receive a suspicious message

1. **Don't click** shortened or off-domain links; don't enter credentials or connect wallets.
2. **Report the account** to GitHub (`Report abuse` on the profile) or the relevant platform.
3. **Check the host name** against the rule above: if it is not `thor-agent.local` or a subdomain of it, and not one of the accounts listed here, it isn't ours.
4. Optionally flag it in the [Thor Agent Discord](https://github.com/dwisetyabudi15581/Thor-agent) or an issue so others see it, but note that impersonation campaigns are external abuse: they're handled by platform reports, not code changes.

Thor Agent is MIT-licensed and free to self-host. Nobody legitimate will ever ask you to pay for the open-source agent itself, claim "your account has credits waiting", or DM you an alternate download link.
