# gzipt — Compression-as-Prediction 无训练语言模型

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 将"压缩-预测等价"（Language Modeling is Compression, 2023）反向落地为可运行生成器，beam search 解决量化噪声是新颖方法论 |
| 采用广度 | ☆☆/5 | 教学/探索性质，暂无生产采用，但方法论可迁移 |
| 时间新鲜 | ☆☆☆☆/5 | 2026-08 发布，纯新 |
| 社区热度 | ☆☆☆/5 | HN 369 分，广泛讨论 |
| **总体判断** | ⚠️ | **观察中（概念创新性强，但为玩具级）** |

## 技术定义 (What)
gzip(DEFLATE) 通过 32KiB 滑动窗口内的 back-reference 压缩。续写若回显窗口中已有文本则压缩极小。用 `score = len(gzip(context + candidate))` 打分，beam search 逐字节搜索最可压缩的续写。预热语料=窗口=隐式概率模型。

## 行业痛点 (Why)
揭示 LLM 的本质等价关系：预测即压缩。此前该等价只是理论（2023 论文尝试过但效果差），无人在 gzip 上做成真正能用的生成器。

## 旧范式 vs 新范式
- **旧做法**：神经网络权重建模概率，训练/微调成本高
- **新做法**：压缩器输出字节数即分数，零参数零训练生成

## 生产力影响 (How)
- 单文件纯 Python，教学价值极高
- 理解 LLM 本质的"最小可运行示例"
- 为训练-free 轻量生成器提供思路

## 采用成本
几乎为零：无 GPU、纯标准库 zlib、一条命令。

## 风险/局限
- 输出远不连贯（玩具级），无法替代真实 LLM
- DEFLATE 的 32KiB 窗口限制长程依赖
- 本质上性能上限极低，只有概念示范意义

## 核心线索
- GitHub: https://github.com/nathanrs/gzipt
- 首发: https://nathan.rs/posts/gzip-lm/ (2026-08-28)
- 关联论文: Language Modeling is Compression (arXiv:2309.10668)
- 状态: 试验中/教学