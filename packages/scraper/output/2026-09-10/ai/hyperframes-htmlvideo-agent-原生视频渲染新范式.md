# HyperFrames — HTML→Video Agent 原生视频渲染新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | HTML/CSS 声明式视频渲染 + 20 个 Agent Skills 工作流 |
| 采用广度 | ☆☆☆☆/5 | HeyGen 官方开源，TypeScript trending，npm 快速采用 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-09 首发，npm 持续更新 |
| 社区热度 | ☆☆☆☆/5 | GitHub 快速涨星，Discord 社区活跃 |
| **总体判断** | ✅ | **新范式 — Agent 原生视频创作引擎** |

## 技术定义 (What)

HyperFrames 是 HeyGen 开源的 Agent 原生视频渲染框架：用 HTML/CSS 编写内容 + seekable 动画声明 → 确定性 MP4 输出。内置 20 个 Agent Skills（产品发布视频、无脸解说、PR→视频、幻灯片等），支持 Claude Code、Cursor、Gemini CLI、Codex 等平台。

## 行业痛点 (Why)

视频创作需要专业工具（AE/Premiere），Agent 无法直接操作。传统方案：Agent 生成脚本 → 人工制视频。Agent 原生视频创作一直缺失。

## 旧范式 vs 新范式
- **旧做法**：Agent 只能生成视频脚本/文案，视频制作需人类介入专业工具
- **新做法**：Agent 直接编写 HTML → 声明动画 → 渲染 MP4，全自动闭环

## 生产力影响 (How)

- Agent 从"生成脚本"升级为"直接出视频"，缩短创意到成品周期
- 20 个开箱即用的 Skills 覆盖主流视频场景
- 声明式动画模型（GSAP/CSS/WAAPI/Three.js）统一为 HTML 属性

## 采用成本
- `npx skills add heygen-com/hyperframes` 一键安装
- 需要 Node.js >= 22
- 学习曲线：需理解 HTML/CSS 动画 + HyperFrames 的 `data-*` 时序属性

## 风险/局限
- HTML→视频渲染质量受浏览器引擎限制
- 复杂 3D/特效场景不如专业工具
- 依赖 Agent 的 HTML/CSS 编码能力

## 核心线索
- GitHub：https://github.com/heygen-com/hyperframes
- 首发来源：HeyGen 官方开源（2026-09）
- 发布时间：2026-09
- 当前状态：活跃（Apache 2.0）
- Discord：活跃社区