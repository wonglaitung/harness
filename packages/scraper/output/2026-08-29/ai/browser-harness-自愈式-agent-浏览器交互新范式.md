# Browser Harness — Self-Healing Agent-Browser Harness

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次提出"Agent 实时编写缺失 helper → harness 随使用进化"的自愈闭环，而非传统静态工具集 |
| 采用广度 | ☆☆☆/5 | 来自 browser-use 团队（成熟项目），支持 Claude Code、Codex、Cursor 等，MCP 协议兼容 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年8月 GitHub trending，全新发布 |
| 社区热度 | ☆☆☆☆/5 | GitHub trending Python daily，browser-use 生态积累 |
| **总体判断** | ✅ | **新范式 — 自愈式 Agent 浏览器交互** |

## 技术定义 (What)
Browser Harness 是一个"活的"浏览器自动化层：通过单一 CDP WebSocket 连接真实浏览器，Agent 在执行任务时实时检测工具缺失 → 自主编写 helper 函数 → 持久化到工作空间。每次任务都在"教"harness 新的交互能力。

## 行业痛点 (Why)
浏览器自动化面对无穷尽的网站和交互模式。传统工具集（Playwright 的 click/fill）永远是静态子集。新网站结构 = 新适配代码 = 人工维护成本。Agent 应该能够自己扩展自己的工具集。

## 旧范式 vs 新范式
- **旧做法**：开发者预先编写所有浏览器操作函数，Agent 仅做组合调用。遇到新场景报错 → 人工介入 → 写新函数 → 重新部署。
- **新做法**：Agent 检测缺失的 helper → 实时编写 → 持久化 → 下次自动可用。Harness 随使用进化，形成"越用越强"的正向飞轮。

## 生产力影响 (How)
- 消除浏览器自动化中 80% 的"适配型"人工工作
- 通过 MCP 协议接入 Claude Code/Cursor/Codex，作为 Agent 的"浏览器技能层"
- 结合 Browser Use Cloud 可扩展到并行浏览器集群

## 采用成本
- 极低：`pip install browser-harness` + 粘贴 setup prompt
- 需 Chrome 远程调试模式
- 开源免费

## 风险/局限
- 依赖 Agent 的代码生成质量（写的 helper 可能不稳定）
- 安全边界：Agent 自主写代码执行需要沙箱保护
- 仅在 Chrome 上测试

## 核心线索
- GitHub：https://github.com/browser-use/browser-harness
- 来源：GitHub Trending (Python daily)
- 发布时间：2026年8月
- 当前状态：活跃开发中
- 关联文章：《The Bitter Lesson of Agent Harnesses》《Web Agents That Actually Learn》