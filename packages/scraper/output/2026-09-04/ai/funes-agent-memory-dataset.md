# Funes — Agent记忆即数据集

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 「记忆是数据集，不是服务」——将Agent记忆提升为可发布、可共享的数据资产 |
| 采用广度 | ☆☆☆/5 | 已支持 Claude Code、Codex、pi、Hermes 四款主流Agent；刚发布 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-09-03 发布（HuggingFace + HN热议） |
| 社区热度 | ☆☆☆☆/5 | HuggingFace官方博客 + HN讨论 |
| **总体判断** | ✅ | **新范式：Agent记忆即数据集** |

## 技术定义 (What)
Funes 是 HuggingFace 发布的 Agent 持久化记忆层。它将多个 Agent 的会话记录解析为统一格式，本地嵌入索引存入 Lance 数据集，提供 recall/get 工具让 Agent 自主回溯历史决策。

## 行业痛点 (Why)
- 每次Agent会话从零开始，历史推理全部丢失
- 跨Agent工具（Claude Code / Codex / pi）无统一记忆
- Session log 只是归档，无法被Agent主动检索
- 团队知识在Agent中不可传递

## 旧范式 vs 新范式
- **旧做法**：Agent会话孤立，上下文靠手工粘贴；session log是死归档
- **新做法**：Agent记忆即数据集——解析→嵌入→索引→可发布到Hub，Agent自主recall，跨Agent跨机器共享

## 生产力影响 (How)
- Agent无需从零理解项目，自主回溯历史决策
- 跨Agent无缝迁移：Claude Code开始→Codex继续
- 新成员第一天即可检索数月项目决策历史
- recall 返回原始证据，不做摘要蒸馏（比 compaction 更准且更便宜）

## 采用成本
安装：`curl -fsSL ... | sh` + `funes add claude`。本地运行，无ML运行时依赖。公开共享需HuggingFace账号（默认私有）。

## 采用案例
- 已支持 Claude Code、Codex、pi、Hermes
- HuggingFace 自用开发 funes 本身
- 团队协作场景：新人Agent第一天就能recall历史决策

## 风险/局限
- 目前仅支持4款Agent（Claude Code/Codex/pi/Hermes）
- 嵌入模型固定（更换需重建索引）
- 隐私需注意：虽本地运行+凭证脱敏，但共享数据集有风险

## 核心线索
- GitHub：https://github.com/huggingface/funes
- 博客：https://huggingface.co/blog/funes
- 发布时间：2026-09-03
- 许可证：Apache 2.0