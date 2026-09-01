# Memoryfields — Agent Memory as a File Format

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ⭐⭐⭐⭐⭐/5 | 首次提出"Agent记忆应该是数据格式而非处理管道"，颠覆 RAG/图数据库/向量数据库三大主流范式 |
| 采用广度 | ⭐⭐/5 | 概念刚发布（2026-08-31），尚无项目采用，但理念与 Karpathy Wiki 一脉相承 |
| 时间新鲜 | ⭐⭐⭐⭐⭐/5 | 发布于 2026-08-31，距今仅数天 |
| 社区热度 | ⭐⭐⭐/5 | HN 161 points，引发广泛讨论 |
| **总体判断** | ✅ **新范式** | 概念创新极强，本质是对现有Agent记忆架构的根本性反思 |

## 技术定义 (What)

Memoryfield 是一种**便携式 Agent 记忆文件格式**：一个 ZIP 包内含 Markdown 页面 + YAML frontmatter + SQLite 向量索引。Agent 通过语义搜索直接跳转到相关记忆页，一次并行读取所有相关页面。

```
my-memories.memoryfield.zip
├── carbon-fibre-woks.md
├── finnish-bureaucracy-tips.md
├── wec-2026-season-notes.md
└── nomic-embed-text-v1.5.sqlite3
```

## 行业痛点 (Why)

现有三种 Agent 记忆系统全部失败：
- **平台绑定型**：从对话历史挖掘记忆，偏向"关于你"而非"关于世界"
- **过度复杂型**：需要 pgvector + Neo4j + 独立LLM 判断什么值得记忆
- **高现代主义型**：将记忆提炼为孤立的"事实"，剥离上下文

三者共同错误：**把记忆当作处理管道，而非数据**。

## 旧范式 vs 新范式
- **旧做法**：RAG管道（分块→嵌入→检索→重排序）、知识图谱遍历（工具调用 N+1 次）、多阶段摘要
- **新做法**：Agent 直接将记忆写成 Markdown 文件 → 语义搜索 → 并行读取所有相关页（最多2次工具调用）

## 生产力影响 (How)

- 记忆系统从"需要运维的基础设施"降级为"Agent可直接读写的文件"
- 知识图谱遍历从 N+1 次工具调用降为 2 次
- 模型上下文窗口不会被无关信息污染
- 记忆可移植、可版本控制、可人工审查

## 采用成本
- 时间：30分钟理解概念并实施
- 金钱：几乎为零（只需 SQLite + 嵌入模型）
- 学习曲线：低，Markdown + YAML 是通用技能

## 风险/局限
- 每页 ~8KB 软限制（vector embedding 容量限制）
- 对长文档（如PDF）不适用——但记忆本不应是长文档
- 语义搜索质量依赖 embedding 模型

## 核心线索
- 来源：https://calpaterson.com/memoryfields.html
- 发布时间：2026-08-31
- 当前状态：概念发布 / 试验中