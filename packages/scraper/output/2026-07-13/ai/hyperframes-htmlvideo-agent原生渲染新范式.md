# HyperFrames

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首个"HTML→Video"Agent原生渲染框架，引入frame.md设计系统、seekable animation、20个Agent skill模块 |
| 采用广度 | ☆☆☆/5 | HeyGen背书，GitHub 157 stars/day快速增长，npm可安装 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月开源发布 |
| 社区热度 | ☆☆☆☆/5 | GitHub TS trending #1 AI项目，HeyGen品牌效应 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
HyperFrames是一个开源框架，将HTML、CSS、媒体和可seek动画确定性渲染为MP4视频。核心理念是"Write HTML, Render Video, Built for Agents"——AI编码Agent通过skill描述视频需求，框架自动完成规划→HTML编写→动画布线→lint→预览→渲染的完整生产循环。

## 行业痛点 (Why)
当前AI生成视频依赖专有模型（Sora、Runway），存在三大问题：(1)不可编程——无法精确控制每一帧的布局、动画和时序；(2)不可复现——同一prompt产生不同结果；(3)Agent无法驱动——视频创作工具没有Agent可操作的编程接口。HyperFrames将视频创作从"黑箱生成"变为"确定性编程"。

## 旧范式 vs 新范式
- **旧做法**：用Premiere/After Effects手动剪辑，或用Sora/Runway等生成式模型从prompt生成视频——不可控、不可复现、Agent无法介入
- **新做法**：用HTML+CSS编写视频内容，用seekable animation定义时序，Agent通过skill驱动整个生产流程——确定性渲染、可编程、Agent原生

## 生产力影响 (How)
开发者可以用自然语言让AI Agent生成产品发布视频、PR演示、数据可视化动画等，无需视频编辑技能。20个skill模块覆盖从产品视频到音乐视频的全场景，frame.md设计系统确保品牌一致性。视频生产从"专业工具+人工"变为"Agent+代码"。

## 采用成本
免费开源(Apache 2.0)，需Node.js 22+和FFmpeg，学习曲线中等——需理解HTML→Video的composition模型和seekable animation概念，20个skill模块可按需加载降低入门门槛

## 采用案例
- Claude Code/Cursor/Gemini CLI/Codex：通过skill直接驱动视频创作
- 产品团队：从网站URL自动生成产品发布视频
- 开发团队：从GitHub PR自动生成变更演示视频

## 风险/局限
- 依赖FFmpeg和Node.js 22+，环境配置有一定门槛
- 当前仅支持HTML→MP4，不支持实时视频流
- 渲染质量受HTML/CSS能力边界限制，复杂3D效果需Three.js集成
- HeyGen商业利益驱动开源，长期维护策略待观察

## 核心线索
- GitHub：https://github.com/heygen-com/hyperframes
- 首发来源：GitHub TypeScript Trending
- 发布时间：2026年7月
- 当前状态：活跃开发中