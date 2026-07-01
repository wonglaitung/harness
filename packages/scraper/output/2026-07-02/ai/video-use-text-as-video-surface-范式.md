# video-use

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次提出"Text-as-Video-Surface"——LLM不观看视频，而是通过文本转录"阅读"视频，将视频编辑从视觉操作转为文本推理 |
| 采用广度 | ☆☆☆/5 | browser-use 团队出品，已被 Claude Code/Codex/Hermes 等多个 Agent 集成 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月首发，GitHub Trending 当日 690 stars |
| 社区热度 | ☆☆☆☆/5 | GitHub 日增 690 stars，browser-use 系列延续热度 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
video-use 是一个开源的 Agent 技能（Skill），让 LLM 通过文本转录而非帧序列来"阅读"和编辑视频。核心创新是双层感知架构：Layer 1 将音频转录为 ~12KB 的带时间戳文本（`takes_packed.md`），Layer 2 按需生成视觉合成图（filmstrip + waveform + word labels）。最终实现"Drop footage → Chat → Get final.mp4"的工作流。

## 行业痛点 (Why)
传统视频编辑需要专业软件和人工逐帧操作。即使有 AI 视频工具，也是预设模板驱动的。LLM 直接处理视频帧需要 45M+ tokens（30,000帧 × 1,500 tokens），既不经济也不精确。没有一个通用 Agent 能像编辑代码一样编辑视频。

## 旧范式 vs 新范式
- **旧做法**：视频编辑软件 + 人工操作时间线；或 AI 视频工具提供固定模板和菜单
- **新做法**：LLM 通过文本转录"阅读"视频内容，用自然语言描述编辑意图，Agent 自主执行剪辑、调色、字幕、动画等操作，并自评估输出质量

## 生产力影响 (How)
将视频编辑从"视觉操作"降维为"文本推理"，使任何会写 prompt 的人都能完成专业级视频编辑。一个命令行对话即可完成去口癖、调色、烧字幕、生成动画叠加等全流程。自评估循环确保输出质量。Session 记忆持久化支持跨会话连续工作。

## 采用成本
- 免费（开源），需 ElevenLabs API key（转录服务）
- 需安装 ffmpeg、uv/pip
- 学习曲线极低：只需会自然语言描述编辑意图
- 兼容 Claude Code、Codex、Hermes 等主流 Agent

## 采用案例
- **内容创作者**：Drop raw footage → "edit these into a launch video" → 获得 final.mp4
- **教程制作**：自动去口癖（umm, uh）、删除空白、烧字幕
- **多素材混剪**：Agent 自主制定编辑策略，并行生成动画叠加

## 风险/局限
- 依赖 ElevenLabs 转录服务（第三方 API）
- 复杂视觉特效仍需人工介入
- 当前主要面向英语内容，多语言支持待验证
- 自评估循环最多重试 3 次，极端情况可能遗漏问题

## 核心线索
- GitHub：https://github.com/browser-use/video-use
- 首发来源：GitHub Trending (Python)
- 发布时间：2026年6月
- 当前状态：活跃