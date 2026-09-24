# Strands Agents — Harness-as-a-Product

## 新范式评分
| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆/5 | "agent harness" 产品化 + model-driven，中等创新（框架类别） |
| 采用广度 | ☆☆/5 | 新发布，生态尚小 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026 新发布，当前 Trending |
| 社区热度 | ☆☆☆/5 | GitHub Trending，115 stars/day，多包已发 PyPI/npm |
| 总体判断 | ⚠️ | 观察中（强框架但概念创新中等） |

## 技术定义 (What)
`create_harness()` 一行得到带 benchmarked 默认值的可控 agent；模型无关、无托管控制面。

## 行业痛点 (Why)
手写 agent 循环成本高、框架绑定厂商、缺统一控制与可观测。

## 旧 vs 新
- 旧：手写 loop / 平台绑定框架，配置优先
- 新：harness 抽象 + 模型无关 + hook 全拦截 + benchmarked 默认

## 生产力影响
把 agent 循环从自研降到一行调用，默认可观测与 guardrail。

## 采用成本
中低，pip/npm 即用。

## 风险
框架赛道拥挤（与 LangChain 等重叠），差异化待验证。

## 核心线索
- GitHub：https://github.com/strands-agents/harness-sdk
- 发布：2026（Trending daily）
- 状态：活跃/早期