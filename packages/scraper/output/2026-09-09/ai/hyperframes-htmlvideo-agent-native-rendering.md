# HyperFrames — HTML→Video Agent-Native Rendering

## 技术定义 (What)
HyperFrames 是一个开源框架，让 AI Coding Agent 通过编写 HTML/CSS 代码来生成确定性 MP4 视频。核心创新在于将"视频渲染"变成 Agent 可编程的代码输出——Agent 写 HTML，框架将其编译为视频，完全不需要传统视频编辑软件。此范式可称为 "Text-as-Video-Surface"：Agent 的代码输出直接成为视频渲染面。

## 行业痛点 (Why)
传统视频制作需要专业软件（AE/PR）、时间线手动操作、渲染管线复杂。AI Agent 无法直接操作这些 GUI 工具生成视频。HyperFrames 让 Agent 用「写代码」这种它最擅长的方式生成视频——打破了 Agent 与视频创作之间的根本障碍。

## 旧范式 vs 新范式
- **旧做法**：传统做法：人类用 Premiere/After Effects 手动编辑时间线，或使用 RunwayML/Sora 等 AI 文生视频工具，输出不可精确控制。Agent 无法参与。
- **新做法**：新范式：Agent 编写 HTML+CSS+动画代码 → HyperFrames 确定性编译为 MP4。20 个 Agent Skill 提供完整制作管线。Agent 成为视频创作者。

## 生产力影响 (How)
视频生产民主化——产品发布视频、PR 变更日志视频、数据可视化动画、社交媒体内容等全部可由 Agent 自动生成。从「几天人工」变成「几分钟 Agent 运行」。

## 采用成本
学习成本低：HTML/CSS 是 Agent 的母语。npm 安装：`npx skills add heygen-com/hyperframes`。对开发者零门槛。

## 核心线索
- GitHub：https://github.com/heygen-com/hyperframes
- 来源：https://github.com/heygen-com/hyperframes
- 发布时间：2026-09-09
