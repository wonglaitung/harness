# @huggingface/kernels — WebGPU Kernel-as-a-Package

## 技术定义 (What)
@huggingface/kernels 是 Hugging Face 发布的 WebGPU 内核系统，将 207 个 GPU 操作（矩阵乘法、注意力、归一化等）打包为版本化的独立仓库——每个内核都附带 manifest.json、WGSL 着色器模板、正确性测试和基准用例。结合 Fleet 众包基准测试工具，在真机 GPU 上收集性能数据。

## 行业痛点 (Why)
浏览器端 AI 推理长期受限于两个问题：(1) WebGPU 内核跨设备性能差异极大，同一操作在不同 GPU 上可能差 1000 倍；(2) 内核没有标准化的版本、测试和分发机制，开发者只能自己写或复制粘贴着色器代码。现有 ONNX Runtime Web 的 WebGPU 后端性能参差不齐，且缺乏透明的正确性/性能验证。

## 旧范式 vs 新范式
- **旧做法**：开发者直接内联 WGSL 着色器字符串到应用代码中，或依赖 ONNX Runtime Web 的黑盒 WebGPU 后端。内核没有版本概念、没有独立测试、无法发现性能退化。
- **新做法**：每个 GPU 操作都是一个独立的、版本化的 HuggingFace Hub 仓库，包含标准化 manifest（合约）、测试用例、基准用例和参数化 WGSL 模板。@huggingface/kernels npm 包负责加载和运行。Fleet 浏览器工具众包真机 GPU 性能/正确性数据，形成开源基准数据库。

## 生产力影响 (How)
相比 ORT WebGPU 后端，在 Apple M4 上几何平均快 2.57 倍，中位数快 1.90 倍。极端情况（Einsum）可达 10,000+ 倍加速。为 Web 端 AI 推理（transformers.js、浏览器内 LLM）提供了可验证的底层基础。

## 采用成本
学习曲线低：npm install 即可使用，API 简洁（getKernel + 类型化数组调用）。需要 WebGPU 支持的浏览器。

## 核心线索
- GitHub：https://huggingface.co/webgpu-kernels
- 来源：https://huggingface.co/blog/webgpu-kernels
- 发布时间：2026-09-06
