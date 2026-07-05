# last30days-skill

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次定义"社交信号聚合搜索"概念：用真实人群的upvote/like/真金白银作为排序信号，而非SEO/编辑筛选 |
| 采用广度 | ☆☆☆/5 | Claude Code Marketplace官方收录，50+ Agent Skills平台支持，但独立项目引用尚少 |
| 时间新鲜 | ☆☆☆☆☆/5 | v3活跃开发，GitHub Trending #1 Repository of the Day |
| 社区热度 | ☆☆☆☆/5 | GitHub Trending当日#1，236 stars/day，Trendshift收录 |
| **总体判断** | ✅ | **新范式 — 社交信号驱动的Agent搜索** |

## 技术定义 (What)
一个AI Agent技能，将Reddit、X/Twitter、YouTube、TikTok、Polymarket、HN、GitHub等十多个平台的社交信号（upvote、like、真金白银投注）聚合为统一搜索，由AI Agent裁判合成为一份简报。核心创新：**用人群注意力和钱包投票排序，而非SEO或编辑筛选**。

## 行业痛点 (Why)
当前AI搜索面临"围墙花园"困境：Google搜不到Reddit评论，ChatGPT只有Reddit没有X，Gemini有YouTube没Reddit，Claude原生全无。每个平台是独立孤岛，各有API和认证。用户无法一次性获取跨平台的真实人群观点。

## 旧范式 vs 新范式
- **旧做法**：Google/Perplexity等搜索引擎基于SEO和编辑排序，或单一平台AI（ChatGPT+Reddit）只能搜索一个围墙花园
- **新做法**：Agent桥接十多个平台，用真实社交参与度（upvote/like/真金白银）作为排序信号，跨平台评分对比后合成简报

## 生产力影响 (How)
- 会议前30秒获取人物/公司最新动态（跨X、Reddit、YouTube、GitHub）
- 工具对比时获取社区真实评价而非营销文案
- 旅行前获取实时社区反馈（排队时间、关闭项目）
- 投资决策时参考Polymarket真金白银概率

## 采用成本
- 免费（BYOK模式，自带各平台API Key）
- 安装：Claude Code一行命令 `/plugin marketplace add`
- 学习曲线低：自然语言交互，零配置启动Reddit/HN/GitHub

## 采用案例
- **会议准备**：`/last30days Peter Steinberger` → 发现其加入OpenAI Codex团队、GitHub 23 PRs 85%合并率
- **工具对比**：`/last30days OpenClaw vs Hermes vs Paperclip` → 跨平台架构对比表
- **时事追踪**：`/last30days Iran vs USA` → Polymarket 74%停火概率 + 27条X帖 + 10个YouTube视频

## 风险/局限
- 依赖BYOK（自带Key），平台API变更可能导致中断
- 社交信号有偏见：Reddit/X用户群不代表全体
- Polymarket流动性低的事件信号不可靠
- 合成质量依赖底层LLM能力

## 核心线索
- GitHub：https://github.com/mvanhorn/last30days-skill
- 首发来源：GitHub Trending
- 发布时间：2025年（v3当前版本）
- 当前状态：活跃开发中