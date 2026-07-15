# BrowserOS/BrowserClaw：Agent原生浏览器新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首创"Agent原生浏览器"类别——浏览器本身即为Agent执行环境，非headless driver |
| 采用广度 | ☆☆☆/5 | GitHub trending 168星/天，新发布快速获关注 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月首次公开发布 |
| 社区热度 | ☆☆☆☆/5 | GitHub TypeScript trending #3，Show HN社区讨论活跃 |
| **总体判断** | ✅ | **新范式——Agent原生浏览器** |

## 技术定义 (What)
BrowserOS是开源Chromium分支，内置AI Agent于每个新标签页；BrowserClaw是同一代码库的"Agent驱动浏览器"——AI Agent（Claude Code、Codex、Cursor等）通过MCP协议直接操控用户已登录的浏览器会话。核心创新：浏览器不再是Agent的"远程控制目标"，而是Agent的原生运行环境。

## 行业痛点 (Why)
当前Agent浏览器操作面临三大困境：1）Playwright/browser-use等headless driver无登录态，无法完成"订机票""查邮箱"等真实任务；2）Browserbase等云浏览器将用户token经第三方服务器，隐私风险巨大；3）现有方案要么无身份（headless），要么不安全（cloud），无法兼顾。

## 旧范式 vs 新范式
- **旧做法**：Agent通过Playwright/Puppeteer启动无头浏览器子进程，无cookie无登录态，只能做爬虫级任务；或使用云浏览器服务，session token经第三方
- **新做法**：BrowserClaw就是用户日常浏览器，Agent直接使用用户已有的登录态操作；BrowserOS将Agent内嵌浏览器本身，53+浏览器工具+40+应用集成，一键MCP连接

## 生产力影响 (How)
开发者无需再为Agent构建复杂的浏览器自动化管道。一键将Claude Code/Codex连接到BrowserClaw，Agent即可操作用户已登录的Gmail、Slack、GitHub等。会话可回放如视频，审计追踪完整。从"Agent无法登录"到"Agent用你的账号工作"，生产力跃升一个量级。

## 采用成本
- 时间：下载安装5分钟，一键MCP连接
- 金钱：完全免费开源（AGPL-3.0），自带AI key
- 学习曲线：极低——安装浏览器+连接AI工具，无需编程

## 采用案例
- Claude Code + BrowserClaw：Agent直接操作用户已登录的网站完成真实任务
- BrowserOS内置Agent：新标签页直接用自然语言指令操作浏览器
- MCP集成：任何MCP兼容AI工具均可一键连接

## 风险/局限
- AGPL-3.0许可证对商业使用有限制
- 仅支持macOS/Windows，Linux支持有限
- 依赖用户本地运行，不适合大规模并行Agent部署
- 安全性依赖本地隔离，多Agent并发操作同一浏览器可能冲突

## 核心线索
- GitHub：https://github.com/browseros-ai/BrowserOS
- 首发来源：GitHub Trending + Show HN
- 发布时间：2026年7月
- 当前状态：活跃开发中，快速迭代