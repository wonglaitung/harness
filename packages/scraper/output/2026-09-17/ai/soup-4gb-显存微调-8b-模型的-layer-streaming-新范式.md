# Soup — Layer Streaming 微调

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | Layer Streaming 技术有 DOI 论文（zenodo 21771064）|
| 采用广度 | ☆☆☆/5 | 22 名贡献者，PyPI 可下载 |
| 时间新鲜 | ☆☆☆☆/5 | 快速迭代中（v0.72→v0.73）|
| 社区热度 | ☆☆☆☆/5 | trending +104、Product Hunt 上榜 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
Layer Streaming 把冻结基础模型移出显存，逐层流式送入 GPU，实现 4GB 笔记本 GPU 微调 8B 模型。RTX 3050 4GB 上 119.6 tok/s、3.32GB 峰值，bit-exact。

## 行业痛点 (Why)
LLM 微调需要高端 GPU + 复杂分布式配置，个人开发者被挡在门外。

## 旧范式 vs 新范式
- **旧做法**：A100/H100 + DeepSpeed/FSDP + SSH 集群
- **新做法**：一条命令 `soup train`，单 YAML，Layer Streaming 在 4GB GPU 微调 8B

## 生产力影响 (How)
微调门槛降至消费级硬件，推动模型定制民主化，个人也能做后训练。

## 采用成本
极低——pip install + one command，无需集群经验。

## 风险/局限
- 训练速度受吞吐影响，且新版有 -4.8% 速度回退
- 适合微调/后训练，不替代大规模预训练
- 大模型（>32B）效率待进一步验证

## 核心线索
- GitHub：https://github.com/MakazhanAlpamys/Soup
- DOI：10.5281/zenodo.21771064
- 当前状态：活跃（快速迭代）
- Website：https://trysoup.dev