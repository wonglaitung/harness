# AG-UI (Agent-User Interaction Protocol)

## 技术定义 (What)
AG-UI 是一个开放、轻量、基于事件的协议，用于标准化 AI Agent 与用户界面应用之间的连接。Agent 后端在执行过程中发出约 16 种标准事件类型，前端则回传少量兼容输入，中间由灵活的中间件层适配任意传输通道（SSE / WebSocket / webhook）。

## 行业痛点 (Why)
MCP 解决了 Agent 获取工具、A2A 解决了 Agent 之间通信，但「Agent 如何把执行状态、流式输出、双向状态同步、人类干预点暴露给用户界面」这一层完全没有标准。每个前端框架各写一套私有事件格式，Agent 无法跨应用复用。

## 旧范式 vs 新范式
- **旧做法**：每个 Agent 应用自建一套流式回调 / 自定义 SSE 事件格式，绑定在特定框架（LangChain callback、CrewAI callback）上，换框架就要重写整个前端交互层。
- **新做法**：Agent 与 UI 之间用统一事件协议解耦。Agent 后端只负责发出标准事件，任意前端（React、Vue、移动端）用中间件适配即可渲染。形成 MCP（工具）→ A2A（Agent 间）→ AG-UI（Agent↔用户）的三层协议栈。

## 生产力影响 (How)
开发者可把 Agent 接入现有产品前端而无需重写交互层；生成式 UI（Generative UI）、双向状态同步、Human-in-the-loop 审批成为协议能力而非自研工程。前端与 Agent 可独立演进。

## 采用成本
低成本。`npx create-ag-ui-app` 秒级脚手架，npm `@ag-ui/core`，MIT 许可，官方提供 Dojo 演练场与参考 HTTP 实现。

## 核心线索
- GitHub：https://github.com/ag-ui-protocol/ag-ui
- 来源：https://github.com/trending/typescript?since=daily
- 发布时间：2026-11-16
