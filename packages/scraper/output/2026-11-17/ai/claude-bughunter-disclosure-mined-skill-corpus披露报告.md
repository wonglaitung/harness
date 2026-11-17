# Claude-BugHunter — Disclosure-Mined Skill Corpus（披露报告挖掘出的可审计技能语料）

## 技术定义 (What)
一个 83 个技能的捆绑包，但关键不在数量，而在**每个技能的来源**：58 个 hunt-* 技能从 681 份已公开的 HackerOne 漏洞披露报告中提炼而成（其中 433 条被单独引用、可逐条回溯到原始报告），覆盖 24 类核心漏洞。技能全部是标准 SKILL.md，一次安装可分发到 Claude Code / OpenCode / Codex CLI / Hermes / Google AntiGravity 五个 harness。

## 行业痛点 (Why)
Agent 领域技能库的通病是"作者凭经验写规则"，无法验证一条技能到底从哪来、准不准、是否过时。安全领域尤其致命：一条过时的绕过 payload 会让 Agent 在真实授权测试中浪费时间甚至越界。此前业界解法是事后评测（如 NVIDIA SkillEvaluator 打分），但评测只能测"写得对不对"，测不出"凭什么这么写"。

## 旧范式 vs 新范式
- **旧做法**：经验驱动 + 事后评测：安全技能由专家凭经验撰写 → 打包发布 → 用评测框架打分筛选质量。
- **新做法**：语料驱动 + 来源可审计：技能从真实披露报告中反向挖掘 → 每条 pattern 挂原始报告引用 → 质量由**可追溯性**保证，而非打分。同时把"技能"当作跨 harness 的中立资产（一份 SKILL.md 多端加载），并用插件命名空间（claude-bughunter:）做版本化分发。

## 生产力影响 (How)
给"Agent 领域专家化"提供了一条低争议的质量路径：不必证明"我的 prompt 更好"，只需证明"我的每条规则都能指向一个真实案例"。对做垂直 Agent 的团队，这提示了一个可复用的构建流水线——先找该领域 500+ 份公开真实案例，再反向蒸馏成技能，而非直接问模型"写个渗透测试专家"。

## 采用成本
安装 1 分钟（plugin marketplace 一行命令）。真正成本在信任校准：需要人工抽查技能是否贴合自己的测试范围（in-scope / OOS 判定），且仅限**已授权**的 red-team 与 bug bounty 场景，误用有法律风险。

## 核心线索
- GitHub：https://github.com/elementalsouls/Claude-BugHunter
- 来源：https://github.com/trending/python?since=daily
- 发布时间：2026-11-17
