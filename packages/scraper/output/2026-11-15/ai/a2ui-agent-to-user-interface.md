# A2UI (Agent-to-User Interface)

## 技术定义 (What)
A2UI 是一个开源的生成式 UI 协议 + 框架：Agent 不再只能返回文字或可执行代码，而是用受 schema 约束的数据（JSON）描述界面，由宿主 App 的原生渲染器（React / Flutter / SwiftUI / Jetpack Compose）流式渲染成真实原生组件。核心构成是「一个协议 + 各语言 Agent SDK + 组件目录（catalog）+ 原生框架适配器」，Agent 通过组合受信组件来表达 UI，因此可以在严格能力边界内跨平台、低延迟地生成界面。

## 行业痛点 (Why)
生成式 UI 的两难：让 LLM 直接吐 HTML/JS 或 React 代码，性能差、跨端不一致，且等于把可执行代码的执行权交给模型（提示注入即可越界操作）；而固定表单/固定页面则无法针对用户当下需求动态组织流程。同时多端（Web/iOS/Android/Flutter）Agent 需要重复实现同一套 UI 逻辑。

## 旧范式 vs 新范式
- **旧做法**：Agent 输出纯文本（用户自己在多级页面里找路径）或输出可执行前端代码 / 在 WebView 里塞 HTML；UI 由产品经理预先硬编码，Agent 只能填内容不能改结构。信任边界靠"事后审查代码"来兜。
- **新做法**：UI-as-Data：Agent 生成的是经过 schema 校验的界面描述，渲染在宿主框架的原生组件上。能力边界由 schema + catalog 在协议层强制（Agent 无法调用未被授权的组件或接触敏感字段），支持远程渲染、流式渐进渲染、同一份流同时适配多端。相当于给 Agent 一门"界面专用词汇"，而不是给它一台计算机。

## 生产力影响 (How)
1) 前端从"写页面"转为"维护组件 catalog + schema"，页面结构交给 Agent 现场组合，长尾流程的开发成本大幅下降；2) 因为是原生渲染而非 WebView/HTML，交互延迟和视觉保真度接近手写界面；3) 多端一致性从"三端各写一遍"变为"一次协议流，多端渲染"；4) 安全上把"防幻觉越权"从提示词工程变成协议级约束，第三方/远程 Agent 可被安全接入。

## 采用成本
中等偏低。接入需选定宿主框架的原生适配器、定义自己的组件 catalog 与数据 schema、在服务端或客户端跑 Agent SDK；已有 A2UI Composer 可在浏览器里直接试。学习成本主要来自 schema/catalog 设计，而非协议本身。开源 + 协议已发布 v1.0 规范。

## 核心线索
- GitHub：https://github.com/a2ui-project/a2ui
- 来源：https://github.com/a2ui-project/a2ui
- 发布时间：2026-11-15
