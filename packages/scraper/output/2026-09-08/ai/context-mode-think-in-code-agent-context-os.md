# Context Mode — Think-in-Code + 工具输出沙箱化

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆ | "Think in Code"让LLM生成代码而非读取数据；工具输出沙箱化98%压缩；Session Continuity通过FTS5索引实现对话恢复 |
| 采用广度 | ☆☆☆☆ | Microsoft, Google, Meta, Amazon, IBM, NVIDIA, ByteDance, Stripe 等 18 家大厂已在团队中使用 |
| 时间新鲜 | ☆☆☆☆☆ | 首发于 2026 年 9 月初，HN 冲上 #1 |
| 社区热度 | ☆☆☆☆☆ | HN 570+ points，Discord 活跃社区，npm 持续增长 |
| **总体判断** | ✅ | **新范式 — Agent 上下文管理的操作系统级方案** |

## 技术定义 (What)

Context Mode 是一个 MCP Server，从四个维度系统性解决 Agent 上下文窗口问题：

1. **Context Saving（沙箱化）**：工具调用产生的原始数据不进入上下文，而是进入沙箱。315KB → 5.4KB，压缩 98%。
2. **Session Continuity（会话连续性）**：所有文件编辑、git 操作、task、错误、用户决策都记录在 SQLite 中，通过 FTS5 + BM25 搜索，在对话被 compact 后精准检索相关内容恢复状态。
3. **Think in Code（代码思维）**：LLM 不读取 50 个文件来统计函数数，而是生成一个脚本执行计数，一次调用替代十次工具调用，节省 100x 上下文。
4. **无散文强制**：不强制模型使用特定风格，将"数据路由"和"表达风格"解耦，避免破坏推理能力。

```js
// Before: 47 × Read() = 700 KB.  After: 1 × ctx_execute() = 3.6 KB.
ctx_execute("javascript", `
  const files = fs.readdirSync('src').filter(f => f.endsWith('.ts'));
  files.forEach(f => console.log(f + ': ' + fs.readFileSync('src/'+f,'utf8').split('\\n').length + ' lines'));
`);
```

## 行业痛点 (Why)

Agent 工作 30 分钟后，40% 上下文窗口被工具调用原始数据占据。当 Agent compact 释放空间时，它会忘记正在编辑的文件、进行中的任务、用户上次的指令。加上模型在 filler、客套话和冗长解释上浪费的 token，上下文从两侧被同时消耗——这是一个尚未被系统性解决的 Agent 工程基础问题。

## 旧范式 vs 新范式
- **旧做法**：MCP 工具直接 dump 原始数据到上下文 → 上下文膨胀 → compact 失忆 → 用户体验断裂
- **新做法**：沙箱隔离原始数据 + 代码替代读取 + 事件溯源持久化 + FTS5 精准检索恢复 = 上下文永远不会因工具调用而膨胀

## 生产力影响 (How)

- **直接经济价值**：上下文窗口利用率提升 40%+，减少 compact 频率，延长 Agent 有效会话时长
- **工程价值**：Think in Code 让 Agent 从"数据消费者"转变为"代码生成者"，100x 上下文节省
- **协作价值**：Insight dashboard 提供团队级 AI 工程分析

## 采用成本
- **时间**：安装 < 5 分钟（Claude Code 插件一键安装）
- **金钱**：开源免费（ELv2 许可）
- **学习曲线**：低。17 个客户端自动路由，`/context-mode:ctx-doctor` 一键诊断
- **兼容性**：Claude Code、Gemini CLI、17+ 平台，支持 OpenClaw gateway

## 采用案例
- **Microsoft/Google/Meta/Amazon** 等 18 家大厂已在团队中使用
- **Claude Code 插件市场**：正式发布，完全自动化路由
- **npm 持续增长**：实时用户统计 badge

## 风险/局限
- 依赖 MCP 协议生态，非 MCP Agent 无法使用
- ELv2 许可（非标准开源），商业使用有限制
- 沙箱执行 `ctx_execute` 需要运行时环境（Node.js/Python）

## 核心线索
- GitHub：https://github.com/mksglu/context-mode
- HN 讨论：https://news.ycombinator.com/item?id=47193064（#1, 570+ points）
- 发布时间：2026 年 9 月初
- npm：https://www.npmjs.com/package/context-mode
- 当前状态：活跃开发中