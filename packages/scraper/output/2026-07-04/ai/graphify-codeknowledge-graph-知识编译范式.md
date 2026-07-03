# Graphify — Code→Knowledge Graph 知识编译范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次定义"任意输入→知识图谱"的Agent Skill范式，引入"God Node""Surprising Connection"等新概念 |
| 采用广度 | ☆☆☆/5 | GitHub日增937 stars，Claude Code官方Skill格式 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月首发 |
| 社区热度 | ☆☆☆☆/5 | GitHub Trending #2 Python，日增937 stars |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
Graphify 是一个AI编码助手技能（Claude Code Skill），将任意文件夹中的代码、PDF、Markdown、截图、白板照片等多模态输入编译为可查询的知识图谱。它使用 tree-sitter AST分析代码调用关系，Claude Vision提取图片/论文概念，Leiden社区检测算法发现隐含结构，最终输出交互式图谱、Wikipedia风格Wiki和持久化JSON。

## 行业痛点 (Why)
开发者面临"信息过载但结构缺失"问题——代码库、论文、截图散落各处，Agent每次查询需重新读取全部原始文件，token消耗巨大且缺乏结构化理解。Andrej Karpathy的`/raw`文件夹问题正是典型：大量非结构化素材无法被高效利用。

## 旧范式 vs 新范式
- **旧做法**：Agent每次查询重新读取所有原始文件，token随文件数线性增长，52个文件需读取全部内容
- **新做法**：一次编译为持久化知识图谱，后续查询直接在图谱上操作，71.5x token减少，跨会话持久可用

## 生产力影响 (How)
- **Token效率**：混合语料库（代码+论文+图片）71.5倍token减少
- **结构发现**：自动识别"God Node"（最高连接度概念）和"Surprising Connection"（跨域隐含关联）
- **持久可用**：graph.json跨会话持久化，无需重复编译
- **多格式输出**：交互式HTML、Obsidian Vault、Wikipedia Wiki、Neo4j Cypher、SVG/GraphML
- **增量更新**：SHA256缓存 + `--update`模式仅处理变更文件

## 采用成本
- **安装**：`pip install graphifyy && graphify install`，1分钟完成
- **依赖**：Python 3.10+、Claude Code、NetworkX/Leiden/tree-sitter（自动安装）
- **学习曲线**：低——`/graphify .`一行命令即可运行
- **成本**：需Claude API调用用于概念提取，大代码库约$1-5/次编译

## 采用案例
- **Karpathy repos + 5论文 + 4图片（52文件）**：71.5x token减少，发现代码-论文跨域关联
- **代码+Transformer论文混合语料（4文件）**：5.4x token减少，结构清晰度提升
- **Git Hook自动同步**：每次commit后自动重建图谱，多Agent并行工作时保持知识库最新

## 风险/局限
- **提取准确性**：边标记为EXTRACTED/INFERRED/AMBIGUOUS，推断边可能不准确
- **小代码库收益有限**：6文件时约1x（文件少时上下文窗口足够）
- **依赖Claude Vision**：图片/论文提取需Claude API，有成本
- **单Skill生态**：目前仅支持Claude Code，未扩展到其他Agent

## 核心线索
- GitHub：https://github.com/safishamsi/graphify
- 首发来源：GitHub Trending Python
- 发布时间：2026年7月
- 当前状态：活跃（v1已发布，CI通过）