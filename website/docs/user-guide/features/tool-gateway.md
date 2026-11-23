---
title: "Tool Gateway"
description: "The managed Nous Tool Gateway has been removed. Tools now use your own direct provider keys."
sidebar_label: "Tool Gateway"
sidebar_position: 2
---

# Tool Gateway

:::danger Managed gateway removed

The Nous Tool Gateway — web search, image generation, TTS, and cloud browser automation routed through a Nous Portal subscription — has been **removed from Thor Agent**. There is no "Nous Subscription" backend anymore, and `thor setup --portal` no longer exists.
:::

## What to use instead

Each tool now uses a direct vendor key that you configure yourself:

| Tool | Direct route |
|---|---|
| Web search & extract | Your own search provider key, or a self-hosted SearxNG (`web.backend: searxng`) |
| Image generation | Your own FAL / Krea key (`thor tools` → Image Generation) |
| Text-to-speech | Your own OpenAI or ElevenLabs key |
| Cloud browser automation | Your own Browser Use / Browserbase key |

Configure each tool at any time with:

```bash
thor tools          # Interactive picker for each tool category
```

Pick the tool, then pick a direct provider and enter its key. Nothing is billed through Thor or ThorHub for tools — ThorHub sells inference tokens only; tool vendors bill you directly.

## Checking what is active

```bash
thor status --full      # Full system status, tools included
```
