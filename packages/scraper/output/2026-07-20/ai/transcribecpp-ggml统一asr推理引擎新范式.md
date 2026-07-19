# Transcribe.cpp

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个ggml统一ASR推理引擎，16模型家族60+变体，whisper.cpp的泛化替代 |
| 采用广度 | ☆☆/5 | v0.1.0刚发布，Mozilla AI赞助，Handy应用内置 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月首次发布v0.1.0 |
| 社区热度 | ☆☆☆☆☆/5 | HN 713分，社区高度认可 |
| **总体判断** | ✅ | **新范式 — ggml统一ASR推理层** |

## 技术定义 (What)
基于ggml运行时的C/C++语音识别推理库，将16个ASR模型家族（Whisper、Parakeet、Canary、Moonshine、Qwen3-ASR、Voxtral等60+变体）统一到单一GGUF格式推理引擎中。支持Metal/Vulkan/CUDA/tinyBLAS全平台GPU加速，每个模型均经过数值验证和WER测试确保与参考实现一致。提供Python/TypeScript/Rust/Swift四种官方绑定。

## 行业痛点 (Why)
当前本地ASR分发困境：只有whisper.cpp和ONNX两条路，ONNX仅CPU且性能差，MLX仅限Apple需维护双引擎。其他库作者不明、测试缺失、无绑定支持，本质是demo代码。跨平台应用需要可信任的、GPU加速的、可嵌入的ASR推理库。

## 旧范式 vs 新范式
- **旧做法**：每个ASR模型家族独立推理引擎（whisper.cpp只跑Whisper、NeMo只跑Parakeet），或用ONNX牺牲GPU性能，或为不同平台维护多套引擎
- **新做法**：ggml统一运行时 + GGUF模型格式，一个引擎跑16个ASR家族，GPU加速全平台覆盖，数值验证确保推理精度

## 生产力影响 (How)
- 开发者无需为不同ASR模型学习不同API和部署方式
- 一个库覆盖从34M参数Tiny到1.1B参数Parakeet全尺寸
- RK3566等嵌入式设备即可实时转录，数瓦功耗
- whisper.cpp近乎drop-in替换，迁移成本极低

## 采用成本
- 学习成本：低（API简洁，whisper.cpp用户可直接迁移）
- 部署成本：零（C/C++编译，无Python依赖）
- 迁移成本：极低（whisper.cpp兼容模式）

## 采用案例
- **Handy**：跨平台语音转文字应用，transcribe.cpp的诞生地
- **Mozilla AI BiR项目**：赞助支持，认可其本地推理分发价值

## 风险/局限
- v0.1.0阶段，部分whisper.cpp特性尚未支持
- 模型转换需NeMo环境，流程较复杂
- 社区生态尚在早期，第三方集成少

## 核心线索
- GitHub：https://github.com/handy-computer/transcribe.cpp
- 首发来源：HN (https://workshop.cjpais.com/projects/transcribe-cpp)
- 发布时间：2026年7月
- 当前状态：试验中（v0.1.0）