# Quantization-Aware Healing (QAH)

## 技术定义 (What)
QAH（Quantization-Aware Healing）是一种新的模型压缩恢复方法。核心创新：绕过结构压缩后的已退化 bfloat16 checkpoint，直接从原始未压缩模型向 4-bit 学生模型进行知识蒸馏。这意味着 4-bit 学生模型直接从源头学习，而非从中间退化版本修复。结果：在 GPT-OSS 120B→60B→MXFP4 压缩流程中，4-bit 模型在 9 个基准中的 7 个上击败了自身的全精度（bfloat16）版本，同时权重内存减少约 4 倍。

## 行业痛点 (Why)
当前模型部署标准流程：结构压缩→量化→修复（healing）。主流修复方法 QAT（量化感知训练）成本高、不稳定，会崩溃超过峰值；QAD（量化感知蒸馏）受限于只能蒸馏自身退化 checkpoint，存在精度天花板。行业缺少一种同时处理结构压缩+量化的统一高效修复方法。

## 旧范式 vs 新范式
- **旧做法**：QAT：在量化后的前向传播中重新运行 SFT/RLHF 等多阶段训练，成本高且不稳定。QAD：从已退化的 bfloat16 checkpoint 蒸馏，精度受其天花板限制。
- **新做法**：QAH：直接从原始未压缩大模型向 4-bit 小模型蒸馏，绕过中间退化 checkpoint。KL 散度 loss 天然稳定（目标固定不漂移），收敛速度约为 QAT 的 7 倍且持续训练不崩溃。重定义了量化阶段——不再是损失性后处理，而是第二轮完整的知识蒸馏。

## 生产力影响 (How)
部署成本大幅降低：权重内存减少约 4 倍、推理更快、精度反而更高。无需多周超参搜索，可用较小数据集完成。开源权重 Hypernova-60B 直接可用。

## 采用成本
低。只需高质量公共数据 + 任务特定数据集（无需原始训练语料）。兼容现有推理栈。论文提供了可复现的完整 recipe。

## 核心线索
- GitHub：https://huggingface.co/papers/2608.20953
- 来源：https://huggingface.co/blog/MultiverseComputingCAI/quantization-aware-healing
- 发布时间：2026-08-26
