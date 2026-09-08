# Soup / Layer Streaming

## 技术定义 (What)
Soup 通过 Layer Streaming 技术，将冻结的基座模型权重「一层一层地流式送入 GPU」而非全部驻留在显存中，使得在 4GB 笔记本 GPU 上微调 8B 参数模型成为可能——实测 Llama-3.1-8B 仅需 3.32GB 峰值显存，输出与全量加载逐比特一致。

## 行业痛点 (Why)
LLM 微调长期被高端 GPU 垄断：即使使用 QLoRA，8B 模型也需 12-16GB 显存。这使独立开发者、学生和资源受限团队无法参与模型定制，阻碍了 AI 民主化。传统方案需要云 GPU（昂贵且复杂）或极度牺牲质量。

## 旧范式 vs 新范式
- **旧做法**：微调需要将整个基座模型加载到 GPU 显存（即使冻结），8B 模型需 12-16GB+，迫使开发者依赖云 GPU 或高端硬件。
- **新做法**：Layer Streaming：冻结的基座权重保留在 CPU RAM/磁盘，每次仅将 1 个 decoder layer 送入 GPU，与其 LoRA 适配器一起计算后立即释放。峰值显存降至 3.32GB，在消费级笔记本 GPU 上实现 119.6 tok/s 的训练速度。

## 生产力影响 (How)
让任何拥有游戏本的开发者都能微调 8B 模型，极大降低 AI 微调的门槛。配合 YAML 配置 + 自动批处理/量化/GPU 检测，将微调从「需要 DevOps 团队」变为「一条命令」。

## 采用成本
学习成本极低（pip install + YAML 配置）；硬件成本从 $2/hr 云 GPU 降至免费（自有机器的空闲时间）；时间成本也因无需 SSH 和集群配置而大幅下降。

## 核心线索
- GitHub：https://github.com/MakazhanAlpamys/Soup
- 来源：https://github.com/trending/python
- 发布时间：2026-09-08
