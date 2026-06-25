# peerd — 浏览器原生 Agent 运行时

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个浏览器原生Agent harness，无后端无云组件 |
| 采用广度 | ☆☆/5 | 极早期0.x，Show HN 67分 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月首次公开 |
| 社区热度 | ☆☆/5 | Show HN 67分，GitHub早期 |
| **总体判断** | ✅ | **新范式 — 浏览器即Agent运行时** |

## 技术定义 (What)
peerd 是首个完全运行在浏览器内的 AI Agent 运行时。作为 Chrome/Firefox 扩展，它直接在你已有的浏览器标签页和会话中运行完整的 Agent 循环——读取和驱动网页、启动沙箱计算（JS Notebook、编译为 WebAssembly 的完整 Linux VM）、通过 WebRTC P2P 网络实现 Agent 间通信。无需后端，无遥测，数据路径中无云组件。

## 行业痛点 (Why)
当前 AI Agent 要么需要云端后端（隐私风险），要么需要独立的桌面应用（割裂体验），要么需要 headless browser（无法复用用户已有会话和登录状态）。peerd 直接利用浏览器本身作为运行时和安全模型，复用用户已有的标签页、cookies、登录态。

## 旧范式 vs 新范式
- **旧做法**：Agent 需要云端服务器 + headless browser，或独立桌面应用（如 Claude Desktop）。用户必须在 Agent 环境中重新登录，数据经过第三方服务器。
- **新做法**：Agent 直接运行在用户的浏览器扩展中，复用已有标签页和会话。利用浏览器数十年硬化的安全模型（V8 隔离、WebCrypto、WebAuthn、opaque-origin iframe）。持有密钥的 Agent 永远不直接读取原始页面——一个无密钥无网络的 disposable runner 读取页面，输出以 untrusted 标记返回。

## 生产力影响 (How)
开发者可以在自己日常使用的浏览器中直接运行 Agent，无需配置任何后端基础设施。Agent 可以操作用户已登录的网页、在浏览器内运行沙箱代码、通过 P2P 与其他 Agent 通信。BYOK 模式，密钥加密存储在本地 vault。

## 采用成本
- 时间：5分钟安装扩展 + 配置 API key
- 金钱：免费开源（Apache 2.0），需自备模型 API key
- 学习曲线：中等——需要理解 Agent harness 概念和浏览器安全模型

## 采用案例
- 个人开发者：在浏览器中让 Agent 自动填写表单、操作 SaaS 工具
- 安全研究员：Agent 在隔离沙箱中分析可疑网页
- P2P Agent 通信：多个 peerd 实例通过 WebRTC 直接通信

## 风险/局限
- 0.x 实验阶段，API 可能随时变更
- 目前仅支持 Anthropic 和 OpenRouter 作为模型提供商
- 浏览器扩展的权限模型可能受限于平台政策
- P2P dweb 层仍为研究级

## 核心线索
- GitHub：https://github.com/NotASithLord/peerd
- 首发来源：Show HN
- 发布时间：2026年6月
- 当前状态：0.x 实验性 Beta