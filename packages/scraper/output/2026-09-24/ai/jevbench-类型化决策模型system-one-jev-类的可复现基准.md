# JevBench — Typed Decision Model Benchmark

## 新范式评分
| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆/5 | 针对新模型类别的密封集+多维门控评测，方法新但属评测工具 |
| 采用广度 | ☆☆/5 | 覆盖 77+ 系统（Jev、djev、GLiNER2 等） |
| 时间新鲜 | ☆☆☆☆☆/5 | v1.4.1 评分于 2026-09-23 |
| 社区热度 | ☆☆☆/5 | Show HN 139 points，多模型主动送评 |
| 总体判断 | ⚠️→✅ | 新范式支撑层（System One/Jev 范式的评测基础设施） |

## 技术定义 (What)
四轴评分（Intelligence/Calibration/Speed/Cost）harmonic mean；534 public + 308 sealed 决策；generalization gate 惩罚过度拟合。

## 行业痛点 (Why)
Jev 类类型化决策模型是新类别，缺防刷分、可复现、多维度的评测。

## 旧 vs 新
- 旧：传统公开题集基准，易饱和
- 新：密封集 + 泛化门控 + 成本/速度 Jev-class gate

## 生产力影响
为 System One/决策模型范式提供标准化评测，推动该类模型商业化与竞争。

## 采用成本
低（MIT 开源，可自运行）。

## 风险
单一评测方（Benchmark Heaven）；密封集黑箱依赖信任。

## 核心线索
- 站点：https://benchmarkheaven.com/jev-models
- 首发：v1.0 → v1.4.1（2026-09 评分）
- 状态：活跃/试验中