# Multi-Agent Autoformalization — DAG 驱动数学证明新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | DAG 分解 + Prove2Me 协作平台 + 多 Agent 并行证明，首次系统化自动形式化方法 |
| 采用广度 | ☆☆☆/5 | 已用于 FLT 和 Vinogradov 三素数定理；社区可能快速跟进 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-08-18 首次公开，距今不到 1 个月 |
| 社区热度 | ☆☆☆☆☆/5 | HN 741 points，Kevin Buzzard（FLT 形式化社区领导者）背书 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)

Anthropic 的研究团队用数十个 Claude Agent 协作，在 11 天内完成了费马大定理（FLT）的端到端计算机可检证明——这是 350 年历史上首次。Agents 通过 **Prove2Me** 平台协作，该平台维护了一个**有向无环图（DAG）** 来表示定理依赖关系。每个 Agent 从 DAG 中选择一个叶子节点（未证明的子定理），独立尝试证明，成功后更新图状态。最终，Claude 写出了 1300 万行 Lean 代码，证明 29,500 个中间定理。

关键创新点：
1. **DAG 驱动的任务分解** — 将 FLT 的 86 页蓝图自动拆分为可并行的子目标
2. **多 Agent 协作** — 数十个 Agent 通过 Prove2Me 同时工作，共享状态
3. **自然语言搜索** — 每个定理附带自然语言描述，Agent 可搜索和复用已有结果

## 行业痛点 (Why)

数学证明验证是"可扩展性瓶颈"：Andrew Wiles 的 FLT 原始证明 129 页，人类验证耗费数月。随着 AI 生成越来越多的"证明"，人类审稿人根本跟不上。传统形式化路径（如 Kevin Buzzard 领导的社区项目）预计需要数年时间完成 FLT 形式化——Claude 在 11 天内就完成了。

## 旧范式 vs 新范式

- **旧做法**：人类数学家手动将证明重写为 Lean 代码，逐行翻译，速度极慢。FLT 形式化社区项目预计数年。审稿依赖人类逐行阅读。
- **新做法**：DAG 自动将证明分解为子目标 → 多 Agent 并行证明 → Prove2Me 自动跟踪依赖和状态 → Lean 编译器自动验证正确性。整个过程几乎不需要人类参与。

## 生产力影响 (How)

1. **数学审稿自动化**：未来每个数学论文都可以附带计算机可检证明，大幅降低审稿负担
2. **AI 证明的可信度**：AI 生成新定理时可以同步生成形式化证明，自我验证
3. **消费者级可及性**：研究者用 3 个 Claude Max 计划（约 $600/月），3 天就完成了 Vinogradov 三素数定理的形式化
4. **证明复用**：生成的 29,500 个中间定理全部可用，为后续数学工作奠基

## 采用成本

- **时间**：小规模证明 3 天（3 个 Max 计划）；大项目 11 天 + 约 60 亿输出 token
- **金钱**：Claude Max 计划 × 3-10（取决于项目规模）
- **学习曲线**：需要对 Lean 证明助手有基本了解，但 Agent 可处理大部分细节
- **基础设施**：只需 Claude 订阅 + Prove2Me（开源平台）

## 采用案例

- **费马大定理（FLT）**：11 天，13M 行 Lean，29,500 定理，首个端到端计算机验证
- **Vinogradov 三素数定理**：3 天，3 个 Max 计划，验证该方法可规模化
- **Riemann Zeta 相关工作**：此前 Anthropic 已用 Claude 在黎曼猜想上取得进展

## 风险/局限

- **Token 消耗巨大**：FLT 项目消耗约 60 亿输出 token
- **依赖 Anthropic 基础设施**：当前方法依赖 Claude 能力，开源模型能否复现存疑
- **DAG 管理仍是挑战**：初期尝试因 Agent 失去状态跟踪而失败
- **不能替代人类理解**：形式化证明是"核对计算"而非"生成洞察"，不能取代人类数学家的创造性工作
- **仅限已形式化的数学基础**：证明依赖 Mathlib 的现有定理库

## 核心线索

- Anthropic 博客：[https://www.anthropic.com/research/formalizing-fermats-last-theorem](https://www.anthropic.com/research/formalizing-fermats-last-theorem)
- GitHub 证明仓库：[https://github.com/anthropics/fermats-last-theorem](https://github.com/anthropics/fermats-last-theorem)
- Prove2Me 平台：[https://prove2me.vercel.app](https://prove2me.vercel.app/)
- 发布时间：2026-08-18
- 当前状态：活跃（已完成，社区正在审查）