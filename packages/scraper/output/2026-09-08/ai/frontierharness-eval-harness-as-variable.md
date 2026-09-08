# FrontierHarness Eval — Harness-as-Variable Agent 评测新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次将 harness（Agent 运行时框架）作为独立变量进行对照评测 |
| 采用广度 | ☆☆☆/5 | 已评测 12 种 harness 配置 + 360 次试验 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年9月首次公开发布 |
| 社区热度 | ☆☆☆/5 | Show HN 82 points；独立 benchmark 网站 |
| **总体判断** | ✅ | **新范式：Harness-as-Variable Eval Methodology** |

## 技术定义 (What)
FrontierHarness 将 Agent 评测的变量从「模型」扩展到「harness（运行时框架）」：同一模型（Kimi K3）+ 同一任务 + 同一环境 → 不同 harness 的 pass rate 从 50.0% 到 66.7%，成本从 $1.05 到 $18.34/任务。首次证明「用什么 harness」和「用什么模型」同等重要。

## 行业痛点 (Why)
当前 Agent 评测将所有变量混在一起（模型 + harness + prompt），无法区分是模型不行还是 harness 不行。FrontierHarness 通过「golden checkpoint + fresh restore」方法学，首次隔离出 harness 的独立贡献。

## 旧范式 vs 新范式
- **旧做法**：SWE-bench 只测「模型 X + 默认 harness」，混淆变量
- **新做法**：同一模型 X 在所有主流 harness 上跑相同任务，harness 成为独立评测维度

## 生产力影响 (How)
- 开发者选 harness 有数据支撑：Codex(66.7%, $3.47) vs Claude Code(63.3%, $18.34)
- 发现关键洞察：缓存命中率 ≠ 节省成本，OpenCode 失败成本隐藏，Claude Code 质量高但贵 6 倍
- 12 个 harness 的对照数据驱动「Agent infra」决策

## 采用成本
零成本 — 公开结果可查阅。自行跑 benchmark 需 Runta 环境（提供 $100 试用额度）。

## 采用案例
- Runta 自身用它作为 Agent 运行时选型的决策依据
- Codex、Claude Code、Pi、Hermes、OpenCode、Kimi Code 等 12 个 harness 已参与

## 风险/局限
- 仅覆盖软件工程任务和终端场景
- v1.0 仅测试一个模型（Kimi K3），未来需多模型交叉
- 新鲜度风险：harness 版本迭代快，结果有效期短

## 核心线索
- 网站：https://frontierharness.org
- GitHub：https://github.com/frontier-harness-eval/eval
- 首发时间：2026年9月
- 当前状态：活跃