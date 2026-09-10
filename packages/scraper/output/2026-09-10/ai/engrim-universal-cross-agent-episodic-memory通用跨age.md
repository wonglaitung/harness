# Engrim — Universal Cross-Agent Episodic Memory（通用跨Agent情节记忆引擎）

## 技术定义 (What)
Engrim 是一个本地优先、项目级 SQLite 记忆引擎，实现跨模型/跨 Agent 的无状态记忆。核心创新：(1) 将项目决策、约束、架构选择从 LLM 上下文中"外化"为持久记忆；(2) 混合检索（BM25 关键词 + model2vec 语义向量）；(3) Agent Provenance 追踪——每条记忆记录来源 Agent（Antigravity/Claude Code/Cursor/Codex），实现多 Agent 协作时的"记忆不丢失"。实测效果：153k tokens 工作成果压缩为 <1000 tokens 记忆（99% 压缩），在 105 次会话、跨 Google/Anthropic/OpenAI 三套 Agent 间零上下文丢失。

## 行业痛点 (Why)
(1) 上下文窗口稀释：随对话增长，推理质量下降；(2) 切换模型/工具即失忆：这是真实痛点，开发者常在 Claude Code、Cursor、Gemini CLI 间切换；(3) 重复 token 浪费：每次重开会话要重新喂大量背景信息；(4) 记忆供应商锁定：各 AI 平台的记忆系统互相隔离，无法跨平台共享项目知识。

## 旧范式 vs 新范式
- **旧做法**：Agent 记忆内嵌在 LLM 的上下文窗口中，每次会话重新加载。切换模型/环境意味着记忆完全丢失。开发者被迫在每次新会话中重新解释项目架构和约束。或者依赖各平台各自的记忆系统（如 ChatGPT Memory），但这些系统互不兼容、不可迁移。
- **新做法**：将"项目记忆"从 LLM 上下文窗口中剥离为独立基础设施层。Agent 无状态化——上下文清空不影响项目记忆恢复。跨平台 Agent Provenance 追踪记录每条决策来源。记忆引擎成为 Agent 生态的"瑞士"——不绑定任何单一模型或平台（Antigravity/Claude/Cursor/Codex 全支持）。

## 生产力影响 (How)
对多 Agent 工作流的开发者是杀手级工具。153k tokens → 1k tokens 的压缩率意味着每次会话重启节省 99% token 成本。支持在 Claude Code 中做架构决策、切到 Cursor 写代码、再用 Gemini CLI review——全程记忆一致。105 次会话/186 单元测试/零回归的实测证明其生产可靠性。

## 采用成本
pip install engrim；5 分钟配置；零学习曲线；本地 SQLite，零服务成本

## 核心线索
- GitHub：https://github.com/timgordontg/engrim
- 来源：https://news.ycombinator.com/show — Show HN 91 points
- 发布时间：2026-09-10
