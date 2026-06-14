# Claw Patrol

## 技术定义 (What)
Deno 发布的 Agent 安全防火墙，位于 Agent 和生产环境之间，在协议层解析流量并按 HCL 规则进行访问控制。支持 SQL、Kubernetes、HTTP 等协议的细粒度权限管理。

## 行业痛点 (Why)
AI Agent 拥有生产环境访问权限后，可能执行破坏性操作（如删除数据库、暴露密钥），缺乏统一的安全控制层。

## 旧范式 vs 新范式
- **旧做法**：在 Agent 代码中硬编码安全限制，或依赖沙箱环境隔离，难以统一管理和审计跨协议访问。
- **新做法**：独立的安全代理层，使用 HCL 声明式规则，支持"人类审批"模式（如 kubectl delete 需人工确认），在协议层拦截危险操作。

## 生产力影响 (How)
将 Agent 安全控制从"代码层面"提升到"基础设施层面"，统一管理所有 Agent 的生产环境访问权限，支持审计和人工审批流程。

## 采用成本
单二进制文件，支持 Linux/macOS/Windows，配置学习成本低（HCL 语法），可渐进式部署（从单个 Agent 开始）。

## 核心线索
- GitHub：https://github.com/denoland/clawpatrol
- 来源：https://github.com/denoland/clawpatrol
- 发布时间：2026-06-14
