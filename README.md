<p align="center">
  <img src="assets/banner.png" alt="Thor Agent" width="100%">
</p>

# Thor Agent ☤
<p align="center">
  <a href="https://github.com/thor726/Thor-agent/">Thor Agent</a> | <a href="https://github.com/thor726/Thor-agent/">Thor Desktop</a>
</p>
<p align="center">
  <a href="https://thor726.github.io/Thor-agent/docs/"><img src="https://img.shields.io/badge/Docs-GitHub-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://github.com/thor726/thor-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/thor726/Thor-agent"><img src="https://img.shields.io/badge/Built%20by-Thor%20Labs-blueviolet?style=for-the-badge" alt="Built by Thor Labs"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/Lang-اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
</p>

**The self-improving AI agent by [Thor Labs](https://github.com/thor726/Thor-agent).** It's the only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations, and builds a deepening model of who you are across sessions. Run it on a $5 VPS, a GPU cluster, or serverless infrastructure that costs nearly nothing when idle. It's not tied to your laptop — talk to it from Telegram while it works on a cloud VM.

Use any model you want — [ThorHub](https://llm.thormarket.site), OpenRouter, OpenAI, your own endpoint, and [many others](https://thor726.github.io/Thor-agent/docs/integrations/providers). Switch with `thor model` — no code changes, no lock-in.

<table>
<tr><td><b>A real terminal interface</b></td><td>Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output.</td></tr>
<tr><td><b>Lives where you do</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal, and CLI — all from a single gateway process. Voice memo transcription, cross-platform conversation continuity.</td></tr>
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks. Skills self-improve during use. FTS5 session search with LLM summarization for cross-session recall. <a href="https://github.com/plastic-labs/honcho">Honcho</a> dialectic user modeling. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
<tr><td><b>Scheduled automations</b></td><td>Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — all in natural language, running unattended.</td></tr>
<tr><td><b>Delegates and parallelizes</b></td><td>Spawn isolated subagents for parallel workstreams. In Desktop, choose their provider, model, and limits under Settings → Model → Subagents, then Apply the complete route. Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns.</td></tr>
<tr><td><b>Runs anywhere, not just your laptop</b></td><td>Six built-in terminal backends — local, Docker, SSH, Modal, Daytona, and Vercel Sandbox — plus plugin backends such as Singularity/Apptainer. Daytona and Modal offer serverless persistence — your agent's environment hibernates when idle and wakes on demand, costing nearly nothing between sessions. Run it on a $5 VPS or a GPU cluster.</td></tr>
<tr><td><b>Research-ready</b></td><td>Batch trajectory generation, trajectory compression for training the next generation of tool-calling models.</td></tr>
</table>

---

## Quick Install

### Linux, macOS, WSL2

```bash
curl -fsSL https://raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.sh | bash
```

> That one-liner installs the latest version — including the ThorHub billing integration, where `/topup` shows your ThorHub balance.
>
> Already installed? Update to the latest version with `thor update`.

### Windows (native, PowerShell)

> **Heads up:** Native Windows runs Thor without WSL — CLI, gateway, TUI, and tools all work natively. If you'd rather use WSL2, the Linux/macOS one-liner above works there too. Found a bug? Please [file issues](https://github.com/thor726/thor-agent/issues).

Run this in PowerShell:

```powershell
iex "& { $(irm https://raw.githubusercontent.com/thor726/Thor-agent/main/scripts/install.ps1) }"
```

The source installer delegates Python 3.14, Node.js, npm, pnpm, ripgrep, FFmpeg,
and Python dependencies to PM. If Git is absent, it stages the verified Git
for Windows archive in Thor' tool store. It does not replace your system Git.
See [installation methods](https://thor726.github.io/Thor-agent/docs/getting-started/installation)
for the separate MSIX/App Installer package and its update ownership.

> **Android / Termux:** A signed APT repository is available for aarch64 devices, with a `stable` channel (tagged releases) and a prerelease `canary` channel. The package includes Python, Node.js, and the TUI. Use the [Termux guide](https://thor726.github.io/Thor-agent/docs/getting-started/termux), not the desktop/server installer script.
>
> **Windows:** Native Windows is fully supported — the PowerShell one-liner above installs everything. If you'd rather use WSL2, the Linux command works there too. Native Windows install lives under `%LOCALAPPDATA%\thor`; WSL2 installs under `~/.thor` as on Linux.

After installation:

```bash
source ~/.bashrc    # reload shell (or: source ~/.zshrc)
thor              # start chatting!
```

### Troubleshooting

#### Windows Defender or antivirus flags `uv.exe` as malware

If your antivirus (Bitdefender, Windows Defender, etc.) quarantines `uv.exe` from the Thor `bin` folder (`%LOCALAPPDATA%\thor\bin\uv.exe`), this is a **false positive**. The file is Astral's `uv` — the Rust Python package manager Thor bundles to manage its Python environment. ML-based antivirus engines commonly flag unsigned Rust binaries that download and install packages.

**To verify your copy is authentic:**

```powershell
# Install GitHub CLI if needed
winget install --id GitHub.cli

# Login to GitHub
gh auth login

# Run verification
$uv = "$env:LOCALAPPDATA\thor\bin\uv.exe"
$ver = (& $uv --version).Split(' ')[1]
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$zip = "$env:TEMP\uv.zip"
Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$ver/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip -UseBasicParsing
gh attestation verify $zip --repo astral-sh/uv
Expand-Archive $zip "$env:TEMP\uv_x" -Force
(Get-FileHash "$env:TEMP\uv_x\uv.exe").Hash -eq (Get-FileHash $uv).Hash
```

If attestation says "Verification succeeded" and the last line prints `True`, you're good.

**To whitelist Thor:**
- **Windows Defender:** Run PowerShell as Admin → `Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\thor\bin"`
- **Bitdefender:** Add an exception in the Bitdefender console (Protection > Antivirus > Settings > Manage Exceptions)
- Whitelist the **folder**, not the file hash — Thor updates `uv` and the hash changes every version

For more context, see the upstream Astral reports: [astral-sh/uv#13553](https://github.com/astral-sh/uv/issues/13553), [astral-sh/uv#15011](https://github.com/astral-sh/uv/issues/15011), [astral-sh/uv#10079](https://github.com/astral-sh/uv/issues/10079).

---

## Getting Started

```bash
thor              # Interactive CLI — start a conversation
thor model        # Choose your LLM provider and model
thor tools        # Configure which tools are enabled
thor config set   # Set individual config values
thor config get   # Print individual config values
thor gateway      # Start the messaging gateway (Telegram, Discord, etc.)
thor setup        # Run the full setup wizard (configures everything at once)
thor update       # Update to the latest version
thor doctor       # Diagnose any issues
```

📖 **[Full documentation →](https://thor726.github.io/Thor-agent/docs/)**

---

## Buy tokens with ThorHub

Thor works with whatever provider you want — that's not changing. Run `thor setup` and pick your own provider and model; each provider has its own API key and billing. That is the normal way to run Thor.

If you would rather buy tokens than manage a provider account, **[ThorHub](https://llm.thormarket.site)** is Thor's own token store: buy a token package at https://llm.thormarket.site/beli (QRIS), get a sub-key (`sk-thor-...`), and add it in Thor as a custom provider. Check your balance any time with `/topup` (when a ThorHub key is configured) and top up at https://llm.thormarket.site/beli/topup. Full details on the [ThorHub docs page](https://thor726.github.io/Thor-agent/docs/integrations/thorhub).

ThorHub is a paid token store, not a free tier — and it only covers model tokens, not web search, image generation, TTS, or a cloud browser. Those tools each need their own key, which you add with `thor tools`.

> Nous Portal, Thor Labs's old unified subscription gateway, has been **removed from Thor Agent**. There is no Portal OAuth login and no `thor setup --portal` anymore.

---

## CLI vs Messaging Quick Reference

Thor has two entry points: start the terminal UI with `thor`, or run the gateway and talk to it from Telegram, Discord, Slack, WhatsApp, Signal, or Email. Once you're in a conversation, many slash commands are shared across both interfaces.

| Action                         | CLI                                           | Messaging platforms                                                              |
| ------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- |
| Start chatting                 | `thor`                                      | Run `thor gateway setup` + `thor gateway start`, then send the bot a message |
| Start fresh conversation       | `/new` or `/reset`                            | `/new` or `/reset`                                                               |
| Change model                   | `/model [provider:model]`                     | `/model [provider:model]`                                                        |
| Set a personality              | `/personality [name]`                         | `/personality [name]`                                                            |
| Retry or undo the last turn    | `/retry`, `/undo`                             | `/retry`, `/undo`                                                                |
| Compress context / check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]`                                        |
| Browse skills                  | `/skills` or `/<skill-name>`                  | `/<skill-name>`                                                                  |
| Interrupt current work         | `Ctrl+C` or send a new message                | `/stop` or send a new message                                                    |
| Platform-specific status       | `/platforms`                                  | `/status`, `/sethome`                                                            |

For the full command lists, see the [CLI guide](https://thor726.github.io/Thor-agent/docs/user-guide/cli) and the [Messaging Gateway guide](https://thor726.github.io/Thor-agent/docs/user-guide/messaging).

---

## Documentation

All documentation lives at **[the documentation site](https://thor726.github.io/Thor-agent/docs/)**:

| Section                                                                                             | What's Covered                                             |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Quickstart](https://thor726.github.io/Thor-agent/docs/getting-started/quickstart)                 | Install → setup → first conversation in 2 minutes          |
| [CLI Usage](https://thor726.github.io/Thor-agent/docs/user-guide/cli)                              | Commands, keybindings, personalities, sessions             |
| [Configuration](https://thor726.github.io/Thor-agent/docs/user-guide/configuration)                | Config file, providers, models, all options                |
| [Messaging Gateway](https://thor726.github.io/Thor-agent/docs/user-guide/messaging)                | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant |
| [Security](https://thor726.github.io/Thor-agent/docs/user-guide/security)                          | Command approval, DM pairing, container isolation          |
| [Tools & Toolsets](https://thor726.github.io/Thor-agent/docs/user-guide/features/tools)            | 40+ tools, toolset system, terminal backends               |
| [Skills System](https://thor726.github.io/Thor-agent/docs/user-guide/features/skills)              | Procedural memory, Skills Hub, creating skills             |
| [Memory](https://thor726.github.io/Thor-agent/docs/user-guide/features/memory)                     | Persistent memory, user profiles, best practices           |
| [MCP Integration](https://thor726.github.io/Thor-agent/docs/user-guide/features/mcp)               | Connect any MCP server for extended capabilities           |
| [Cron Scheduling](https://thor726.github.io/Thor-agent/docs/user-guide/features/cron)              | Scheduled tasks with platform delivery                     |
| [Context Files](https://thor726.github.io/Thor-agent/docs/user-guide/features/context-files)       | Project context that shapes every conversation             |
| [Architecture](https://thor726.github.io/Thor-agent/docs/developer-guide/architecture)             | Project structure, agent loop, key classes                 |
| [Contributing](https://thor726.github.io/Thor-agent/docs/developer-guide/contributing)             | Development setup, PR process, code style                  |
| [CLI Reference](https://thor726.github.io/Thor-agent/docs/reference/cli-commands)                  | All commands and flags                                     |
| [Environment Variables](https://thor726.github.io/Thor-agent/docs/reference/environment-variables) | Complete env var reference                                 |

---

## Migrating from OpenClaw or another agent

If you're coming from OpenClaw, Claude Code, Codex CLI or Cursor, Thor can import your settings, memories and skills (and, for OpenClaw, API keys when you ask for them).

**During setup:** `thor setup` asks whether to import from another agent, pre-selects the ones it finds (`~/.openclaw`, `~/.claude`, `~/.codex`, `~/.cursor`), installs the official `agent-importers` plugin and runs the import with a preview first.

**Anytime after install:**

```bash
thor plugins install agent-importers          # once per profile
thor import-agent openclaw                    # interactive migration (full preset)
thor import-agent openclaw --dry-run          # preview what would be migrated
thor import-agent openclaw --migrate-secrets  # also bring allowlisted API keys
thor import-agent claude-code                 # or codex / cursor
```

What gets imported from OpenClaw:

- **SOUL.md** — persona file
- **Memories** — MEMORY.md and USER.md entries
- **Skills** — user-created skills → `~/.thor/skills/openclaw-imports/`
- **Command allowlist** — approval patterns
- **Messaging settings** — platform configs, allowed users, working directory
- **API keys** — allowlisted secrets (Telegram, OpenRouter, OpenAI, Anthropic, ElevenLabs), only with `--migrate-secrets`
- **TTS assets** — workspace audio files
- **Workspace instructions** — AGENTS.md (with `--workspace-target`)

`thor claw migrate` still works as the older spelling. See the [OpenClaw migration guide](https://thor726.github.io/Thor-agent/docs/guides/migrate-from-openclaw) and [Import from Other Agents](https://thor726.github.io/Thor-agent/docs/user-guide/import-from-other-agents).

---

## Contributing

We welcome contributions! See the [Contributing Guide](https://thor726.github.io/Thor-agent/docs/developer-guide/contributing) for development setup, code style, and PR process.

Start with the [PM developer workflow](website/docs/reference/package-management.md#developer-workflow)
for activation, daily use, dependency changes, and leaving the environment.
[Development Setup](CONTRIBUTING.md#development-setup) covers the separate test environment and verification commands.

---

## Community

- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/thor726/thor-agent/issues)
- 🔌 [computer-use-linux](https://github.com/avifenesh/computer-use-linux) — Linux desktop-control MCP server for Thor and other MCP hosts, with AT-SPI accessibility trees, Wayland/X11 input, screenshots, and compositor window targeting.
- 🔌 [ThorClaw](https://github.com/AaronWong1999/thorclaw) — Community WeChat bridge: Run Thor Agent and OpenClaw on the same WeChat account.

---

## License

MIT — see [LICENSE](LICENSE).

Built by [Thor Labs](https://github.com/thor726/Thor-agent).
