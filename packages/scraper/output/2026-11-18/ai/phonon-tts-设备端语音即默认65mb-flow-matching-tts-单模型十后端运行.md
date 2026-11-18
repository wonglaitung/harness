# Phonon TTS — 设备端语音即默认（65MB flow-matching TTS + 单模型十后端运行时）

## 技术定义 (What)
Phonon 是 Gradium 开源权重、约 65MB / 75MB 两档的设备端 TTS，基于 **Pocket TTS 血统 + flow matching** 生成音频（与主流 TTS 的建模路线不同，这也是小模型能做到该音质的根本原因）。31m 英文版 Apache 2.0 可商用，40m 覆盖英/法/德/西/葡但为 CC BY-NC。100+ 内置音色，支持 voice cloning / voice design。关键工程配套：自研推理框架 **ptts** 单流上机、覆盖 10+ 后端（CPU：Intel/Arm/WASM；GPU：CUDA/Vulkan/Metal/WebGPU；NPU：Apple Core ML、Snapdragon），以及 Hugging Face Transformers v5.21 起作为 **modular model 集成——约 200 行只描述差异**，提供批量生成 + 全图 `torch.compile` 的 GPU 吞吐路线。

## 行业痛点 (Why)
语音 AI 默认走云：每句话都要往返服务器。结果是隐私外泄（你说的话离开设备）、离线不可用、首字延迟被网络吃掉。而「小到能装进设备」与「好听到能用」长期是二选一。

## 旧范式 vs 新范式
- **旧做法**：云端 TTS API：文本出设备、音频回设备；延迟由网络决定，断网即失能，语音内容不可避免经过第三方。为了音质必须用大模型，为了体积只能牺牲自然度。
- **新做法**：语音默认住在设备上：文本不出设备、无网可用、权重开放（31m Apache 2.0）。小模型 + flow matching 同时拿到体积与音质；同一个模型靠 ptts 的后端矩阵铺到手机、笔记本、单板机、浏览器标签页与 Apple Watch。Transformers 侧作为 modular model 只写 ~200 行差异，说明「血统复用」正在成为官方集成方式。

## 生产力影响 (How)
HF Open TTS Leaderboard 上（23 语言，按可懂度 WER / 速度 / 自然度评测）：德、西两语可懂度**第一**，所有评测语言均在前三，对手模型最多大它 100 倍；CPU streaming 首字延迟榜**第一**（31m 28ms、40m 38ms，对比 Pocket TTS 165ms，越低越好）。上线两周下载超 20 万并在 HF trending。可落地的场景：Apple Watch 断网逐步指导冲咖啡、iPhone 无信号计数报数、离线浏览器小恐龙游戏变成 Rex 主持的电台节目、单机游戏本地配音、逐页朗读。

## 采用成本
低门槛：`transformers>=5.21` 即可加载（`AutoProcessor` + `GradiumPhononTTSForConditionalGeneration`）；要极致端侧性能用 ptts（需按目标后端编译）。商用注意许可分档：31m 英文 Apache 2.0；40m 多语为 CC BY-NC，商用按用户数计价而非按合成量。仅覆盖 5 种语言，中文不在列。

## 核心线索
- GitHub：https://github.com/gradium-ai/xn-ptts
- 来源：https://huggingface.co/blog/phonon-tts
- 发布时间：2026-11-18
