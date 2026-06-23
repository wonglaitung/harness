# Context Mode

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次系统提出"上下文沙箱化"：MCP工具输出98%压缩，Think-in-Code范式（LLM生成脚本而非读取数据），会话连续性通过FTS5+BM25检索 |
| 采用广度 | ☆☆☆/5 | 声称被Microsoft/Google/Meta/Amazon/NVIDIA/ByteDance等团队使用；17个平台支持；ClawHub/OpenClaw集成 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月发布，HN #1（570+分） |
| 社区热度 | ☆☆☆☆☆/5 | HN #1（570+分），GitHub快速增长，Discord活跃 |
| **总体判断** | ✅ | **新范式 — Agent上下文管理的新基础设施** |

## 技术定义 (What)

Context Mode 是一个 MCP 服务器，解决了 AI 编码 Agent 的"上下文窗口污染"问题。核心思路：将 MCP 工具调用的原始输出隔离到沙箱中（不进入上下文窗口），通过 SQLite+FTS5 索引，按需用 BM25 检索相关片段。同时引入 "Think in Code" 范式——LLM 不应处理数据，而应生成处理数据的脚本，只将结果注入上下文。

四大能力：
1. **上下文保存**：工具输出沙箱化，315KB → 5.4KB（98%压缩）
2. **会话连续性**：所有文件编辑/git操作/任务/错误记录在SQLite，compaction后通过FTS5+BM25检索恢复
3. **Think in Code**：LLM写脚本分析数据，console.log只输出结果，1个脚本替代10次工具调用
4. **零散文执行**：不强制模型如何写回复，聚焦数据路由而非表达风格

## 行业痛点 (Why)

AI 编码 Agent 运行30分钟后，40%上下文窗口被 MCP 工具原始输出占满（Playwright快照56KB、20个GitHub issue 59KB、一条访问日志45KB）。当 Agent 压缩对话释放空间时，会忘记正在编辑的文件、进行中的任务和最近的请求。同时 Agent 还在输出冗余寒暄和解释，从两侧燃烧上下文。

## 旧范式 vs 新范式

- **旧做法**：MCP工具原始输出直接注入上下文窗口 → 30分钟占满40% → 对话压缩丢失关键信息 → 频繁重新解释项目背景
- **新做法**：工具输出隔离到沙箱 → SQLite+FTS5索引 → BM25按需检索 → 上下文窗口只留精要 → "Think in Code"让LLM生成分析脚本而非读取原始数据

## 生产力影响 (How)

1. **上下文利用率提升10倍+**：98%压缩意味着同样的上下文窗口能处理10倍以上的工具调用
2. **长任务不再断片**：会话压缩后通过BM25检索自动恢复上下文，无需手动重新解释
3. **Think in Code范式**：1个脚本替代10次Read()调用，从700KB降到3.6KB
4. **跨17个平台通用**：Claude Code、Cursor、Copilot、Codex CLI等全部支持

## 采用成本

- **时间**：Claude Code 下 2分钟安装（/plugin marketplace add + /plugin install）
- **金钱**：开源免费，ELv2许可证
- **学习曲线**：极低——安装后自动生效，无需配置路由规则（SessionStart hook自动注入）

## 采用案例

- **Claude Code**：插件市场一键安装，全自动路由
- **OpenClaw**：原生集成，gateway层面支持
- **其他15+平台**：通过hook或路由文件配置

## 风险/局限

- ELv2许可证限制商业使用场景
- 沙箱化可能丢失某些工具输出的细节上下文
- BM25检索可能无法精确召回所有相关信息
- 声称的企业用户（Microsoft/Google等）未经验证，可能仅为个人使用
- "Think in Code"要求LLM具备代码生成能力，小模型可能表现不佳

## 核心线索

- GitHub：https://github.com/mksglu/context-mode
- 首发来源：Hacker News（#1, 570+分）
- 发布时间：2026年6月
- 当前状态：活跃（每日更新）