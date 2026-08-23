# Apache Maka

## 技术定义 (What)
Apache Maka 是一个本地优先的 AI Agent 工作空间，其核心创新是将 Agent 的模型消息、工具调用、工具结果、权限决策和终止事件全部记录为附加日志（Append-only Log）。运行时的一切行为都是该日志的投影，而非日志是行为的副产品。这意味着 Agent 的每一步执行都可追溯、可恢复、可审计。

## 行业痛点 (Why)
当前 Agent 框架将执行历史和上下文混在一起管理。上下文窗口变长导致成本高、质量下降；但丢弃历史意味着失去执行证据。Agent 崩溃后无法恢复中间状态，调试 Agent 行为像「黑盒探案」。

## 旧范式 vs 新范式
- **旧做法**：Chat-first 范式：Agent 将整个对话历史塞进 LLM 上下文窗口。上下文即历史，丢弃旧消息就是丢失执行证据。Agent 状态完全耦合于 LLM 的上下文窗口。
- **新做法**：Log-as-Runtime：Agent 所有行为记录在不可变的追加日志中。UI 和 LLM 调用都是日志的投影视图。短上下文不等于删除历史——Maka 可以省略旧工具输出不发给 LLM，但不丢弃执行证据。崩溃后可从中断处恢复。

## 生产力影响 (How)
(1) Agent 行为可审计——每一步都有日志证据；(2) 上下文成本可控——可以按需加载历史而非常驻窗口；(3) 崩溃恢复——日志确保执行状态可重建；(4) 评估可复现——Eval 通过 Runtime Host 执行，实验可精确复现。

## 采用成本
中等。当前仅 macOS Apple Silicon 桌面构建可用（Windows 预览，Linux 未支持）。需要 Node.js 22.19+，自行配置模型提供商。Apache 孵化阶段，API 仍可能变更。

## 核心线索
- GitHub：https://github.com/apache/maka
- 来源：https://github.com/apache/maka
- 发布时间：2026-08-24
