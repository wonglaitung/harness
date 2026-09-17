# OpenViking — Context Database for AI Agents

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 明确"Context Database"术语 + viking:// 虚拟文件系统 |
| 采用广度 | ☆☆☆/5 | 火山引擎背书，trendshift 上榜 |
| 时间新鲜 | ☆☆☆☆/5 | 近期开源，快速迭代 |
| 社区热度 | ☆☆☆☆/5 | 多语言 README、社区渠道齐全 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
把 Agent 的知识/记忆/技能统一为 `viking://` 虚拟文件系统，Agent 用文件操作进行浏览、读取、编辑，配合目录摘要/概览/全文三层按需加载和目录内向量搜索。

## 行业痛点 (Why)
Memory/RAG/Skills 三套系统分散、无统一抽象，Agent 浪费 token 或遗漏信息，跨 session 经验复用困难。

## 旧范式 vs 新范式
- **旧做法**：Memory、RAG、Skills 各自为政，全量或简单相似度检索
- **新做法**：单一 `viking://` 文件系统统一上下文，目录结构 + 三层懒加载 + 目录内向量搜索

## 生产力影响 (How)
统一上下文抽象降低 Agent 开发复杂度，减少 token 浪费，让跨 session 记忆复用成为一等公民。

## 采用成本
需理解 viking:// URI 和三层 context layer，AGPLv3 许可需注意商用合规。

## 采用案例
- 火山引擎（背书方）：作为 Agent 基础设施的上下文层

## 风险/局限
- AGPLv3 许可对闭源商用有约束
- 概念较新，生态兼容性待验证
- 对非文件系统思维模型的开发者有一定学习成本

## 核心线索
- GitHub：https://github.com/volcengine/OpenViking
- 来源：火山引擎 volcengine
- 当前状态：活跃（近期开源，持续迭代）
- 官网：https://www.openviking.ai