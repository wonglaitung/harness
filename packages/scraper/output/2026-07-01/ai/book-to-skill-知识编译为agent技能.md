# book-to-skill — 知识编译为Agent技能

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次定义"Knowledge Compilation"——将书籍/文档编译为Agent可按需加载的结构化技能，提出"Discovery Loop Tax"概念量化知识检索成本 |
| 采用广度 | ☆☆☆☆/5 | 基于开放Agent Skills标准，兼容GitHub Copilot CLI、Amp、Claude Code三大平台 |
| 时间新鲜 | ☆☆☆☆/5 | 2026年5月发布，TrendShift Python #10 |
| 社区热度 | ☆☆☆/5 | GitHub日增205星，TrendShift #10 Python仓库；社区关注知识管理范式 |
| **总体判断** | ✅ | **新范式 — 知识从"被动阅读"到"主动编译"的范式转换** |

## 技术定义 (What)

book-to-skill是一个知识编译器，将技术书籍、文档文件夹、论文集合转化为Agent可按需加载的结构化技能。核心创新在于：不是把书"喂"给LLM，而是将书"编译"成SKILL.md（核心心智模型+章节索引）+ 按需加载的章节文件 + 术语表 + 模式库 + 速查表。Agent只需加载~5K token的核心+1个章节（~1K token），而非整本书的200K+ token。

## 行业痛点 (Why)

1. **Discovery Loop Tax**：让Agent直接读PDF，它会反复导航（查目录→翻页→回溯），每次导航都消耗token且被压缩，最终得到无法验证的降质摘要
2. **Context Dump浪费**：把整本书塞入上下文，每轮对话都重复支付200K+ token成本
3. **知识遗忘**：读完书3个月后记不住第7章，传统笔记也无人再翻

## 旧范式 vs 新范式

- **旧做法**：把PDF/EPUB直接喂给Agent → 每轮对话消耗全量token → Agent在导航循环中浪费token → 得到降质摘要
- **新做法**：一次性编译书籍为结构化技能 → Agent按需加载单章节 → 24-51× fewer tokens → 无导航循环，源文件可验证

## 生产力影响 (How)

- **Token节省**：比全量dump节省24-51× token，比Discovery Loop节省2.4-15.6×
- **知识持久化**：编译一次，永久可用，跨会话记忆
- **零幻觉**：Agent从实际编译内容回答，而非凭记忆编造
- **成本**：约$1/本书的编译成本，之后每次查询仅~5K token

## 采用成本

- **时间**：5分钟安装，编译一本书约3-5分钟
- **金钱**：编译成本约$1/本（LLM API费用），之后免费使用
- **学习曲线**：极低——`/book-to-skill your-book.pdf` 一行命令

## 采用案例

- **技术书籍**：Think Python 2（244页→19章节技能），Working Backwards（371页→10章节技能）
- **内部文档**：架构决策记录、运维手册、入职指南 → 一个技能覆盖整个docs/目录
- **品牌设计系统**：品牌手册 → 团队可查询的技能
- **研究集群**：论文+笔记 → 统一技能，新论文可增量合并

## 风险/局限

- 章节自动检测需要明确的"Chapter N"标题，纯标题/罗马数字的书籍无法自动分段
- EPUB提取需ebooklib才能获得最佳质量
- 技术书籍需Docling（~1.5s/页），比纯文本慢
- 单次一次性阅读场景下，直接用PDF Agent可能更简单

## 核心线索

- GitHub：https://github.com/virgiliojr94/book-to-skill
- 首发来源：GitHub Trending Python
- 发布时间：2026年5月
- 当前状态：活跃，快速迭代中