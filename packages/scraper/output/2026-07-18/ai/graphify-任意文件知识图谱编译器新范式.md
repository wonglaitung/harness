# Graphify

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次将任意文件（代码/PDF/图片/视频）编译为可查询知识图谱，引入"God Nodes""Surprising Connections"等新概念 |
| 采用广度 | ☆☆☆☆/5 | 支持 Claude Code、Codex、OpenCode、Cursor、Gemini CLI 等主流编码Agent |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年首发，GitHub trending 1476星/日 |
| 社区热度 | ☆☆☆☆/5 | GitHub日增1476星，PyPI发布，活跃CI |
| **总体判断** | ✅ | **新范式 — 知识编译器** |

## 技术定义 (What)
Graphify是一个**知识编译器**：将任意文件夹（代码、PDF、Markdown、截图、白板照片、甚至其他语言的图片）编译为一个可查询的结构化知识图谱。它不是搜索工具，而是将非结构化信息"编译"为Agent可直接导航的结构——类似编译器将源码编译为可执行文件。

核心创新点：
- **God Nodes**：图谱中度最高的概念节点，揭示"一切通过什么连接"
- **Surprising Connections**：按复合分数排名的跨域关联，代码-论文边比代码-代码边排名更高
- **渐进式诚实标注**：每条边标记为 EXTRACTED/INFERRED/AMBIGUOUS，区分"发现的"vs"猜测的"
- **71.5x Token压缩**：52文件混合语料库上，每查询token数比读原始文件减少71.5倍

## 行业痛点 (Why)
当前AI编码Agent面临"上下文爆炸"问题：代码库越大，需要读的文件越多，token消耗线性增长。传统RAG检索碎片化，缺乏结构化关联。Andrej Karpathy的`/raw`文件夹问题——论文、推文、截图、笔记散落，无法系统化查询——是典型场景。

## 旧范式 vs 新范式
- **旧做法**：Agent逐文件读取源码/文档 → token线性消耗 → 上下文窗口溢出 → 信息碎片化
- **新做法**：一次性将整个文件夹编译为持久化知识图谱 → Agent按图导航 → 71.5x token压缩 → 跨域关联发现

## 生产力影响 (How)
1. **Token成本暴降**：大型代码库查询从O(n)文件读取降为O(1)图谱查询
2. **跨域发现**：自动发现代码与论文、设计图与实现之间的隐含关联
3. **持久化复用**：graph.json跨会话持久化，无需重复读取原始文件
4. **SHA256增量缓存**：只重新处理变更文件，支持`--watch`自动同步
5. **多格式输出**：HTML交互图、Obsidian vault、Wiki、Neo4j Cypher、MCP server

## 采用成本
- **时间**：`pip install graphifyy && graphify install`，5分钟内完成
- **金钱**：免费开源，需Claude API调用（知识提取阶段）
- **学习曲线**：低——`/graphify .`一条命令即可运行

## 采用案例
- **Claude Code用户**：作为Skill安装，`/graphify .`一键编译代码库
- **Karpathy /raw文件夹场景**：论文+推文+截图混合语料，71.5x压缩
- **大型代码库维护**：AST+调用图提取，God Nodes揭示架构关键点

## 风险/局限
- INFERRED边可能产生虚假关联（但已明确标注）
- 依赖Claude视觉能力提取图片/截图中的概念
- 小型代码库（<10文件）压缩收益有限
- PyPI包名暂时为`graphifyy`（正在 reclaim `graphify`）

## 核心线索
- GitHub：https://github.com/safishamsi/graphify
- 首发来源：GitHub Trending (Python)
- 发布时间：2026年
- 当前状态：活跃开发，v1已发布