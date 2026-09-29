# AnythingMCP

## 技术定义 (What)
自托管的 MCP 服务器和网关，将任意 REST/OpenAPI、SOAP、GraphQL、SQL API 转成 MCP 工具，无代码、265 个现成连接器（含 ERP/电商，21 个无需 API key），用 JSON 适配器定义 + 代理网关统一暴露给 Claude/ChatGPT/Copilot。

## 行业痛点 (Why)
企业系统（ERP、SOAP 遗留服务、数据库）没有 MCP 服务器，逐一手写 MCP server 费时费力。

## 旧范式 vs 新范式
- **旧做法**：为每个内部系统手写 MCP server，或让模型直接对接各类异构 API。
- **新做法**：声明式适配器目录 + 网关，把任何 API/DB 在几分钟内声明成受控的 MCP 工具集，企业级凭据加密、RBAC、审计日志内建。

## 生产力影响 (How)
大幅降低企业接入 AI Agent 的门槛，将 MCP 从"手写协议"变成"声明式集成"，已在 KOCH Freiburg 生产环境对接 15+ 系统。

## 采用成本
低：Docker Compose 三命令行启动；AGPL-3.0 自托管。

## 核心线索
- GitHub：https://github.com/HelpCode-ai/anythingmcp
- 来源：https://github.com/trending/typescript (81 stars today, production-adopted)
- 发布时间：2026-09-29
