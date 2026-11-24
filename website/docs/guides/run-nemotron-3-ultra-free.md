---
sidebar_position: 0
title: "Run Nemotron 3 Ultra free in Thor Agent"
description: "Try NVIDIA Nemotron 3 Ultra free via NVIDIA NIM, with day 0 support in Thor Agent"
---

# Run Nemotron 3 Ultra free in Thor Agent

Thor Labs has been inducted into the **Nemotron Coalition** of leading AI labs working with **NVIDIA** to advance open frontier foundation models. In honor of this, **Nemotron 3 Ultra** was free for two weeks (**June 4th – June 18th**). Follow the instructions below to try the model in your Thor Agent today.

:::danger Offer ended — Nous Portal removed

The free June 4–18 offer on Nous Portal has ended, and Nous Portal itself has been **removed from Thor Agent**. The steps below now use NVIDIA NIM instead: get a free API key at [build.nvidia.com](https://build.nvidia.com/settings/api-keys) and run the model as the `nvidia` provider.
:::

:::info Limited-time offer
The `nvidia/nemotron-3-ultra:free` tier is available from **June 4th to June 18th**. The `:free` tag is what keeps it on the no-cost plan — pick that exact variant.
:::

Pick whichever install fits you. The **desktop app** is the easiest — no terminal required. If you live in a terminal, the **command-line** install is right below it.

## Option A — Desktop app (recommended)

The simplest path: a one-click installer with a guided, point-and-click setup. No terminal needed.

### 1. Download and install

[Download the Thor Desktop installer](https://github.com/thor726/Thor-agent/) for macOS or Windows, then open it. On first launch it finishes setting itself up (usually under a minute).

### 2. Connect NVIDIA NIM

When the app opens, you'll see a "Let's get you set up" screen. Choose **NVIDIA NIM** and enter a free API key from [build.nvidia.com](https://build.nvidia.com/settings/api-keys). The app connects automatically.

### 3. Pick the free Nemotron 3 Ultra model

After connecting, the app shows a **Default model** card. Click **Change**, search for **nemotron 3 ultra**, and select the variant tagged **Free tier**:

```
nvidia/nemotron-3-ultra:free
```

The `:free` tag is what keeps it on the no-cost tier — pick that variant.

### 4. Start chatting

Click **Start chatting**. That's it — you're talking to Nemotron 3 Ultra, free.

## Option B — Command line

Prefer the terminal?

### 1. Install Thor Agent

On macOS/Linux/WSL2/Android, run

```bash
curl -fsSL https://raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.sh | bash
```

On Windows, run

```powershell
iex (irm https://raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.ps1)
```

Prefer to review first? Download [`install.sh`](https://raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.sh), inspect it, then run it.

After it finishes, reload your shell:

```bash
source ~/.bashrc   # or source ~/.zshrc
```

### 2. Run Quick Setup

```bash
thor setup
```

Select **Quick Setup**. Thor opens a browser tab and waits for you to finish the next steps.

### 3. Get a free NVIDIA NIM key

Create an account and a free API key at [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys), and add it to `~/.thor/.env`:

```bash
NVIDIA_API_KEY=<redacted>
```

### 4. Connect the NVIDIA provider

When prompted, pick the **NVIDIA NIM** provider. You'll see a confirmation once it's linked.

### 5. Select the free Nemotron 3 Ultra model

Return to your terminal. From the model list, select:

```
nvidia/nemotron-3-ultra:free
```

The `:free` tag is what keeps it on the no-cost tier, so make sure you pick that variant.

### 6. Start chatting

Complete the remaining Quick Setup prompts, then run:

```bash
thor
```

That's it — you're talking to Nemotron 3 Ultra, free.

## Switching to it later

Already set up with another model?

- **Desktop app:** open the model picker, search for **nemotron 3 ultra**, and select the **Free tier** variant.
- **CLI / TUI:** switch any time from inside a session with `/model nvidia/nemotron-3-ultra:free`, or run `/model` to open the picker and choose it from the list.

## Troubleshooting

- **Don't see the model in the list?** Make sure you finished the NVIDIA NIM setup above and picked the `:free` variant. In the CLI, `thor model` shows your current provider.
- **Picked the wrong variant?** Re-select `nvidia/nemotron-3-ultra:free` — the `:free` suffix is required to stay on the no-cost tier.
- **Browser didn't open / you're on a remote host (CLI)?** See [OAuth over SSH / Remote Hosts](./oauth-over-ssh.md) for port-forwarding workarounds.

## See also

- **[Desktop App](../user-guide/desktop.md)** — The native one-click app (macOS, Windows, Linux)
- **[NVIDIA NIM](../integrations/providers.md#nvidia-nim)** — Free API key setup for Nemotron models
- **[Quickstart](../getting-started/quickstart.md)** — Install-to-chat in under 5 minutes
