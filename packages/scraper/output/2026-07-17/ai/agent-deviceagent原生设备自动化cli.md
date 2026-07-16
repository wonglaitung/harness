# agent-device：Agent原生设备自动化CLI — 移动端验证新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个Agent原生跨平台设备自动化CLI——将iOS/Android/TV/桌面应用验证纳入Agent工作流，语义引用(@e1/@e2)替代坐标点击，可录制回放脚本 |
| 采用广度 | ☆☆☆/5 | Callstack（React Native核心团队）出品；Expo EAS集成；MCP服务器支持；但刚发布，生态早期 |
| 时间新鲜 | ☆☆☆☆/5 | 2026年7月发布，GitHub TypeScript trending |
| 社区热度 | ☆☆☆/5 | GitHub trending；Expo官方博客推荐；Callstack社区影响力 |
| **总体判断** | ✅ | **新范式 — Agent从浏览器走向真实设备验证** |

## 技术定义 (What)
agent-device是Callstack发布的开源设备自动化CLI，让AI编码Agent能够直接在iOS模拟器、Android模拟器、物理设备、tvOS、桌面应用上打开应用、检查UI、交互操作、收集调试证据。它提供token高效的accessibility快照、语义引用（如@e1、@e2）和结构化交互，而非截图+坐标点击的原始方式。

## 行业痛点 (Why)
当前AI编码Agent（Claude Code、Codex、Cursor等）只能验证Web应用，无法验证移动端和桌面端应用的实际运行效果。开发者修改移动代码后，必须手动在设备上测试——Agent的"写代码-验证"闭环在移动端断裂。现有移动测试工具（Appium、Maestro）面向人类QA，不是Agent友好的接口。

## 旧范式 vs 新范式
- **旧做法**：Agent只能通过浏览器验证Web应用；移动端需人工测试，或使用Appium等重量级框架编写脚本；截图+坐标点击方式脆弱且token浪费
- **新做法**：Agent通过单一CLI直接操控真实设备，获取accessibility树快照和语义引用，token高效地验证移动应用行为；可录制.ad脚本供CI回放

## 生产力影响 (How)
- Agent编码闭环从Web扩展到移动端：写代码→设备验证→修复，全自动化
- 语义引用(@e1)比坐标点击更稳定，减少Agent误操作
- 录制回放功能将探索性测试转化为CI可重复检查
- 跨平台统一接口：一套Agent工作流覆盖iOS/Android/Web/TV/桌面

## 采用成本
- 安装：`npm install -g agent-device@latest`
- 前置依赖：Node.js 22+、Xcode（iOS）、Android SDK（Android）
- 学习曲线：低——CLI命令直观（open/snapshot/fill/screenshot/close）
- MCP集成：支持作为MCP服务器供Agent调用

## 采用案例
- **Expo EAS Workflows**：集成agent-device实现AI QA Agent自动验证移动应用
- **Vercel Eve**：使用agent-device构建移动QA Agent
- **Codex + agent-device**：AI编码Agent在iOS Contacts应用中自动创建联系人

## 风险/局限
- 依赖平台特定工具（Xcode/Android SDK），配置门槛存在
- 物理设备自动化需要macOS Accessibility权限
- Web平台支持复用agent-browser，功能相对有限
- 目前仅CLI接口，无GUI控制台

## 核心线索
- GitHub：https://github.com/callstack/agent-device
- 首发来源：Callstack官方博客 + GitHub TypeScript Trending
- 发布时间：2026年7月
- 当前状态：活跃开发中（v0.x快速迭代）