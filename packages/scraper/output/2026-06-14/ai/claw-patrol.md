# Claw Patrol

## 技术定义 (What)
Agent 安全防火墙，部署在 AI Agent 和生产环境之间，解析 Agent 流量并根据 HCL 规则进行访问控制。支持 PostgreSQL、ClickHouse、Kubernetes、HTTP 等多种协议的细粒度权限管理。

## 行业痛点 (Why)
AI Agent 执行数据库操作、K8s 部署等生产环境任务时，存在误删数据、泄露敏感信息、执行未授权操作的风险。缺乏有效的访问控制和审计机制，难以限制 Agent 的权限边界。

## 旧范式 vs 新范式
- **旧做法**：依赖 Agent 自身的安全意识或简单的 RBAC 权限控制。无法实时监控和拦截 Agent 的危险操作，缺乏针对 Agent 工作流的专门安全工具。
- **新做法**：在 Agent 和生产环境之间部署独立的防火墙层，实时解析和审计所有流量。使用 HCL 规则定义细粒度访问策略（如阻止删除生产数据库、要求人工审批敏感操作），支持 WireGuard 和 Tailscale 安全隧道。

## 生产力影响 (How)
为 AI Agent 提供生产环境安全护栏，防止误操作和恶意行为。支持"需要审批"模式，高风险操作自动暂停等待人工确认。完整审计日志便于事后追溯，适合企业级 Agent 部署场景。

## 采用成本
部署简单（单二进制文件），需要编写 HCL 规则配置。学习成本中等，需要理解 CEL 表达式和协议级审计。支持三种部署模式：gateway、join、run，适应不同网络架构。

## 核心线索
- GitHub：https://github.com/denoland/clawpatrol
- 来源：https://github.com/denoland/clawpatrol
- 发布时间：2026-06-14
