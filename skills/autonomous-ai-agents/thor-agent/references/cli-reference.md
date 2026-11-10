# Thor CLI Reference

Live sources when anything looks stale: `thor --help`, `thor <command> --help`,
https://thor-agent.nousresearch.com/docs/reference/cli-commands

### Global Flags

```
thor [flags] [command]        (no subcommand = interactive chat)

  --version, -V             Show version
  -z, --oneshot PROMPT      One-shot: print ONLY the final response (for scripts/pipes)
  -m MODEL  --provider P    Model/provider override for this invocation
  -t, --toolsets LIST       Comma-separated toolsets for this invocation
  --resume, -r SESSION      Resume session by ID or title
  --continue, -c [NAME]     Resume by name, or most recent session
  --worktree, -w            Isolated git worktree mode (parallel agents)
  --skills, -s SKILL        Preload skills (comma-separate or repeat)
  --profile, -p NAME        Use a named profile
  --yolo                    Skip dangerous command approval
  --tui / --cli             Force the Ink TUI / classic REPL
  --ignore-rules            Skip AGENTS.md/SOUL.md/memory/skill injection
  --safe-mode               Disable ALL customizations (troubleshooting)
  --pass-session-id         Include session ID in system prompt
```

### Chat

```
thor chat [flags]
  -q, --query TEXT          Single query, non-interactive
  --image PATH              Attach a local image to a single query
  -Q, --quiet               Suppress banner, spinner, tool previews
  --checkpoints             Enable filesystem checkpoints (/rollback)
  --max-turns N             Cap tool-calling iterations
  --source TAG              Session source tag (default: cli)
```
(plus the global flags above)

### Configuration

```
thor setup [section]      Wizard (model|tts|terminal|gateway|tools|agent)
thor model                Interactive model/provider picker
thor fallback [add|remove|list]  Fallback provider chain
thor config [show|edit|get|set|unset|path|env-path|check|migrate]
thor login / logout       OAuth sign-in / clear stored auth
thor doctor [--fix]       Check dependencies and config
thor status [--full]      Component summary (--full: every section)
```

### Tools & Skills

```
thor tools [list|enable NAME|disable NAME]   Per-platform toolsets (curses UI with no args)

thor skills list|browse|search QUERY|inspect ID
thor skills install ID    Hub identifier OR a direct https://…/SKILL.md URL
thor skills config        Enable/disable skills per platform
thor skills check|update|uninstall|publish PATH
thor skills tap add REPO  Add a GitHub repo as a skill source
thor bundles              Skill bundles (one /<name> alias loads several skills)
```

### MCP Servers

```
thor mcp add NAME (--url or --command) | remove | list | test NAME
thor mcp catalog | install NAME     Curated catalog install
thor mcp configure NAME             Toggle tool selection
thor mcp-serve                      Run Thor as an MCP server (mcp-serve plugin)
```
Details (transport, tool discovery, catalog): `references/native-mcp.md`.

### Gateway (Messaging Platforms)

```
thor gateway run|install|start|stop|restart|status|setup
```

20+ platforms: Telegram, Discord, Slack, WhatsApp (Baileys + Business Cloud API), iMessage (Photon — `thor photon setup`), Signal, Email, SMS, Matrix, Mattermost, Teams, LINE, SimpleX, ntfy, Google Chat, Home Assistant, DingTalk, Feishu, WeCom, Weixin, API Server, Webhooks. Open WebUI connects via the API Server adapter. Most adapters ship under `plugins/platforms/`.
Docs: https://thor-agent.nousresearch.com/docs/user-guide/messaging/

### Sessions

```
thor sessions list|browse|rename ID TITLE|delete ID|export OUT|prune|stats
```

### Cron / Webhooks

```
thor cron list|create SCHED|edit ID|pause|resume|run ID|remove|status
    Schedules: '30m', 'every 2h', '0 9 * * *', ISO timestamp
thor webhook subscribe NAME|list|remove NAME|test NAME
```
Webhook payloads/routes: `references/webhooks.md`.

### Profiles

```
thor profile list|create NAME (--clone|--clone-all|--clone-from)|use|show|delete
thor profile rename A B | alias NAME | export NAME | import FILE
thor profile migrate-identity A B   Retry a completed rename's session/routing identity migration
```

### Credentials & Pools

```
thor auth                 Interactive credential manager
thor auth add [PROVIDER]  Add OAuth or API-key credential (nous, openai-codex, qwen-oauth, …)
thor auth list|remove P IDX|reset PROVIDER|status
```
Multiple credentials per provider form a pool that rotates automatically and skips exhausted keys.

### Other

```
thor desktop / gui        Native desktop app
thor dashboard            Web admin panel + embedded chat (--stop / --status)
thor proxy                OpenAI-compatible local proxy backed by an OAuth provider
thor portal               Quick setup / sign in via Nous Portal
thor kanban <verb>        Multi-agent work-queue board
thor project              Named multi-folder workspaces (see references/projects-and-folders.md)
thor skin list|use|set    Switch/tweak skins (see references/themes.md)
thor pets <verb>          Pet mascots (see references/petdex.md)
thor memory setup|status|off|reset   Memory provider
thor secrets bitwarden|onepassword   External secret stores
thor moa                  Mixture-of-Agents slots
thor hooks / security / backup / import / checkpoints / console
thor logs [-f] [errors]   View agent/error logs
thor send                 One-off message through a gateway platform
thor pairing / plugins / insights / journey / computer-use
thor acp                  ACP server (IDE integration)
thor completion bash|zsh|fish
thor update / uninstall
```

Plugin- and provider-supplied subcommands (e.g. `thor photon setup`) only appear once their plugin is installed/active. Importing from OpenClaw, Claude Code, Codex CLI or Cursor (`thor import-agent <agent>`, plus the older `thor claw migrate|cleanup`) comes from the `agent-importers` plugin; a fresh `thor setup` that finds one of those agents offers to install it.

### Where to Find Things

| Looking for... | Location |
|---|---|
| Config options | `thor config edit` · [Configuration docs](https://thor-agent.nousresearch.com/docs/user-guide/configuration) |
| Tools / toolsets | `thor tools list` · [Tools reference](https://thor-agent.nousresearch.com/docs/reference/tools-reference) |
| Skills catalog | `thor skills browse` · [Skills catalog](https://thor-agent.nousresearch.com/docs/reference/skills-catalog) |
| Provider setup | `thor model` · [Providers guide](https://thor-agent.nousresearch.com/docs/integrations/providers) |
| Env variables | `thor config env-path` · [Env vars reference](https://thor-agent.nousresearch.com/docs/reference/environment-variables) |
| Gateway logs | `~/.thor/logs/gateway.log` (or `thor logs`) |
| Sessions | `thor sessions browse` (reads state.db) |
