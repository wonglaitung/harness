# i-have-adhd — Agent 输出协议新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次将"Agent 输出格式"定义为可安装、可复用的协议（SKILL.md），而非提示词模板 |
| 采用广度 | ☆☆☆/5 | GitHub 422★/天，被 HN 广泛讨论和验证 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年9月8日 GitHub trending，同时登上 HN 首页 288 分 |
| 社区热度 | ☆☆☆☆/5 | HN 288 分，GitHub 422★/天，多语言 README 社区响应 |
| **总体判断** | ✅ | **新范式 —— Skill-as-Output-Protocol：将 Agent 的行为协议化为可安装的代码包** |

## 技术定义 (What)

i-have-adhd 不只是一个"提示词"，而是一个可安装的 **Agent 行为协议**。它定义了 10 条强制规则（行动优先、编号步骤、禁止"Hope this helps!"结尾等），以 `SKILL.md` 文件形式分发，通过 Claude Code plugin marketplace 安装后自动生效。

核心洞察：Agent 的输出格式应该被当作**可编程接口**来管理，而非一次性的提示词工程。

## 行业痛点 (Why)

Coding Agent 普遍存在"答案埋没"问题——大量铺垫、过度解释、以"Hope this helps!"结尾，导致开发者需要反复滚动才能找到真正需要采取的行动。这不仅浪费时间，更在 Agent 辅助编程场景中降低了"行动密度"。随着 Agent 使用频率指数增长，这个摩擦被放大了数百倍。

## 旧范式 vs 新范式

- **旧做法**：在 CLAUDE.md 或 system prompt 中写"be concise"——不可复用、没有版本管理、每个项目都要重写
- **新做法**：将输出协议定义为 `SKILL.md`，通过 plugin marketplace 安装，开箱即用，fork 可定制

## 生产力影响 (How)

- 每次 Agent 交互节省 10-30 秒的"滚动到答案"时间
- 按每天 50 次 Agent 交互计算，日节省 8-25 分钟
- 10 条规则适配 ADHD 思维模式，降低认知负荷
- 规则的"可安装性"使其成为基础设施而非一次性配置

## 采用成本

- 安装：一条命令 `/plugin install`
- 学习：零成本，安装后自动生效
- 定制：fork 后编辑 `SKILL.md` 即可

## 采用案例

- 大量 Claude Code 用户已安装并报告显著改善
- 被翻译为中文、葡语、日语、越南语、韩语、泰语——证实跨文化需求
- 与 Context Mode 互补：前者管 Agent 输入（上下文），后者管 Agent 输出（格式）

## 风险/局限

- 主要面向 Claude Code 生态（但协议设计本身是通用的）
- 禁止"preamble/recap/closer"在某些场景可能过于激进（如新手用户需要解释）
- 规则可 fork 但需要手动管理版本更新

## 核心线索

- GitHub：https://github.com/ayghri/i-have-adhd
- 首发来源：GitHub Trending + HN 首页
- HN 讨论：288 分
- 当前状态：活跃爆发期