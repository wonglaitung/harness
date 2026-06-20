# slime

## 技术定义 (What)
slime 是清华 THUDM 开发的 LLM 后训练框架，专注于 RL Scaling，通过 Megatron（训练）+ SGLang（推理）原生集成实现高效训练和灵活数据生成。支持 GLM、Qwen、DeepSeek、Llama 等系列模型的后训练。

## 行业痛点 (Why)
传统 RL 框架需要拼接多个系统（训练器、推理服务、Agent 框架），数据流复杂、调试困难、性能瓶颈多。slime 通过原生集成消除抽象层，保持数据流简洁。

## 旧范式 vs 新范式
- **旧做法**：使用多个独立工具组合（如 DeepSpeed + vLLM + LangChain），需要手动处理权重同步、数据缓冲、容错等问题。
- **新做法**：训练与推理原生集成，Megatron 参数和 SGLang 参数直接透传，支持 Delta 权重同步、PD 分离、外部推理引擎等高级特性。

## 生产力影响 (How)
已验证于 GLM-5.2、GLM-5.1、DeepSeek V3 等多个 SOTA 模型的后训练流程。支持数学、代码、搜索、工具、沙盒、验证器等多种数据生成工作流。

## 采用成本
中。需要熟悉 Megatron 和 SGLang，但文档完善，提供 CI、调试、追踪、性能分析等工程支持。

## 核心线索
- GitHub：https://github.com/THUDM/slime
- 来源：https://github.com/THUDM/slime
- 发布时间：2026-06-20
