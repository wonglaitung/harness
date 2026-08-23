# OpenViking — Context Database for AI Agents

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 「Context Database」——将 Agent 的记忆、知识、技能统一为 `viking://` 虚拟文件系统，完全颠覆黑盒向量数据库范式 |
| 采用广度 | ☆☆☆/5 | 已集成 OpenClaw、Hermes、Claude Code；火山引擎背书；有公开 benchmark 证明 |
| 时间新鲜 | ☆☆☆☆/5 | 2026 年活跃开发中，v0.3.22 为当前版本 |
| 社区热度 | ☆☆☆/5 | GitHub trending，多语言文档（中/英/日），Discord/Lark/WeChat 社区 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
OpenViking 是一个面向 AI Agent 的开源上下文数据库。它将 Agent 的记忆（Memories）、知识资源（Resources）和技能（Skills）统一存储在 `viking://` 虚拟文件系统协议下。Agent 使用 `ls`、`tree`、`find` 等文件系统语义浏览上下文，而非向黑盒向量数据库发查询。每个条目按 L0（摘要 100 token）→ L1（概览 2k token）→ L2（完整内容）三层分级加载，仅在需要时深入。

## 行业痛点 (Why)
Agent 上下文管理三大痛点：(1) 向量数据库是黑盒——检索结果无法追溯到具体路径；(2) 所有上下文平铺进 token 窗口——token 成本高且无分级控制；(3) 记忆、知识、技能分散在不同系统中，Agent 需要学习多种 API 范式。

## 旧范式 vs 新范式
- **旧做法**：Vector DB + Prompt Stuffing：用向量相似度搜索找相关文档 → 把所有结果塞进 LLM 上下文窗口。检索不可观测，无分层加载，记忆/知识/技能各自为政。
- **新做法**：Context Database + Tiered Loading：统一的 `viking://` 文件系统 → 先看目录摘要（L0）→ 再看概览（L1）→ 必要时才加载全文（L2）。检索路径可追踪，token 消耗按需加载。

## 生产力影响 (How)
- **LoCoMo 记忆准确率**：从 24-57%（原生 Agent）提升至 80-83%（+OpenViking），同时输入 token 减少 34-91%
- **tau2-bench 任务成功率**：零售 +6.87pp、航空 +11.87pp
- **可观测性**：每次检索保留目录浏览轨迹，结果不对时可以追溯到具体路径
- **Session→Memory**：会话结束后异步提取用户偏好和 Agent 经验进入长期记忆

## 采用成本
pip install 一条命令启动，需要配置 embedding 模型提供商（支持 Volcengine/OpenAI/Ollama 等）。集成到 Agent 需调用 Viking URI 协议。学习曲线 1-2 天。

## 采用案例
- **OpenClaw + OpenViking**：LoCoMo 记忆准确率 24.20%→82.08%
- **Hermes Agent + OpenViking**：记忆准确率 33.38%→82.86%
- **Claude Code + OpenViking**：记忆准确率 57.21%→80.32%

## 风险/局限
- AGPLv3 许可证可能限制商业闭源使用
- 目前仍为早期版本（v0.3.x），API 可能变动
- 依赖外部 embedding 模型提供商

## 核心线索
- GitHub：https://github.com/volcengine/OpenViking
- 首发来源：火山引擎开源
- 当前状态：活跃开发中