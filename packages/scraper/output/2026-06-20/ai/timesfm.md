# TimesFM

## 技术定义 (What)
TimesFM 是 Google Research 开发的时间序列基础模型，采用 decoder-only 架构，可在零样本或少样本情况下进行时间序列预测。当前版本 2.5 支持 16k 上下文、200M 参数、连续分位数预测，已集成到 BigQuery ML、Google Sheets、Vertex AI 等产品中。

## 行业痛点 (Why)
传统时间序列预测需要针对每个任务训练专门模型，数据需求大、迁移能力差。TimesFM 作为基础模型，可以在多种时间序列任务间迁移，无需从头训练。

## 旧范式 vs 新范式
- **旧做法**：为每个预测任务单独训练 ARIMA、Prophet 或 LSTM 模型，需要大量领域数据和调参工作。
- **新做法**：使用预训练的时间序列基础模型，通过零样本或少样本推理完成预测，支持 Agent 技能调用和微调。

## 生产力影响 (How)
降低时间序列预测门槛，非专家用户可通过 Google Sheets 或 BigQuery ML 直接使用。支持 LoRA 微调适应特定领域。

## 采用成本
低。可通过 PyPI 安装，支持 PyTorch 和 Flax 后端。提供 Agent 技能文档，可与 Claude/Codex 集成。

## 核心线索
- GitHub：https://github.com/google-research/timesfm
- 来源：https://github.com/google-research/timesfm
- 发布时间：2026-06-20
