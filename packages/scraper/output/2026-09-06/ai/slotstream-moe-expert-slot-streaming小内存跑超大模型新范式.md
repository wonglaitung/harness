# Slotstream — MoE Expert Slot Streaming：小内存跑超大模型新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次将 MoE Expert Slot Streaming 工程化落地：105GB 模型（125B 参数）在 48GB Mac 上以 ~12 tok/s 运行 |
| 采用广度 | ☆☆☆/5 | Show HN 237 分社区验证，已开放 API（Ollama/OpenAI 兼容），Sevra 应用基于此构建 |
| 时间新鲜 | ☆☆☆☆☆/5 | 首次发布 < 1 个月，Show HN 2026-09 上榜 |
| 社区热度 | ☆☆☆☆/5 | Show HN 237 points，HN 热搜，多个 Mac 型号实测数据已提交 |
| **总体判断** | ✅ | **新范式 — 消费级硬件运行超大模型的 Expert-Streaming 工程范式** |

## 技术定义 (What)

Slotstream 是一个 Swift 原生推理引擎，专为 Apple Silicon 设计。它将 125B 参数的 Qwen3.8-Flash-Next 模型（105GB 4-bit 权重）的大部分数据放在 SSD 上，**按需流式加载当前推理所需的 Expert 权重到内存**——类似于 MoE 模型的 Expert 调度，但在存储层实现。48GB M5 Pro 上做到 ~12 tok/s，支持本地离线推理。

## 行业痛点 (Why)

- **超大模型被硬件锁定**：125B+ 参数模型需要多张 H100/A100，消费级硬件（MacBook 48GB）无法运行
- **云端推理成本高+隐私风险**：API 调用有 token 费用、网络延迟、数据外泄风险
- **现有方案不足**：Ollama/llama.cpp 依赖全量加载到内存，无法突破物理 RAM 限制；传统 swap 方式速度极慢

## 旧范式 vs 新范式

- **旧做法**：买更大显存的 GPU / 用量化牺牲精度 / 用云端 API / 接受只能跑 7B-30B 模型
- **新做法**：Swift 二进制 + SSD Expert 流式加载，105GB 模型在 48GB Mac 上达到可用速度（12 tok/s），完全本地、离线、免费

## 生产力影响 (How)

- **Agent 本地化**：Coding agent 可通过兼容 API 直接使用 125B 级模型，无需联网
- **隐私场景**：医疗、法律、金融等敏感领域可本地跑大模型
- **降低门槛**：开发者无需采购昂贵 GPU，MacBook 即可跑超大模型实验
- **API 兼容**：Ollama/OpenAI 兼容，生态无缝接入

## 采用成本

- **时间**：模型首次下载 105GB（100Mbps 约 2.5h，仅一次），安装一行 curl 命令
- **金钱**：免费（Apache 2.0），需要 Apple Silicon Mac + 110GB SSD 空闲空间
- **学习曲线**：低，兼容 Ollama/OpenAI API 标准

## 采用案例

- **Sevra**：基于 Slotstream 构建的个人本地 AI 应用
- **fx (coding agent)**：通过 Vercel AI SDK gateway 协议集成
- **Open WebUI**：通过 Ollama 兼容 API 直接使用
- **社区实测**：48GB M5 Pro 12 tok/s，128GB M5 Max 更快，16GB M2 Mac mini 1.41 tok/s

## 风险/局限

- 仅支持 Apple Silicon Mac（macOS 14+）
- 长 prompt 预填充较慢（2000 token ~9s，8000 token ~39s）
- 目前仅支持一个模型（Qwen3.8-Flash-Next），生态待扩展
- Tool calling / JSON schema / logprobs 暂未完全支持
- SSD 频繁读写可能影响寿命（尚未有长期数据）

## 核心线索

- GitHub：https://github.com/carloslfu/slotstream
- Show HN：237 points
- 发布时间：2026-09（Show HN 上榜）
- 当前状态：活跃开发中
- 许可：Apache 2.0