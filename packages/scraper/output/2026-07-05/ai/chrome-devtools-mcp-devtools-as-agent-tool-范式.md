# Chrome DevTools MCP

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个将浏览器DevTools作为AI Agent工具链的标准MCP服务器，引入"DevTools-as-Agent-Tool"概念，AI可自主进行性能分析、网络调试和UI自动化 |
| 采用广度 | ☆☆☆☆☆/5 | 支持10+主流AI编码平台（Antigravity、Claude Code、Codex、Cursor、Cline、Windsurf等），Google Chrome官方团队维护 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6-7月发布，GitHub Trending TypeScript 303⭐/day |
| 社区热度 | ☆☆☆☆/5 | GitHub Trending TypeScript榜首，单日303星，Chrome DevTools官方团队出品 |
| **总体判断** | ✅ | **新范式 — AI Agent从"写代码"到"调试运行时"的能力跃迁** |

## 技术定义 (What)
Chrome DevTools MCP 是一个 MCP 服务器，让 AI 编码助手（如 Claude Code、Codex、Cursor）能够控制和检查真实的 Chrome 浏览器实例。它通过 MCP 协议暴露 Chrome DevTools 的完整能力，包括性能追踪、网络请求分析、截图、控制台消息检查（含 source-mapped 堆栈跟踪），以及基于 Puppeteer 的可靠浏览器自动化。

## 行业痛点 (Why)
当前 AI 编码助手只能"写代码"，无法"调试运行时"。开发者需要手动切换到浏览器 DevTools 查看性能问题、网络请求和控制台错误，再将信息复制回 AI 工具——这个切换循环严重打断工作流，且 AI 无法自主发现和修复运行时问题。

## 旧范式 vs 新范式
- **旧做法**：AI 编码助手只能生成和编辑代码，开发者手动打开浏览器 DevTools 检查运行时问题，复制错误信息粘贴给 AI，形成低效的人工中继循环
- **新做法**：AI Agent 通过 MCP 直接操作浏览器 DevTools，自主完成性能分析、网络调试、UI自动化，实现从"代码生成"到"运行时验证"的闭环

## 生产力影响 (How)
1. **消除人工中继**：AI可直接查看浏览器状态，无需开发者手动复制粘贴错误信息
2. **自主性能优化**：AI 可录制性能追踪并提取可操作的优化建议
3. **可靠自动化**：基于 Puppeteer 的操作自动等待结果，比传统 CSS 选择器更稳定
4. **Source-mapped调试**：控制台错误直接映射回源码位置，AI可精确定位问题

## 采用成本
- 免费（开源），`npx chrome-devtools-mcp@latest` 一行命令安装
- 需要 Node.js LTS + Chrome 稳定版
- 自动集成已安装的 AI 编码工具
- 提供 `--slim` 模式用于基础浏览器任务

## 采用案例
- **Claude Code**：通过 Plugin 系统安装，AI 可直接调试前端问题
- **Codex**：通过 CLI 添加 MCP 服务器，AI 自主进行浏览器测试
- **Antigravity**：自动连接 Antigravity 内置浏览器
- **性能优化**：AI 录制 Chrome DevTools Performance Trace，自动分析瓶颈

## 风险/局限
- 仅支持 Google Chrome（其他 Chromium 浏览器不保证兼容）
- 默认收集使用统计数据（可通过 --no-usage-statistics 关闭）
- 暴露浏览器内容给 MCP 客户端，需注意敏感信息
- 性能工具可能发送追踪 URL 到 Google CrUX API

## 核心线索
- GitHub：https://github.com/ChromeDevTools/chrome-devtools-mcp
- 首发来源：GitHub Trending TypeScript
- 发布时间：2026年6-7月
- 当前状态：活跃开发，Google Chrome 官方团队维护