# Soup — Layer Streaming：4GB 显存微调 8B 模型的新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | Layer Streaming（层流式显存管理）是明确的训练基础设施创新，有 DOI 论文 |
| 采用广度 | ☆☆☆/5 | 22 名外部贡献者、60 个 PR（v0.75），社区活跃 |
| 时间新鲜 | ☆☆☆☆/5 | 近期快速迭代（v0.72→v0.75） |
| 社区热度 | ☆☆☆/5 | GitHub trending python 单日 +104，Product Hunt 上榜 |
| **总体判断** | ⚠️→✅ | **新范式（观察中）** |

## 技术定义 (What)
开源 LLM 微调/后训练 CLI。核心是 Layer Streaming：冻结的基座模型不常驻显存，逐 decoder 层流入 GPU（仅 113MB VRAM 缓冲），Rm-3.1-8B+NF4 在 RTX 3050 4GB 上以 119.6 tok/s、3.32GB 峰值微调，且与常规运行 bit-exact 一致。

## 行业痛点 (Why)
微调基础设施耗掉团队 30-50% 时间；8B 模型微调需 16GB+ 显存，普通开发者被挡在门外。

## 旧范式 vs 新范式
- **旧做法**：基座整个常驻显存，需云 GPU、SSH、复杂配置，显存门槛高。
- **新做法**：Layer Streaming 逐层喂入，4GB 显存即可微调 8B；单一 YAML + 一条命令自动处理。

## 生产力影响 (How)
显存门槛降低约 4-6 倍，消费级硬件本地微调成为可能，显著缩短基础设施耗时。

## 采用成本
pipx 安装即用；Layer Streaming 为 BETA，参数 opt-in。

## 采用案例
- 官方验证：RTX 3050 Laptop 4GB 微调 Llama-3.1-8B，bit-exact；H100 上独立复现。
- 免费 Colab T4 notebook 可复现。

## 风险/局限
- Layer Streaming 属 BETA，宽架构与部分偏好损失场景需进一步验证；性能曾因正确性修复降 ~4.8%。

## 核心线索
- GitHub：https://github.com/MakazhanAlpamys/Soup
- 首发来源：https://github.com/MakazhanAlpamys/Soup
- 发布时间：近期（2026 Q3 活跃）
- 当前状态：活跃（早期）