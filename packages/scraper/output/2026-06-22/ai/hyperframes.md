# HyperFrames

## 技术定义 (What)
开源框架，将 HTML、CSS、媒体文件和可寻址动画转换为确定性 MP4 视频。用 Web 技术栈定义视频，通过 headless Chrome + FFmpeg 渲染，相同输入保证相同输出。

## 行业痛点 (Why)
视频渲染通常需要专业软件（After Effects、Premiere）或复杂的视频编辑 API。程序化视频生成缺乏标准化方法，难以集成到自动化流程中。

## 旧范式 vs 新范式
- **旧做法**：使用 GUI 视频编辑软件手动创建，或调用视频 API（如 Remotion）需要学习特定框架和 API
- **新做法**：用标准 HTML/CSS 定义视频内容，用 GSAP/CSS/Lottie/Three.js 定义动画，用 data-attributes 定义时间轴。Agent 可以直接用 Web 技能生成视频，无需学习专门的视频框架。

## 生产力影响 (How)
将视频生成从"专业工具"转变为"Web 技能"。开发者可以用熟悉的 HTML/CSS 技术栈生产视频，Agent 可以直接生成视频代码。支持无限长度、多轨道音频、字幕、特效等完整视频功能。

## 采用成本
需要 Node.js 22+、FFmpeg。提供 Agent Skills，Claude Code/Cursor/Codex 可直接使用。学习曲线：熟悉 Web 开发者约 30 分钟。

## 核心线索
- GitHub：https://github.com/heygen-com/hyperframes
- 来源：https://github.com/trending/typescript
- 发布时间：2026-06-22
