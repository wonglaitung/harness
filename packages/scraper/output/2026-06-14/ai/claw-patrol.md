# Claw Patrol

## 技术定义 (What)
Deno 推出的 Agent 安全防火墙，部署在 Agent 与生产环境之间，解析流量并基于 HCL 规则实时拦截危险操作。支持 Kubernetes、Postgres、ClickHouse、HTTP 等协议。

## 行业痛点 (Why)
AI Agent 可直接执行 kubectl delete pod、DROP TABLE 等破坏性操作，缺乏人工审批或自动拦截机制。传统防火墙无法理解 Agent 意图和协议语义。

## 旧范式 vs 新范式
- **旧做法**：信任 Agent 执行所有操作，或完全禁止 Agent 访问生产环境。无法细粒度控制"读允许但写需审批"。
- **新做法**：线级流量解析 + CEL 表达式规则引擎，针对每种协议提取语义事实（SQL 的 verb/table、K8s 的 resource/verb/namespace），支持 deny/approve 等多种裁决。通过 WireGuard/Tailscale 隧道部署，支持进程级隔离（Linux netns/macOS NetworkExtension）。

## 生产力影响 (How)
团队可为 Agent 定义安全边界：阻止删除 K8s secrets、要求人工审批 kubectl delete、拦截危险 SQL。实时监控所有 Agent 操作，审计日志完整。

## 采用成本
单二进制部署，支持 gateway/join/run 三种模式。规则用 HCL 编写，学习成本低。需要基础设施访问权限。

## 核心线索
- GitHub：https://github.com/denoland/clawpatrol
- 来源：https://github.com/denoland/clawpatrol
- 发布时间：2026-06-14
