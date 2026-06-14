# Holo3.1

## 技术定义 (What)
首个专门针对跨环境（桌面、移动、Web）的 Computer Use 模型家族，支持本地化部署和量化推理，实现 GUI 自动化操作的新范式。

## 行业痛点 (Why)
现有的 Computer Use 模型在跨环境部署时性能不稳定，且无法在本地设备上运行，限制了隐私保护和成本控制。

## 旧范式 vs 新范式
- **旧做法**：使用云端模型处理 GUI 操作，依赖单一环境（浏览器或桌面），无法支持移动端，部署成本高且存在隐私风险。
- **新做法**：单一模型家族支持跨所有 GUI 环境（Web、桌面、移动），提供 FP8/NVFP4/Q4 GGUF 量化版本，可在消费级硬件本地运行，实现完全私密的 Agent 操作。

## 生产力影响 (How)
开发者可在本地部署 GUI 自动化 Agent，降低 70% 以上推理成本，保护用户隐私，NVFP4 量化提供 1.74x 吞吐量提升。

## 采用成本
免费开源模型，支持 vLLM 和 llama.cpp，需要消费级 GPU（如 RTX 5080）即可本地运行 35B 模型。

## 核心线索
- GitHub：https://huggingface.co/collections/Hcompany/holo31
- 来源：https://huggingface.co/blog/Hcompany/holo31
- 发布时间：2026-06-14
