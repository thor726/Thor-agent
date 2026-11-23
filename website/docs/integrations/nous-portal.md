---
sidebar_position: 1
title: "Nous Portal (removed)"
description: "Nous Portal has been removed from Thor Agent. Use ThorHub or a direct provider instead."
---

# Nous Portal (removed)

Nous Portal — Thor Labs's unified subscription gateway — has been **removed from Thor Agent**. Thor now stands on its own: there is no Portal OAuth login, no `thor setup --portal`, and no Nous subscription billing inside Thor.

## What to use instead

- **[ThorHub](./thorhub.md)** — Thor's own token store at https://llm.thormarket.site. Buy token packages (QRIS), get a sub-key (`sk-thor-...`), and use it in Thor as a custom provider. Top up at https://llm.thormarket.site/beli/topup and check your balance with `/topup` (when a ThorHub key is configured) or `/skill saldo`.
- **Direct providers** — run `thor setup` and pick a provider yourself (Gemini, Groq, OpenAI, Anthropic, OpenRouter, and others), each with its own API key and billing. This is the normal way to run Thor; ThorHub is one optional provider among them.

Old links to `portal.thor-agent.local` no longer resolve — that domain was never a public address. If you followed an old guide that told you to run `thor setup --portal` or `thor portal`, use `thor setup` instead and choose your own provider.
