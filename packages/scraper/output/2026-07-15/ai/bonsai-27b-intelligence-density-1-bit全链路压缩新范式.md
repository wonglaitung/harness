# Bonsai 27B：Intelligence Density 新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次提出"Intelligence Density"（每GB智能量）指标；1-bit/ternary权重全链路压缩（attention+MLP+embedding+LM head无高精度逃逸口） |
| 采用广度 | ☆☆☆/5 | Apache 2.0开源；支持MLX（Apple全生态）+ CUDA（NVIDIA）；已有Hermes Agent集成demo |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-07-14首发 |
| 社区热度 | ☆☆☆☆/5 | HN 332分；GitHub白皮书发布 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
Bonsai 27B是基于Qwen3.6 27B的1-bit/ternary全链路压缩模型，首次让27B级推理+工具调用+视觉+Agent能力在手机端运行。核心创新是"Intelligence Density"——每GB存储能承载的智能量，1-bit Bonsai 27B达到0.53/GB，是全精度基线的10倍以上。

## 行业痛点 (Why)
Agent工作负载需要数百步模型调用，云端API每步累积token成本且隐私数据必须出网。27B模型16-bit占54GB、4-bit占18GB，远超手机和大多数笔记本内存。本地部署Agent在能力与体积间存在结构性矛盾。

## 旧范式 vs 新范式
- **旧做法**：4-bit量化是压缩极限，27B模型仍需18GB+；Agent工作负载只能走云端API，每步付费+隐私外泄
- **新做法**：1-bit/ternary全链路压缩（无高精度逃逸口），27B能力压缩至3.9GB（1-bit）/5.9GB（ternary）；Agent可完全本地运行，边际成本为零，数据不出设备

## 生产力影响 (How)
- 开发者可在手机/笔记本部署27B级Agent，无需GPU服务器
- 混合部署架构成为可能：本地处理隐私敏感+非前沿任务，云端仅处理最难步骤
- 离线Agent、持久设备端Agent等全新产品类别解锁

## 采用成本
- 模型权重Apache 2.0免费
- 需要适配1-bit/ternary推理kernel（已提供MLX+CUDA实现）
- 1-bit版90%基线能力保留，ternary版95%保留——Agent工具调用能力下降约10-14%

## 采用案例
- **Hermes Agent**：Ternary Bonsai 27B在RTX 5090上运行端到端Agent工作流demo
- **iPhone 17 Pro**：1-bit Bonsai 27B在6GB可用内存内运行多模态Agent（demo模式）

## 风险/局限
- Agent工具调用（BFCL v3）1-bit版仅66% vs 基线80%，复杂Agent场景可能不够可靠
- 视觉能力1-bit版仅59.6% vs 基线72.6%，多模态场景受限
- 手机端demo模式使用缓存+预填充图像上下文，真实实时性能待验证
- 压缩方法架构无关但尚未在更大模型（如70B+）验证

## 核心线索
- GitHub：https://github.com/PrismML-Eng/Bonsai-demo
- 首发来源：https://prismml.com/news/bonsai-27b
- 发布时间：2026-07-14
- 当前状态：活跃（首发日）
- 白皮书：https://github.com/PrismML-Eng/Bonsai-demo/blob/main/bonsai-27b-whitepaper.pdf