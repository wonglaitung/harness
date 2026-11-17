# Token Pooling-Aware Training — 部署期有损压缩感知训练

## 技术定义 (What)
在多向量检索（ColBERT 类）中，文档的每个 token 都存一个向量，百万文档即上亿向量。Token pooling 用 Ward 层次聚类把相似 token 向量合并成一个均值向量来压缩存储。关键在于：不再"训练完再压缩"（压缩必然掉点），而是在训练时就模拟 pooling 过程，让编码器学会把重要信息放进合并后仍能保留的位置。同样 4 倍压缩预算下，NanoBEIR nDCG@10 保留率从 94.6% 提升到 97.8%。

## 行业痛点 (Why)
嵌入模型的存储成本和精度长期是二选一：为了省存储做后处理压缩（量化、pooling、剪枝），精度必然掉，且掉多少只能事后测量，无法训练补偿。Multi-vector 检索尤其严重——4-bit 量化下 200 向量 × 128 维 = 每文档 12.8KB，百万文档 12.8GB。

## 旧范式 vs 新范式
- **旧做法**：训练 → 部署前压缩（量化/池化）→ 接受精度损失，或用蒸馏重训一个更小的模型。
- **新做法**：训练时就把目标压缩算子放进梯度路径：Loss wrapper 在 forward 中执行真实 pooling，编码器直接学习"抗压缩表示"。压缩预算成为超参而非事后妥协。同样的存储预算下，量化与 pooling 可叠加使用而非互相打折。

## 生产力影响 (How)
对 RAG/搜索团队，这是"用训练时间换存储成本"的直接杠杆：4 倍向量压缩几乎免费（保留 97.8% 质量），意味着同等预算可索引 4 倍语料。方法论可外推——凡是部署期有不可逆有损变换（量化、剪枝、降维、打分聚合），都值得把该变换搬进训练 loop，而不是在推理侧打补丁。

## 采用成本
低。Sentence Transformers 已内置 HierarchicalTokenPooling 与 loss wrapper，几十行代码即可复现；可选 kernel 加速。成本主要是重训一次编码器（不是从零预训练），以及为自己的语料校准 pooling 预算（固定 budget vs 按文档长度比例 vs 自适应）。

## 核心线索
- GitHub：https://github.com/lightonai/fast-plaid
- 来源：https://huggingface.co/blog/token-pooling
- 发布时间：2026-11-17
