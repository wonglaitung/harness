# Apache Maka — Log-is-the-Runtime Agent 事件溯源运行时

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆ | "The log is the runtime"：每条模型消息、工具调用、权限决策、终止信号都是 append-only RuntimeEvent。UI、prompt、崩溃恢复都是 log 的投影——这是 Agent 领域的 Event Sourcing |
| 采用广度 | ☆☆☆ | Apache 孵化项目，与 FrontierHarness 联动评测（Maka 作为被测 harness 之一），支持多种模型后端 |
| 时间新鲜 | ☆☆☆☆☆ | 2026 年进入 Apache Incubator，处于早期阶段 |
| 社区热度 | ☆☆☆☆ | Apache 基金会背书，GitHub stars 持续增长，多平台支持 |
| **总体判断** | ✅ | **新范式 — Agent 运行时从"状态机"进化为"事件溯源系统"** |

## 技术定义 (What)

Apache Maka 是一个高性能 Agent 工作空间，核心创新是 **"日志即运行时"（Log-is-the-Runtime）** 架构：

```
Desktop / TUI / CLI → Runtime Host → SessionManager → AgentRun
                                             ↓
                         Model + Tool Runtime → Runtime Event Log（Append-Only）
                                             ↓
                              Context / Session / UI projections
```

- **每个 turn 的所有事件**（模型消息、工具调用、权限请求、用户审批、文件编辑、终止）都是 **不可变的 RuntimeEvent**
- **UI、prompt 构建、崩溃恢复** 都是同一份 log 的不同投影
- 旧工具输出可以离开 prompt 但不离开 log——实现了"上下文窗口"与"真相来源"的分离
- 评测系统（Experiment → Cells → Attempts → Results）直接使用同一 Runtime Host

## 行业痛点 (Why)

1. **Agent 会话不可复现**：当前 Agent 工具的对话历史是 prompt 字符串拼接，丢失了工具调用的精确时序和权限决策
2. **崩溃后无法恢复**：对话 compaction 或系统崩溃后，Agent 丢失"做过什么"的精确记录
3. **评测不可靠**：无法确定 Agent 失败是因为模型能力还是 harness 的实现差异

## 旧范式 vs 新范式

- **旧做法**：Agent 运行时以"当前状态"为核心——模型读取对话历史（可能已被 compaction 压缩），工具输出混在 prompt 中。崩溃=丢失上下文
- **新做法**：Agent 运行时以"完整事件日志"为核心——每个事件 append-only 写入 SQLite。prompt 构建是 log 的实时投影，崩溃后从 log 恢复。**数据与呈现彻底分离**

## 生产力影响 (How)

1. **100% 可复现**：任何 Agent 会话可以完全重放和审计
2. **崩溃零丢失**：从 log 恢复，自动续接
3. **公平评测**：Maka 在 FrontierHarness 上用同一模型、同一官方验证器跑分，结果公开发布在 `docs/eval/`
4. **本地优先**：会话、设置、运行记录都留存在用户机器上

## 采用成本

- **时间**：中等。需要搭建 Node.js 环境，自带模型 API key
- **学习曲线**：中等。需要理解事件溯源概念和 Runtime Host 架构
- **平台**：macOS 稳定，Windows/Linux 预览。支持 Claude Code 风格的 TUI 和 CLI

## 采用案例

- **FrontierHarness 评测**：Maka 作为 12 个被测 harness 之一，在 360 次独立冷启动试验中与其他 harness 对比
- **Apache 孵化器**：进入 ASF 孵化，代表社区认可其架构创新

## 风险/局限

- 尚未正式发布 ASF release 版本（仅有 Nightly）
- 事件日志存储可能随时间增长（需要 purge 策略）
- 平台支持不完整（Windows/Linux 仍是预览）
- 不自带模型，用户需自行配置 API 或本地模型

## 核心线索

- GitHub：https://github.com/apache/maka
- 网站：https://maka.apache.org/
- 架构文档：ARCHITECTURE.md
- 发布时间：2026 年进入 Apache Incubator
- 当前状态：活跃开发中（Apache 孵化项目）