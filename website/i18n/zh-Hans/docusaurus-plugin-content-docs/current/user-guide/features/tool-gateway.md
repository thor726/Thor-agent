---
title: "Tool Gateway（工具网关）"
description: "托管的 Nous Tool Gateway 已移除。各工具现在使用你自己的服务商 Key。"
sidebar_label: "Tool Gateway"
sidebar_position: 2
---

# Tool Gateway（工具网关）

:::danger 托管网关已移除

Nous Tool Gateway——通过 Nous Portal 订阅路由的网页搜索、图像生成、TTS 和云浏览器自动化——已从 Thor Agent 中**移除**。不再有 "Nous Subscription" 后端，`thor setup --portal` 也不存在了。
:::

## 改用什么

每个工具现在使用你自己配置的服务商直连 Key：

| 工具 | 直连方式 |
|---|---|
| 网页搜索与抓取 | 你自己的搜索服务商 Key，或自建 SearxNG（`web.backend: searxng`） |
| 图像生成 | 你自己的 FAL / Krea Key（`thor tools` → 图像生成） |
| 文本转语音 | 你自己的 OpenAI 或 ElevenLabs Key |
| 云浏览器自动化 | 你自己的 Browser Use / Browserbase Key |

随时配置每个工具：

```bash
thor tools          # 每个工具类别的交互式选择器
```

选择工具，再选择直连服务商并输入 Key。工具费用不经过 Thor 或 ThorHub 结算——ThorHub 只出售推理 Token；工具服务商直接向你收费。

## 查看当前状态

```bash
thor status --full      # 完整系统状态，包括工具
```
