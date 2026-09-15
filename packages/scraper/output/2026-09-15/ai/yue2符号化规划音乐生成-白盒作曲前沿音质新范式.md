# YuE2：符号化规划音乐生成新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ★★★★★ | 首次将符号化作曲规划与神经音频生成统一到单一模型，白盒乐谱作为可控中间层 |
| 采用广度 | ★★★ | HKUST/MAP/Tokenwave/NYU/Stanford/MBZUAI 多机构合作，MERT2/SheetSage2配套生态 |
| 时间新鲜 | ★★★★★ | 2026年9月刚发布，GitHub trending 559⭐/天 |
| 社区热度 | ★★★★ | WildSongBench 公开基准，与 Suno v5/v6/Mureka 9 对标 |
| **总体判断** | ✅ | **新范式 — 开源音乐生成的"Stable Diffusion时刻"** |

## 技术定义 (What)
YuE2 是一个开源音乐生成系统，将符号化作曲规划（ABC记谱法）与神经音频合成统一到一个模型中：歌词+风格→乐谱计划→音频渲染。这实现了白盒可编辑的音乐生成。

## 行业痛点 (Why)
Suno/Udio等商业音乐生成是黑箱：输入prompt→输出音频，中间作曲过程不可见、不可编辑。音乐人无法干预旋律与和声。

## 旧范式 vs 新范式
- **旧做法**：端到端黑箱：歌词→音频，乐谱不可见
- **新做法**：符号-音频双层：先"作曲"（ABC乐谱）→再"演奏"（音频渲染），乐谱可检查、编辑

## 生产力影响 (How)
- 音乐创作者可精确控制AI生成的旋律与和声
- Agent可通过对话编辑音乐（"把和弦改成爵士"）
- 零样本翻唱：转录→保留旋律→换风格
- WildSongBench best-of-8: 6.9632 SongBench Avg，超越Suno v5/v6

## 采用成本
Linux + 24GB VRAM GPU + Python 3.12；开源Apache 2.0；提供Agent Skill集成

## 核心线索
- GitHub：https://github.com/multimodal-art-projection/YuE
- 演示页面：https://map-yue2.github.io/
- 发布时间：2026-09-14
- 当前状态：活跃开发中