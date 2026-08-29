# Quantization-Aware Healing (QAH)

## 技术定义 (What)
QAH 是一种全新的模型压缩恢复范式：在结构压缩+量化之后，直接从原始大模型（而非恢复后的中间checkpoint）进行知识蒸馏。教师模型（120B BF16）和学生模型（60B MXFP4）架构完全不同，通过KL散度在logits层传递知识，使4-bit量化模型的基准测试超过其16-bit全精度对应版本。

## 行业痛点 (Why)
传统压缩流程（结构压缩→量化→QAT/QAD恢复）存在根本天花板：量化恢复只能"修补"到中间恢复checkpoint的水平，无法超越。QAT成本高昂且不稳定，QAD在结构压缩后缺乏真正的全精度教师模型。

## 旧范式 vs 新范式
- **旧做法**：旧范式：压缩后的模型通过QAT（量化感知训练，重跑整个post-training）或QAD（量化感知蒸馏，从恢复后的BF16 checkpoint蒸馏）。结果：4-bit模型性能永远 ≤ 恢复后的BF16版本。
- **新做法**：新范式：QAH绕过中间checkpoint，直接从原始120B教师模型向60B MXFP4学生模型蒸馏。结果：4-bit模型在7/9基准上超越BF16版本（AIME 2025 +5.6, AA-LCR +7.4），颠覆了"量化=精度损失"的基本假设。

## 生产力影响 (How)
直接经济价值：同样硬件运行更小、更快、更准的模型。对部署团队意味着：可以用4-bit模型替代BF16模型，省一半显存和带宽，同时获得更高精度。长期影响：重新定义模型部署的效率天花板。

## 采用成本
需要原始模型权重（作为教师）+ 预计算logits的存储。技术上使用chunked KL-divergence loss适配32k长上下文。适用于有原始大模型访问权且需要压缩部署的团队。

## 核心线索
- GitHub：https://huggingface.co/papers/2608.20953
- 来源：https://huggingface.co/blog/MultiverseComputingCAI/quantization-aware-healing
- 发布时间：2026-08-29
