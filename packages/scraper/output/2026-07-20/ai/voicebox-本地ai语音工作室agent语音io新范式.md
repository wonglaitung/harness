# Voicebox

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个本地全栈语音工作室：7个TTS引擎+语音克隆+全局听写+MCP Agent语音输出，ElevenLabs+WisprFlow的本地替代 |
| 采用广度 | ☆☆☆/5 | macOS/Windows/Linux/Docker全平台，Tauri(Rust)原生性能，MCP集成Claude Code/Cursor/Cline |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月新发布，GitHub Trending 629 stars/day |
| 社区热度 | ☆☆☆☆/5 | GitHub Trending #1 TypeScript，629 stars/day，社区高度关注 |
| **总体判断** | ✅ | **新范式 — 本地AI语音工作室+Agent语音I/O** |

## 技术定义 (What)
本地优先的开源AI语音工作室，将语音输出（7个TTS引擎、语音克隆、23语言）和语音输入（全局听写热键、Whisper STT）统一到单一桌面应用中。核心创新是MCP服务器集成：任何MCP感知的AI Agent（Claude Code、Cursor、Cline）可通过一个工具调用`voicebox.speak`直接对用户说话，使用用户克隆的语音。内置本地LLM用于语音人格和文本润色。Tauri(Rust)构建，非Electron。

## 行业痛点 (Why)
当前语音AI工具链严重分裂：ElevenLabs只做TTS输出（云端付费），WisprFlow只做听写输入（云端付费），开发者需要拼接多个SDK才能实现完整语音交互。Agent无法"说话"——只能输出文本。语音克隆需要上传音频到云端，隐私风险高。

## 旧范式 vs 新范式
- **旧做法**：拼接ElevenLabs(TTS)+Whisper(STT)+云API，每个能力独立SDK，Agent只能输出文本，语音数据必须上传云端
- **新做法**：单一本地应用覆盖完整语音I/O栈，Agent通过MCP直接"说话"，语音克隆零样本本地完成，7个TTS引擎可切换

## 生产力影响 (How)
- Agent开发者：一个MCP工具调用让Agent获得语音输出能力，无需集成任何语音SDK
- 内容创作者：7个TTS引擎+情感标签+后处理效果，本地完成播客/有声书制作
- 隐私敏感场景：所有语音数据留在本地，零云端依赖

## 采用成本
- 免费（MIT开源）
- 需要GPU（macOS MLX/Windows CUDA/Linux ROCm）
- 学习曲线低：pip install或下载DMG/MSI，MCP配置几行JSON

## 采用案例
- Claude Code用户：Agent完成代码后通过voicebox.speak语音通知
- 播客制作：多轨道Stories编辑器+语音克隆+情感标签
- 无障碍：全局听写热键+自动粘贴，辅助输入

## 风险/局限
- Linux预构建二进制尚未提供，需从源码编译
- 7个TTS引擎质量参差不齐，Chatterbox Turbo仅支持英语
- 依赖本地GPU，无GPU时性能受限
- 相比ElevenLabs云端，超高质量语音克隆可能仍有差距

## 核心线索
- GitHub：https://github.com/jamiepine/voicebox
- 官网：https://voicebox.sh
- 文档：https://docs.voicebox.sh
- 发布时间：2026年7月
- 当前状态：活跃开发，Public Beta