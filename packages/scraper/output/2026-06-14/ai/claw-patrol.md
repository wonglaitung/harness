# Claw Patrol

## 技术定义 (What)
专为 AI Agent 设计的安全防火墙，基于 HCL 规则在网络层拦截危险操作，支持 Kubernetes、PostgreSQL、ClickHouse、HTTP 等协议，提供审批流程。

## 行业痛点 (Why)
Agent 在生产环境执行危险操作（如删除 Pod、修改数据库）缺乏防护，可能导致生产事故，企业不敢大规模部署 Agent。

## 旧范式 vs 新范式
- **旧做法**：依赖 Agent 自身的对齐机制或人工监督，无法在网络层拦截危险请求，存在安全盲区。
- **新做法**：在网络层解析 Agent 流量，基于 CEL 表达式规则实时拦截危险操作，支持人工审批流程，提供审计日志。

## 生产力影响 (How)
DevOps 团队可为 Agent 配置安全策略，阻止 kubectl delete pod、DROP TABLE 等危险操作，企业可安全部署 Agent 到生产环境。

## 采用成本
开源免费（MIT 许可证），Go 语言编写，提供三种部署模式：gateway、join、run，支持 WireGuard/Tailscale 隧道。

## 核心线索
- GitHub：https://github.com/denoland/clawpatrol
- 来源：https://github.com/denoland/clawpatrol
- 发布时间：2026-06-14
