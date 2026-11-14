# Headroom — Context Compression Layer for AI Agents（Agent 上下文压缩层）

## 技术定义 (What)
Headroom 是一个运行在本地的「上下文压缩层」，在 prompt 送进 LLM 之前压缩 Agent 读取的一切内容——工具输出、日志、RAG chunk、文件、对话历史，声称"同样的答案，更少的输入 token"。它提供五种接入形态：Python/TS 库（`compress(messages)` 一行调用）、HTTP proxy（零代码改动）、`headroom wrap claude|codex|cursor|aider|...` 一条命令包裹 15+ 种 Agent CLI、MCP server（`headroom_compress`/`headroom_retrieve`/`headroom_stats`）、以及跨 Agent 共享记忆库。关键设计是 CCR（可逆压缩）：原始内容本地缓存、按需取回，因此压缩不是有损的单向丢弃。

## 行业痛点 (Why)
Agent 的成本与失败率由上下文膨胀主导：一次 55k token 的 Agent prompt 里绝大多数是工具输出、日志噪音和重复 JSON 数组，而这些内容既稀释注意力又拉高账单。开发者只能在"塞满"和"截断丢信息"之间二选一——截断会丢掉第 67 行的 FATAL，塞满则 token 费用失控。传统做法（手工裁剪、RAG 摘要、上下文窗口扩容）都是应用层补丁，不构成可复用的基础设施层。

## 旧范式 vs 新范式
- **旧做法**：上下文管理被当作每个应用的局部实现细节：要么把全部工具输出原样塞进上下文并依赖更大的 context window，要么粗暴截断/摘要并接受信息丢失。压缩与检索被混为一谈。
- **新做法**：上下文压缩被抽成一层独立的、可逆的基础设施：在 Agent 与模型之间插入一个本地可部署的压缩层（库/proxy/MCP），对结构化内容（JSON、日志、文件）做高比率压缩而对散文几乎不动，同时把原文缓存在本地以便按需取回。Agent 本身零改动，压缩比可测量（21–57%，重复 JSON/日志 90%+）。

## 生产力影响 (How)
对手写应用，一行 `compress(messages)` 即可降低 20%+ 输入 token；对编码 Agent，`headroom wrap <tool>` 零代码接入。压缩发生在本地，无 API key、无模型下载、`HEADROOM_OFFLINE=1` 可完全离线，因此不存在把 prompt/文件内容外发的合规问题。附带 `headroom learn` 把失败 session 挖掘成 CLAUDE.md/AGENTS.md 修正项，把"压缩"延伸为"经验沉淀"。

## 采用成本
库接入分钟级（pip/npm 一行）；proxy 与 wrap 模式需在本地跑一个 8787 端口服务。学习成本低但需自行验证压缩保真度——README 自述"对散文效果很小（little on prose）"，因此对散文为主的场景收益有限。核心风险是压缩器本身可能丢关键信息，CCR 的可逆性是主要缓解手段。

## 核心线索
- GitHub：https://github.com/headroomlabs-ai/headroom
- 来源：https://github.com/trending/python?since=daily
- 发布时间：2026-11-14
