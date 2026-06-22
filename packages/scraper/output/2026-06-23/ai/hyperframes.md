# HyperFrames

## 技术定义 (What)
HyperFrames 是开源的视频渲染框架，将 HTML、CSS、媒体和可寻址动画转换为确定性 MP4 视频。核心创新：**HTML-native video composition**（用 HTML 定义视频）、**Seekable animations**（可寻址动画引擎）、**Agent skills**（Agent 技能包）。Agent 写 HTML，框架渲染视频，同一输入始终产生相同输出。

## 行业痛点 (Why)
视频制作对开发者不友好：需要学习非线性编辑软件、时间线概念、关键帧动画。现有代码生成视频工具（如 Remotion）需手动编码动画逻辑，Agent 难以理解。缺乏针对 Agent 优化的设计系统。

## 旧范式 vs 新范式
- **旧做法**：使用 Adobe After Effects/Premiere 手动编辑，或使用 Remotion 等代码驱动工具编写 React 组件和动画逻辑。视频时间线与代码分离，难以迭代。
- **新做法**：HTML-to-Video：用 HTML 定义视频结构（`data-start`、`data-duration`、`data-track-index`），用 CSS/GSAP/Three.js 定义动画，用 FFmpeg 渲染。Agent 可直接操作熟悉的 HTML/CSS。提供 `frame.md` 设计系统模板，将 web 设计规范转换为视频适用格式。

## 生产力影响 (How)
让 Agent 用前端技能制作视频。适用于产品演示、PR 讲解、数据可视化、社交媒体视频。开发者在浏览器中预览，本地渲染，无需云服务。由 HeyGen（AI 视频领导者）开发，生产级质量。

## 采用成本
**时间成本**：安装简单（`npx hyperframes init`）。需 Node.js 22+ 和 FFmpeg。**金钱成本**：开源免费（Apache 2.0）。云渲染可选。**学习成本**：会 HTML/CSS 即可上手。提供设计模板（Biennale、BlockFrame、Blue Professional 等）。

## 核心线索
- GitHub：https://github.com/heygen-com/hyperframes
- 来源：https://github.com/trending/typescript
- 发布时间：2026-06-23
