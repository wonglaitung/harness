# TencentDB Agent Memory

## 技术定义 (What)
腾讯云推出的 Agent 记忆架构，通过"符号化短期记忆 + 分层长期记忆"解决 Agent 的上下文过载问题。短期记忆使用 Mermaid Canvas 符号图压缩任务日志，长期记忆构建 4 层语义金字塔（L0 Conversation → L1 Atom → L2 Scenario → L3 Persona），实现渐进式信息提取与追溯。

## 行业痛点 (Why)
现有 Agent 记忆系统的三大问题：1）Token 爆炸（长任务日志累积数十万 tokens）；2）信息碎片化（向量数据库缺乏结构，召回准确率低）；3）不可追溯（压缩后无法还原原始证据）。测试数据：OpenClaw 在 WideSearch 基准上成功率仅 33%，PersonaMem 准确率仅 48%。

## 旧范式 vs 新范式
- **旧做法**：将所有对话、工具日志、任务轨迹扁平化存储在向量数据库中。召回时通过语义相似度搜索，但缺乏宏观结构和层级关系。压缩采用不可逆摘要，丢失原始细节。
- **新做法**：短期记忆：将冗长的工具日志卸载到外部文件，用 Mermaid 符号图表示任务状态转移，Agent 只需关注几百 tokens 的结构图，需要细节时通过 node_id 追溯原始日志。长期记忆：构建语义金字塔，Persona 层存储日常偏好，Scenario 层存储场景块，Atom 层存储原子事实，Conversation 层保留原始对话。上下层之间可双向追溯。

## 生产力影响 (How)
实测数据：1）Token 降低 61.38%（WideSearch 基准）；2）成功率提升 51.52%（相对提升）；3）PersonaMem 准确率从 48% 提升到 76%；4）SWE-bench 上任务成功率提升 9.93%。对开发者的影响：显著降低长任务成本，提升 Agent 长期工作能力。

## 采用成本
开源项目（MIT 协议），支持 OpenClaw 和 Hermes Agent。安装：`openclaw plugins install @tencentdb-agent-memory/memory-tencentdb`。依赖：SQLite + sqlite-vec（本地零配置）。学习曲线：需要理解分层记忆概念，但使用简单（自动捕获、提取、聚合）。

## 核心线索
- GitHub：https://github.com/TencentCloud/TencentDB-Agent-Memory
- 来源：https://github.com/trending/typescript
- 发布时间：2026-06-16
