# TencentDB-Agent-Memory

## 技术定义 (What)
TencentDB Agent Memory 是一个四层语义记忆系统（L0 Conversation → L1 Atom → L2 Scenario → L3 Persona），结合符号化短期记忆（Mermaid Canvas）和分层长期记忆，解决 Agent 在长任务中的上下文膨胀和跨会话记忆丢失问题。

## 行业痛点 (Why)
Agent 长任务中，工具日志占大量 token（搜索结果、代码、错误日志）。传统方案要么暴力累积历史（token 爆炸），要么不可逆总结（细节丢失）。跨会话记忆要么没有，要么压成平面向量（无法回溯细节）。

## 旧范式 vs 新范式
- **旧做法**：短期记忆：暴力累积对话历史，token 爆炸后截断。长期记忆：平面向量存储，检索像盲人摸象，只有碎片，没有宏观结构。压缩：不可逆总结，细节永久丢失，无法回溯。
- **新做法**：短期：历史卸载到外部文件（refs/*.md），用 Mermaid Canvas 高密度符号表示任务状态（node_id 可追溯到原文）。长期：四层语义金字塔（对话 → 原子事实 → 场景块 → 用户画像），渐进式披露，细节在底层，结构在顶层。存储：底层 SQLite（事实、日志），顶层 Markdown（画像、场景、画布），完全可回溯。

## 生产力影响 (How)
实测结果：Token 使用降低 61.38%（WideSearch），任务通过率提升 51.52%（相对），PersonaMem 准确率从 48% 提升到 76%。适用于需要长时段记忆的 Agent（如连续跑 50 个 SWE-bench 任务）。支持 OpenClaw、Hermes Agent。

## 采用成本
开源免费。需 Node 22+、OpenClaw 2026.3.13+ 或 Hermes Gateway。安装：openclaw plugins install @tencentdb-agent-memory/memory-tencentdb。默认 SQLite 后端，零配置即用。支持 Postgres 持久化。

## 核心线索
- GitHub：https://github.com/TencentCloud/TencentDB-Agent-Memory
- 来源：https://github.com/trending/typescript
- 发布时间：2026-06-15
