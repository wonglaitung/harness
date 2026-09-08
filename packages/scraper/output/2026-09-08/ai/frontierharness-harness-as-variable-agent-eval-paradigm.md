# FrontierHarness — Harness-as-Variable Agent 评测新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆ | "Harness-as-Variable"：将 Agent 执行框架（harness）从常量变为自变量，12 种配置同一模型同一任务对比 |
| 采用广度 | ☆☆☆ | 被 Runta 基础设施支持，12 个主流 harness（Codex, Claude Code, Pi, Kimi Code 等）参与评测 |
| 时间新鲜 | ☆☆☆☆☆ | v1.0 聚焦软件工程场景，2026 年 9 月发布 |
| 社区热度 | ☆☆☆ | Show HN 82 points，360 次独立试验，全冷启动环境 |
| **总体判断** | ✅ | **新范式 — Agent 评测从"换模型"进化为"换执行层"** |

## 技术定义 (What)

FrontierHarness 将 Agent 的 **Harness（执行框架）** 作为自变量进行评测，而不是把模型作为唯一变量。在同一模型（Kimi K3）、同一硬件环境（Runta 全冷启动）、同一任务集上，对比 12 种不同 harness 的 **质量、成本、速度**。核心洞察：**相同的模型 + 不同的 harness = 截然不同的结果**。

## 行业痛点 (Why)

当前 Agent 评测几乎都围绕"换模型"：GPT vs Claude vs Gemini。但实际生产中，**Codex DSH Creator ($3.28/task) 和 Claude Code ($18.34/task) 使用同一模型，成本差 5.6 倍**，通过率仅差 3%。评测社区长期忽视 harness 层的影响。

## 旧范式 vs 新范式

- **旧做法**：固定 harness，换模型做 benchmark。评测的结论是"模型 A 更好"
- **新做法**：固定模型，换 harness 做 benchmark。评测的结论是"同一模型下，harness X 以 1/17 的成本达到 harness Y 的效果"

## 生产力影响 (How)

1. **成本优化**：发现 Exo Harness $1.05/task vs Claude Code $18.34/task — 降本 94%
2. **选型决策**：企业可按"通过率/成本/速度"三维度选择最优 harness
3. **方法论革新**：360 次独立冷启动试验，消除缓存偏差，为 Agent 评测建立科学标准

## 采用成本

- 零成本查看结果：https://frontierharness.org/
- 自测 harness：Runta 提供 $100 免费额度
- 开源：https://github.com/frontier-harness-eval/eval

## 风险/局限

- v1.0 仅覆盖软件工程和终端任务，不涉及其他知识工作场景
- 仅使用 Kimi K3 单一模型，跨模型结论待验证
- 依赖 Runta 云环境，本地复现成本高

## 核心线索

- 网站：https://frontierharness.org/
- GitHub：https://github.com/frontier-harness-eval/eval
- 博客：https://runta.com/blog/introducing-frontierharness-eval
- 发布时间：2026 年 9 月
- 当前状态：活跃