# Browser Harness

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ⭐⭐⭐⭐/5 | "自愈 harness"概念：Agent 边用边写缺失的 helper，每次使用都让 harness 更强 |
| 采用广度 | ⭐⭐/5 | 刚发布，browser-use 生态项目 |
| 时间新鲜 | ⭐⭐⭐⭐/5 | 2026年8月首次出现在 GitHub Trending |
| 社区热度 | ⭐⭐⭐/5 | browser-use 项目已有广泛社区基础，harness 作为其新组件 |
| **总体判断** | ✅ | **新范式 — "自愈 harness"重新定义 Agent-浏览器交互模式** |

## 技术定义 (What)
Browser Harness 是一个自愈式 Agent-浏览器连接层。它通过一个可编辑的 CDP WebSocket 将 LLM 直接连接到真实浏览器。核心创新：Agent 在操作过程中遇到缺失的 helper 函数时会自己写出来，使 harness 随每次任务不断进化变强。

## 行业痛点 (Why)
传统 browser agent 依赖预设的固定工具集：如果网站结构变化或需要新的交互模式，agent 就"卡住了"。Browser Harness 打破了这个限制——agent 不再被预设工具束缚，而是可以在运行时扩展自己的能力。

## 旧范式 vs 新范式
- **旧做法**：Playwright/Puppeteer 固定 API，agent 只能调用预定义操作（click、type、wait），超出预设就失败
- **新做法**：Agent 直接操作 CDP WebSocket，缺什么 helper 就写什么 helper，harness 持续进化

## 生产力影响 (How)
- Agent 不需要开发者提前覆盖所有网站交互场景
- 同一个 harness 越用越强，适应各种网站
- 开发成本从"事前穷举"变为"运行时自适应"

## 采用成本
- 安装简单（pip install browser-harness）
- 需要 Chrome/Chromium 开启远程调试
- Python 3.12+，对开发者友好

## 风险/局限
- 依赖 CDP 协议，Firefox/Safari 兼容性有限
- Agent 生成的 helper 代码质量不确定
- 安全性：Agent 获得了浏览器完全控制权

## 核心线索
- GitHub：https://github.com/browser-use/browser-harness
- 首发来源：GitHub Trending
- 发布时间：2026年8月
- HN 相关讨论链接：https://browser-use.com/posts/bitter-lesson-agent-harnesses
- 当前状态：活跃开发中