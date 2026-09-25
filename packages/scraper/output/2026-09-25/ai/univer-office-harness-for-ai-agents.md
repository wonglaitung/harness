# Univer — Office Harness for AI Agents

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 引入"Office Harness for AI Agents"定位：办公文档从人类 GUI 工具转为 Agent 原生运行时（无头 + Worktree 协作） |
| 采用广度 | ☆☆☆☆/5 | 多个独立生态集成：DeepSeek Harness、WorkBuddy、OpenClaw、Univer Workspace；Trendshift 上榜 |
| 时间新鲜 | ☆☆/5 | 项目本身较成熟，但"Agent Harness"定位是近期重新确立的新范式 |
| 社区热度 | ☆☆☆/5 | GitHub 高星（长期积累），Trendshift badge，活跃维护 |
| **总体判断** | ⚠️ | **观察中——"文档操作台"范式成立，但底层 SDK 非新项目** |

## 技术定义 (What)
Univer 是一个插件化、Canvas 渲染、同构（isomorphic）的开源 Office SDK。核心是"同一套逻辑既在浏览器渲染 UI、又在 Node.js 无头运行"，配合统一 Facade API，使 AI Agent 能结构化地读写 spreadsheet/document/presentation/base/board/PDF 等办公内容。

## 行业痛点 (Why)
AI Agent 需要操作办公文档时，传统方案要么依赖 GUI 模拟（慢、脆），要么只能生成最终文件、无法读写中间态。缺乏一个"无头、可程序化编辑、可渲染验证、可分支协作"的文档运行时。

## 旧范式 vs 新范式
- **旧做法**：人类在 Office GUI 中编辑，Agent 只能产出最终文件；或截图模拟点击。
- **新做法**：Office 作为 Agent 原生 Harness——无头运行 + Facade API 程序化编辑 + 渲染验证 + Worktree 隔离分支，人机在同一文件上协作。

## 生产力影响 (How)
让 Agent 直接读写表格/文档，实现自动化报表、"决策仪表盘（指标绑定单元格）"、文档审阅与交付闭环。Node.js 无头运行使服务端工作流复用同一套 Office 逻辑。

## 采用成本
中低（Preset 快速模式 / Plugin 精确组合）；但实时编辑与 Worktree 协作需 Web SDK 与商业授权，许可需评估。

## 采用案例
- **DeepSeek Harness**：Office 插件，带内容校验与隔离 worktree
- **WorkBuddy**：本地 Office 集成，MCP 预览 + 草稿审阅
- **OpenClaw**：创建、审阅、交付 Office 内容

## 风险/局限
- 底层 SDK 非新项目（成熟积累），范式创新在于"Agent Harness"重新定位
- 协作能力商业授权，开放源码与 Pro 范围需区分
- "文档操作台"能否成为独立范式仍待观察

## 核心线索
- GitHub：https://github.com/dream-num/univer
- 官网：https://univer.ai/
- 当前状态：活跃