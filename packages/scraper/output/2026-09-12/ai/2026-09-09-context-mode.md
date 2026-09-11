# Context Mode — Agent 上下文操作系统级方案

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次提出"工具输出沙箱化 + Think-in-Code + 会话连续性"三位一体Agent上下文管理方案 |
| 采用广度 | ☆☆☆☆☆/5 | 被 Microsoft/Google/Meta/Amazon/IBM/NVIDIA/Stripe 等顶级团队采用 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-09-09 HN #1，当日 GitHub 趋势榜 |
| 社区热度 | ☆☆☆☆☆/5 | HN #1 570+ points，GitHub 224 stars/day，Discord 活跃社区 |
| **总体判断** | ✅ | **新范式：Agent 上下文操作系统** |

## 技术定义 (What)

Context Mode 是一个 MCP 服务器，将 Agent 上下文管理提升为操作系统级别的方案。它解决四维问题：(1) 工具输出沙箱化（98% 上下文压缩），(2) SQLite+FTS5 会话连续性，(3) Think-in-Code 范式（用脚本替代多次工具调用），(4) 跨 17 个编码客户端自动路由。

## 行业痛点 (Why)

AI 编码 Agent 的上下文窗口是稀缺资源。一个 Playwright 快照 56KB，20 个 GitHub issue 59KB，一个访问日志 45KB——30 分钟后 40% 的上下文被消耗殆尽。更糟的是 compaction 时 Agent 会忘记正在编辑的文件、进行中的任务。

## 旧范式 vs 新范式

- **旧做法**：每个 MCP 工具调用的原始输出直接进入上下文窗口 → 上下文快速膨胀 → compaction 丢失状态 → 重新开始
- **新做法**：工具输出先进入 SQLite 沙箱，仅返回摘要（315KB→5.4KB）。会话状态持久化在 FTS5 索引中，compaction 后通过 BM25 检索恢复。代码生成器模式替代阅读器模式。

## 生产力影响 (How)

- 98% 上下文节省：单次例行操作从 315KB 降至 5.4KB
- 会话永续：compaction 后通过 FTS5 BM25 检索精确恢复工作状态
- Think-in-Code：一个脚本替代 47 次 Read() 调用，700KB→3.6KB
- 跨平台路由：自动适配 Claude Code、Codex、Cursor、Cline、Copilot 等 17 个客户端

## 采用成本

- **时间**：1 分钟安装（Claude Code: `/plugin marketplace add mksglu/context-mode`）
- **金钱**：免费开源（ELv2 许可证）
- **学习曲线**：低，安装后自动生效，支持 `/context-mode:ctx-doctor` 诊断

## 采用案例

- Microsoft/Google/Meta/Amazon/IBM/NVIDIA：内部团队已采用
- Stripe/Datadog/Salesforce/GitHub/Red Hat：生产环境使用
- Supabase/Canva/Notion/Hasura/Framer/Cursor：集成到工作流
- HN 社区：570+ points，#1 热帖

## 风险/局限

- 需要与 MCP 生态深度绑定
- ELv2 许可证（非完全开放）
- 对非 MCP 客户端需手动配置路由文件
- "Think in Code" 范式需要 Agent 具备代码生成能力

## 核心线索

- GitHub：https://github.com/mksglu/context-mode
- HN 首发：https://news.ycombinator.com/item?id=47193064
- 发布时间：2026-09-09（HN #1）
- 当前状态：活跃开发中，npm 持续更新
- npm：`context-mode`