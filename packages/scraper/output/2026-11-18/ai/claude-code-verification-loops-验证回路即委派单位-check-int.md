# Claude Code Verification Loops — 验证回路即委派单位 + Check Integrity（检查不可自改）

## 技术定义 (What)
Anthropic Claude Code 团队公开其内部工程范式：约 90% 的代码由 Claude 编写**并由 Claude 评审**，因此把「让 agent 用证据自我验证」当作核心基础设施。核心命题——**验证回路是委派规模的基本单位**：没有验证回路，你只能同时跑 1~2 个 Claude（因为要自己逐行检查）；有了它，可以并行跑几十到几百个。配套三个可命名的新构造：(1) **verify skill**（放在 `.claude/skills/verify`，让 agent 端到端启动/驱动/检查真实系统，用 CDP／模拟器／API harness）；(2) **39 项可靠性清单 + diff 可读的触发器**（每次只匹配 3~10 项，没人需要背历史事故）；(3) **Check Integrity（检查不可自改）**——「如果一项改动能修改评判它的那个检查，这个检查就是坏的」：Code Review 只读 base/默认分支的 `REVIEW.md`，永不读 PR 里的改动。

## 行业痛点 (Why)
Agent 大规模并行的瓶颈不是生成能力，而是**人类验证带宽**。人读不完每一个 diff，所以要么限制并发数，要么把未经验证的代码合进主干。同时，让 agent 自己写测试会带来「自证清白」问题：agent 可以顺手把测试改绿。

## 旧范式 vs 新范式
- **旧做法**：人类逐行 review；只写单元测试（快但可被「agent 与测试都不理解完整任务」同时骗过）；靠「堆更多 reviewer」提升评审质量；测试与规则和被评审的改动放在同一个可修改的位置。
- **新做法**：把验证当成**可请求、可执行的软件资产**来投资，而不是人的时间。测试类型按「难以欺骗」排序：E2E（最难伪造，能截图+说明哪一步失败）> property tests（fast-check/Hypothesis/proptest 生成上千输入，专打人和 agent 都想不到的边界）> differential tests（旧系统当 oracle，适用于大规模迁移）。验证结果回流为规则（hook 或 CLAUDE.md），使同类问题基本不再复发。评审与验证串行叠加、每轮带上前面轮的上下文与失败记录，「更便宜且找到更多」。失败 3 轮后人接手；代码 owner 自己写检查，检查拉人时必须说明理由。

## 生产力影响 (How)
内部实测：在结构化文件生成任务上，用独立的 grader 按 rubric 检查 Claude 的产出，比标准 prompting 回路**成功率最高提升 10 个百分点**，且在最难的任务上收益最大。更关键的是并发上限被打开——从「同时跑 1~2 个」到「几十到几百个」。这是把 agent 从「个人助手」推向「可管理的算力池」的组织级前提。

## 采用成本
必须先有一个能一条命令跑起来的 E2E 冒烟测试骨架（这是真投入）；`verify` skill 要持续迭代并压测到「rock solid」，因为它就是你的冒烟测试 harness。property/differential 测试需要按项目写不变式与 oracle，迁移场景还需归一化无关差异并维护「已批准变更」白名单。规则本身要挂在改动改不到的分支上，需要一点仓库权限设计。

## 核心线索
- GitHub：
- 来源：https://claude.dev/blog/how-the-claude-code-team-thinks-about-verification/
- 发布时间：2026-11-18
