# OpenViking — Context Database：Agent 上下文数据库新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次提出「Context Database」概念：`viking://` 协议 + L0/L1/L2 三层分层加载 + 确定性文件系统检索，颠覆了传统黑箱向量检索 |
| 采用广度 | ☆☆☆/5 | 已支持 Claude Code、Codex、OpenClaw、Hermes、Cursor、MCP 等 10+ Agent 集成 |
| 时间新鲜 | ☆☆☆☆/5 | 2026年活跃开发中，由字节跳动火山引擎开源 |
| 社区热度 | ☆☆☆☆/5 | GitHub 趋势榜 Python 日榜前列，有完整文档站和 Live Demo |
| **总体判断** | ✅ | **新范式 — Context Database / `viking://` 协议** |

## 技术定义 (What)
OpenViking 是 AI Agent 的**上下文数据库**。它将 Agent 的记忆、资源和技能统一在一个虚拟文件系统下（`viking://` 协议），Agent 用 `ls`、`tree`、`find` 等确定性操作浏览自己的上下文——而非查询黑箱向量数据库。内容按三个层级处理：L0（摘要 ~100 tokens）、L1（概览 ~2k tokens）、L2（完整原文），按需逐层加载，大幅降低 token 消耗。

## 行业痛点 (Why)
现有 Agent 记忆方案（RAG + 向量数据库）存在根本缺陷：(1) 检索是黑箱，无法解释和调试；(2) 无分层加载，上下文窗口被无关信息撑爆；(3) 无确定性检索语义，Agent 无法像开发者操作文件系统一样精确获取信息。LoCoMo 基准测试中，原生 Agent 记忆准确率仅 24-57%。

## 旧范式 vs 新范式
- **旧做法**：向量嵌入 → 相似度检索 → 黑箱 Top-K 结果 → 全部塞入上下文
- **新做法**：`viking://` URI → 目录递归检索 → L0/L1/L2 按需分层加载 → 可观测的检索轨迹

## 生产力影响 (How)
- **Token 节省 34-91%**：分层加载避免在上下文窗口塞入无关信息
- **准确率跃升**：LoCoMo 从 24-57% 提升到 80-83%；tau2-bench 任务成功率提升 +6.87 到 +11.87pp
- **可调试性**：每次检索保留目录浏览轨迹，可追溯结果来源
- **Session→Memory**：会话结束后异步提取用户偏好和Agent经验到长期记忆

## 采用成本
- `pip install openviking` 零门槛
- 支持 Volcengine、OpenAI、Kimi、GLM、Ollama 等主流 Provider
- 学习曲线低：Agent 用熟悉 POSIX 语义操作上下文

## 采用案例
- **Claude Code + OpenViking**：LoCoMo 准确率从 57.21% → 80.32%
- **OpenClaw + OpenViking**：从 24.20% → 82.08%
- **Hermes + OpenViking**：从 33.38% → 82.86%

## 风险/局限
- 目前由单一公司（字节跳动/火山引擎）主导，社区贡献度待观察
- AGPLv3 许可证对企业部署有约束
- 生态尚未形成标准化共识

## 核心线索
- GitHub：https://github.com/volcengine/OpenViking
- Docs：https://docs.openviking.ai
- 来源：GitHub Trending Python（日榜）
- 发布时间：2026年活跃开发
- 当前状态：活跃