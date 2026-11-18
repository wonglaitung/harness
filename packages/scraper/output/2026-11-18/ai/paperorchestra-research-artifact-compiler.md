# PaperOrchestra — 论文即构建产物（Research-Artifact Compiler）

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 把"论文写作"重构为多 Agent 编译流水线；输入是 (raw_materials_dir, latex_template_dir)，输出是 submission-ready 产物目录。模板从"事后套壳"变为"前置格式约束" |
| 采用广度 | ☆☆/5 | Google Cloud AI Research 出品；arXiv 2604.05018；GitHub 单日 +1,072 stars（当日 Python trending 第 2） |
| 时间新鲜 | ☆☆☆/5 | arXiv 首发 2026-04（约 7 个月），GitHub 爆发 2026-11；略超 6 个月但社区热度为近期 |
| 社区热度 | ☆☆☆☆/5 | 单日 1,072 stars，是本次抓取中增速最高的 AI 研究类项目 |
| **总体判断** | ✅ | **新范式（有条件：时间新鲜度略超）** |

## 技术定义 (What)

Google Cloud AI Research 开源的多 Agent 流水线，把"未结构化的写前材料"（一个 idea + 实验日志）编译成"可提交的 LaTeX 手稿"。它把论文写作拆成 5 个专职 Agent（Outline / Literature Review / Section Writing / Content Refinement / Plotting），并支持指定会议 LaTeX 模板（如 cvpr2025）作为"目标产物格式"，同时自动搜索并整合 Semantic Scholar 文献、从代码生成图表。

## 行业痛点 (Why)

从"做完实验"到"能投稿"之间存在巨大的非科研性劳动：查文献、写八股、画图、套模板、调格式。这部分工作消耗研究者大量时间却不产生科学价值，且极易在长周期中丢失实验细节。

## 旧范式 vs 新范式

- **旧做法**：论文写作 = 人的表达行为。LLM 辅助 = 单次 prompt 生成某一段文字，人是唯一编排者与整合者，"投稿就绪"由人负责拼装 LaTeX。
- **新做法**：论文 = 一条可重放的构建流水线产物。输入 (原始材料目录, LaTeX 模板目录) → 输出提交就绪目录。写作拆解为有明确 I/O 契约的多 Agent 阶段；图表由 Plotting Agent 从代码生成。心智模型与软件工程 source→build artifact 同构。

## 生产力影响 (How)

对研究者：把 2-4 周写作期压缩为"整理材料 + 审阅产物"；修改实验日志重跑流水线，全文与图表自动同步，消除"正文数据与图不一致"的经典错误。对工程团队：证明"多阶段 Agent + 产物格式约束"可迁移到任何长文档产物（技术报告、合规文档、标书）。

## 采用成本

低-中。Python 3.11 + Conda，需 Semantic Scholar / Gemini(Vertex) / OpenAI 三套 API key。数据集未随仓库发布，目前只能用自有材料试跑；LaTeX 模板需自备。仓库自带 Streamlit 交互 demo。

## 采用案例

- Google Cloud AI Research 自用：作者列表含 Tomas Pfister（Google Cloud AI Research 负责人），属机构级内部产出而非周末项目。
- 下游复用方向：技术报告生成、合规文档流水线、标书生成——同一"模板即约束 + 多阶段 Agent"骨架。

## 风险/局限

- **模板污染风险**：支持"指定会议模板"意味着可大批量产出形似投稿的手稿，学术会议审稿系统将面临新的量级压力。
- **数据集缺位**：README 明确声明 dataset 不包含在仓库中，复现门槛高。
- **非官方支持**：README Disclaimer 明确 "This is not an officially supported Google product"。
- **文献 Agent 依赖 Semantic Scholar API**，速率限制会直接卡住流水线。

## 核心线索

- GitHub：https://github.com/google-research/paper-orchestra
- 论文：arXiv 2604.05018 (Song, Song, Pfister, Yoon)
- 首发来源：GitHub Python trending，2026-11（单日 +1,072 stars）
- 当前状态：活跃（单日爆发期）
