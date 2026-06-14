# obsidian-wiki

## 技术定义 (What)
基于 Karpathy LLM Wiki 模式的 AI Agent 数字大脑框架，让 Agent 自动构建和维护 Obsidian 知识库。通过 Markdown 文件作为技能定义，支持 Claude Code、Cursor、Codex、Gemini CLI 等所有主流 AI 编码 Agent。

## 行业痛点 (Why)
重复向 LLM 提问相同问题，或为相同上下文反复运行 RAG，浪费 token 和时间。知识散落在聊天记录、文档、代码注释中，缺乏结构化管理和自动更新机制。

## 旧范式 vs 新范式
- **旧做法**：1）每次提问都重新检索和生成；2）使用传统笔记工具手动整理知识；3）依赖外部 RAG 系统管理知识，缺乏与 Agent 工作流的深度集成。
- **新做法**：让 Agent 自动从代码、文档、对话中提取知识，编译成互联的 Markdown 文件（数字大脑）。Agent 通过读取这些文件快速获取上下文，避免重复计算。支持增量更新和跨会话持久化。

## 生产力影响 (How)
将知识管理从手动整理转变为 Agent 驱动的自动化流程。一次编译、多次复用，显著降低重复提问的 token 成本。Obsidian 可视化让知识图谱可审计、可导航，适合长期项目知识积累。

## 采用成本
安装简单（pip install 或 npx skills add），配置 Obsidian vault 路径即可。学习成本中等，需要理解 wiki-ingest、wiki-query 等 Agent 指令。适合已有 Obsidian 使用习惯的开发者。

## 核心线索
- GitHub：https://github.com/Ar9av/obsidian-wiki
- 来源：https://github.com/Ar9av/obsidian-wiki
- 发布时间：2026-06-14
