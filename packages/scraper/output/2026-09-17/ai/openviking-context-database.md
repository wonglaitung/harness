# OpenViking — Agent 的"上下文数据库"新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 提出"Context Database"及 `viking://` 虚拟文件系统，统一 Memory/RAG/Skills |
| 采用广度 | ☆☆/5 | 火山引擎（volcengine）出品，trendshift 排位靠前，社区 Discord/WeChat 活跃 |
| 时间新鲜 | ☆☆☆☆/5 | 近期开源（GitHub issue/贡献活跃） |
| 社区热度 | ☆☆☆/5 | Python trending 单日 +276 stars |
| **总体判断** | ✅ | **新范式（观察中）** |

## 技术定义 (What)
由火山引擎开源的 Agent 上下文数据库。上下文被组织成 `viking://` 虚拟文件系统，Agent 像操作文件一样 browse/read/write；通过 L0(目录摘要)→L1(概览)→L2(全文)分层加载，向量搜索先定位目录再下钻，会话 commit 后归档为长期记忆。

## 行业痛点 (Why)
Agent 的 memory、knowledge RAG、skills 三套系统彼此割裂，无统一治理层，造成上下文冗余、检索不精准、token 浪费。

## 旧范式 vs 新范式
- **旧做法**：向量库 + 独立记忆模块 + 独立 skills 库拼接，缺乏统一入口与分层加载。
- **新做法**：单一 `viking://` 文件系统承载全部上下文，分层摘要按需加载，向量检索目录下钻，会话自归档为记忆。

## 生产力影响 (How)
为 Agent 提供一个确定性、可检索、可复用的上下文统一底座，降低集成成本，减少上下文窗口浪费。

## 采用成本
需适配 `viking://` URI 与分层加载模型；AGPLv3 需评估合规。

## 采用案例
- 火山引擎官方 Studio 在线演示 + 可自托管 Web Studio。
- 定位为统一 Agent Memory、Knowledge RAG 与 Skills 的底座。

## 风险/局限
- 概念仍在早期，生态与第三方集成尚少；AGPLv3 对商业闭源使用有限制。

## 核心线索
- GitHub：https://github.com/volcengine/OpenViking
- 首发来源：https://github.com/volcengine/OpenViking
- 发布时间：近期（2026 Q3 活跃）
- 当前状态：活跃（早期）