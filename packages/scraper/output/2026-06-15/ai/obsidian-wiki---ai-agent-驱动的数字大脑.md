# obsidian-wiki - AI Agent 驱动的数字大脑

## 技术定义 (What)
基于 Andrej Karpathy "LLM Wiki" 模式的框架，让 AI Agent 自动构建和维护个人知识库。知识一次编译成互联的 markdown 文件（Obsidian vault），后续直接查询，无需重复问 LLM 或运行 RAG。

## 行业痛点 (Why)
- 每次问 LLM 同样问题，浪费时间金钱
- RAG 每次检索，计算成本高
- 知识碎片化，缺乏结构化组织
- 多 Agent 工具间无统一知识库

## 旧范式 vs 新范式
- **旧做法**：每次提问都重新检索或调用 LLM，无知识沉淀
- **新做法**：知识一次编译进互联 markdown 文件，AI Agent 持续维护，形成"第二大脑"

## 四阶段工作流
1. **Ingest**：读取源材料（markdown、PDF、JSONL、图片、聊天导出等）
2. **Pull Information**：提取概念、实体、关系
3. **Connect**：自动建立双向链接，整合到现有知识网络
4. **Answer**：从结构化知识库回答查询

## 支持的 AI Agent
**完整兼容**：Claude Code、Cursor、Windsurf、Codex、Gemini CLI、Hermes、Pi、Kilo、GitHub Copilot CLI、Trae、OpenClaw、Aider 等 20+ Agent

**核心机制**：
- 每个 Agent 一个 `AGENTS.md` 或 `CLAUDE.md` 引导文件
- `.skills/` 目录下技能文件自动发现
- Slash 命令：`/wiki-ingest`、`/wiki-query`、`/wiki-status` 等

## 生产力影响 (How)
- **个人知识管理**：自动构建可查询的知识网络
- **团队协作**：共享 vault，多人协同维护
- **跨 Agent 复用**：一次构建，所有 Agent 可用

## 采用成本
- 安装：`pip install obsidian-wiki` 或 `npx skills add Ar9av/obsidian-wiki`
- 配置：运行 `obsidian-wiki setup --vault /path/to/vault`
- 学习曲线：Karpathy LLM Wiki 模式，30 分钟理解核心理念
- 依赖：Obsidian（可选，用于可视化）

## 核心线索
- GitHub：https://github.com/Ar9av/obsidian-wiki
- 来源：GitHub Trending (Python)
- 发现时间：2026-06-15
- 今日 Stars：135
- 灵感来源：https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f