# TencentDB Agent Memory

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首创"符号记忆+分层记忆"双支柱架构，Mermaid Canvas编码任务状态 |
| 采用广度 | ☆☆☆/5 | 已集成OpenClaw、Hermes Gateway，腾讯云生产级部署 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年新发布，GitHub trending当日567 stars |
| 社区热度 | ☆☆☆☆/5 | GitHub 567 stars/day，TypeScript trending #1 |
| **总体判断** | ✅ | **新范式 — Agent记忆从扁平向量存储走向分层符号化** |

## 技术定义 (What)
TencentDB Agent Memory 是一个为 AI Agent 设计的分层记忆系统，核心创新在于拒绝传统的"扁平向量堆"存储方式，转而采用**符号短期记忆（Symbolic Short-term Memory）+ 分层长期记忆（Layered Long-term Memory）**双支柱架构。短期记忆通过 Mermaid 语法图将冗长工具日志压缩为高密度符号图；长期记忆通过 L0→L3 语义金字塔（Conversation→Atom→Scenario→Persona）实现渐进式披露。

## 行业痛点 (Why)
当前 Agent 记忆系统存在两大问题：1）短期任务中，冗长的工具日志（搜索结果、代码、错误追踪）消耗大量 token，导致上下文溢出；2）长期记忆将所有对话碎片化后堆入扁平向量库，召回退化为盲搜，缺乏宏观引导。传统方案要么暴力累积历史（token爆炸），要么不可逆有损摘要（丢失细节）。

## 旧范式 vs 新范式
- **旧做法**：将记忆碎片化后存入扁平向量数据库（Pinecone/Weaviate），召回靠向量相似度盲搜，短期靠暴力塞入上下文，长期靠有损摘要
- **新做法**：短期记忆用 Mermaid 符号图编码任务状态转移，工具日志卸载到外部文件，Agent 只需关注顶层符号结构；长期记忆构建 L0→L3 语义金字塔，Persona层承载日常偏好，需要细节时通过 node_id 钻取到原子事实

## 生产力影响 (How)
- **Token 消耗降低 61.38%**（WideSearch benchmark），SWE-bench 降低 33.09%
- **任务成功率提升 51.52%**（WideSearch），SWE-bench 提升 9.93%
- **Persona 记忆准确率从 48% 提升到 76%**
- 开发者无需反复向 Agent 重复 SOP、项目背景、工具约定

## 采用成本
- npm 安装：`@tencentdb-agent-memory/memory-tencentdb`
- 需要 Node.js >= 22.16
- 需配合 OpenClaw >= 2026.3.13 或 Hermes Gateway 使用
- 学习曲线：需理解分层记忆概念和 Mermaid 符号编码方式

## 采用案例
- **OpenClaw Agent**：集成后 SWE-bench 连续50任务会话中 token 降低33%，成功率提升10%
- **Hermes Gateway**：作为 Agent 记忆后端，支持长期个性化

## 风险/局限
- 目前主要与腾讯云生态绑定（TencentDB），独立部署需自行适配存储层
- Mermaid 符号编码对复杂任务可能存在信息损失
- 长期记忆的 L0→L3 蒸馏过程需要额外计算开销
- 文档以英文为主，中文社区资源较少

## 核心线索
- GitHub：https://github.com/TencentCloud/TencentDB-Agent-Memory
- 首发来源：GitHub Trending (TypeScript)
- 发布时间：2026年
- 当前状态：活跃（trending，高速增长）
