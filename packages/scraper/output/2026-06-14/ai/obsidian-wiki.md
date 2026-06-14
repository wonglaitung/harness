# Obsidian Wiki

## 技术定义 (What)
基于 Andrej Karpathy LLM Wiki 模式的 AI Agent 数字大脑框架，让 Agent 将知识编译成互联的 Markdown 文件并持续更新，避免重复询问相同问题。

## 行业痛点 (Why)
每次遇到相同问题都需重新解释上下文，或依赖 RAG 检索（成本高、延迟大）。Agent 无法积累个人知识，每次对话从零开始。

## 旧范式 vs 新范式
- **旧做法**：每次对话重新提供上下文，或使用向量数据库做 RAG（embedding 成本 + 检索延迟）。知识分散在多个工具，无法形成个人知识图谱。
- **新做法**：Agent 直接读写 Obsidian vault（Markdown 文件），支持 PDF/JSONL/图片/聊天记录等多格式输入，自动提取概念、实体、关系，构建双向链接的知识网络。一次编译、持续更新、即时查询。

## 生产力影响 (How)
开发者可用自然语言向 Agent "投喂"知识，Agent 自动整理成可检索的数字大脑。支持 Claude Code、Cursor、Codex、Gemini 等 15+ 主流 Agent，技能跨平台复用。

## 采用成本
pip install 即用，需指定 Obsidian vault 路径。setup.sh 自动为所有 Agent 安装技能。学习曲线平缓，核心是"告诉 Agent 记住什么"。

## 核心线索
- GitHub：https://github.com/Ar9av/obsidian-wiki
- 来源：https://github.com/Ar9av/obsidian-wiki
- 发布时间：2026-06-14
