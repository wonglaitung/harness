# COG-second-brain — V-model 验证生命周期：Worker 永不给自己打分

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 明确命名并落地 **V-model verification lifecycle**，核心约束是 "the worker never grades its own homework"：6 workers 负责读写，4 个 **read-only verifiers** 独立裁决。配套 **memory-hygiene**（对持久记忆重验证 + `last_verified` 时间戳 + confidence）把「记忆过期」变成一等概念 |
| 采用广度 | ☆☆/5 | 43 skills 跨 6 个 Agent 载体（Claude Code / Antigravity / Cursor / Kiro / Gemini CLI / Codex），符合 Agent Plugins 1.0.0 规范；但主要仍是单一作者生态，外部独立集成少 |
| 时间新鲜 | ☆☆☆☆/5 | 新项目，GitHub Python trending daily 出现 |
| 社区热度 | ☆☆/5 | 37 stars/day —— 明显弱于同批项目（AutoSwarm 64、ffmpeg-skill 331），HN 无讨论 |
| **总体判断** | ⚠️ | **观察中：架构模式有价值，社区验证不足** |

## 技术定义 (What)

COG = Cognition + Obsidian + Git。整个「第二大脑」就是一棵 `.md` 文件树 + Git 历史，没有数据库。

架构分三层：

- **43 个 Skills**：编排层，读 `SKILL.md` 执行（onboarding / braindump / daily-brief / weekly-checkin / generate-prd / team-brief…）
- **6 个 Workers**：有写权限，实际产出和修改 `.md`
- **4 个 Read-only Verifiers**：只观察文件系统，对 worker 产出做独立验证，**不可写**

即 V-model：左侧下降是需求→实现（worker），右侧上升是验证→确认（verifier），两侧不同角色。

## 行业痛点 (Why)

Skill 生态爆发后的系统性失效模式：**self-grading**。

在知识管理、PRD、发布说明这类「没有编译器兜底」的任务上，Agent 写 → 自检 → 宣布完成，幻觉被直接写入长期记忆，再被后续检索反复放大，形成自我强化的污染循环。

## 旧范式 vs 新范式

- **旧做法**：单 Agent 读写 + 自检 + 自我宣布完成。质量靠模型自觉，记忆漂移靠人工偶尔审查。
- **新做法**：Worker/Verifier 角色在架构上分离，verifier 只读且不共享生成上下文；记忆条目带 `last_verified` + confidence，由 `memory-hygiene` 定期重验证。

## 生产力影响 (How)

提供了一个**可移植的架构模式**，而非锁定在某框架里的功能：

1. 验证与生成解耦 —— 任何 markdown-as-state 的 Agent 工作流（规格、知识库、发布流程）都能套用 worker/verifier 分离
2. 记忆带过期语义 —— `last_verified` 让「这条记忆还成立吗」可查询、可审计
3. 全状态可 diff —— 因为就是 Git 里的 `.md`，Agent 的每次写入都可 review、可回滚，没有不透明数据库

## 采用成本

低。`git clone` → 在 Claude Code / Cursor / Antigravity / Gemini CLI / Codex 里说 "Run onboarding"，约 2 分钟完成个性化。无数据库、无厂商锁定、无额外 key。也可 `npx skills add huytieu/COG-second-brain`。

## 采用案例

- 个人知识管理：braindump → url-dump → weekly-checkin 闭环，verifier 校验 daily-brief 的 7 日新鲜度
- 团队智能：team-brief 交叉引用 GitHub + Linear + Slack + PostHog，双向同步回 Linear
- PM 工作流：generate-prd 带 **approval gate**（发布到 Confluence/Notion 前必须过闸）

## 风险/局限

- **社区验证严重不足**：37 stars/day、无 HN 讨论、无外部独立项目引用 —— 概念虽好但尚未被市场筛选
- 43 skills 对单仓维护是重负担，作者自建 `validate-agent-surface.sh` 检测 manifest/文档/文件漂移，说明漂移已是实际问题
- 「verifier 只读」是约定而非强制（同进程、同文件权限下的 Agent 约束靠提示词），真正硬隔离需沙箱支持
- 单一作者项目，长期维护性存疑

## 核心线索

- GitHub：https://github.com/huytieu/COG-second-brain
- 首发来源：GitHub Python trending daily（2026-11-16）
- 发布时间：新项目（< 6 个月）
- 当前状态：试验中（概念验证阶段，社区未放量）
- 关联引用：受 Garry Tan 的 gstack / gbrain 启发
