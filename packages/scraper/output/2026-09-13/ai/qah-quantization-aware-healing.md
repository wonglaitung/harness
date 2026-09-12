# QAH (Quantization-Aware Healing)

## 技术定义 (What)
QAH 是一种量化修复方法：将结构压缩+量化后的 4-bit 模型直接从原始的、未压缩的全精度 teacher 模型中蒸馏，而非从压缩恢复后的 bf16 checkpoint 蒸馏。这使得 4-bit 模型能够获得 bf16 checkpoint 在恢复阶段未能传递的信息，最终在 7/9 个基准上超越其自身的全精度版本。

## 行业痛点 (Why)
结构压缩+量化两步走的模型部署流程中，量化阶段的信息损失始终被视为不可逆。即使进行 healing，恢复质量也被压缩后 checkpoint 的天花板限制。QAH 打破了这一天花板。

## 旧范式 vs 新范式
- **旧做法**：传统 QAT（量化感知训练）：在压缩恢复后的 checkpoint 上插入伪量化算子继续微调，成本高且不稳定。传统 QAD（量化感知蒸馏）：从压缩恢复后的 bf16 checkpoint 蒸馏到量化模型，但 teacher 本身就是蒸馏过的近似，存在质量天花板。
- **新做法**：量化不再是模型发布后的损失性后处理步骤，而是对原始 teacher 的第二轮完整蒸馏。4-bit 模型可以超越其全精度源模型——颠覆了"量化必有损"的基本假设。

## 生产力影响 (How)
更小、更便宜、更准确的模型：对部署端是降本增效的质变。120B→60B 压缩+MXFP4 量化后的模型在数学、推理、编码等关键能力上超越 16-bit 版本，同时内存和计算需求大幅降低。

## 采用成本
需要 Fine-tune 基础设施（GPU 集群），但这是模型发布方的成本，终端用户零成本——下载更小的 4-bit 模型即可获得更高质量

## 核心线索
- GitHub：https://huggingface.co/papers/2608.20953
- 来源：https://huggingface.co/blog/MultiverseComputingCAI/quantization-aware-healing
- 发布时间：2026-09-13
