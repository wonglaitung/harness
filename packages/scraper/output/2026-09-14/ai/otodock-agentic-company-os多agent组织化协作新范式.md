# OtoDock — Agentic Company OS

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次提出"Agent 部门+委派+会议+四种共享模式"的组织化 Agent OS 概念，定义了 Agent 六部分架构（Persona/Memory/Workspace/Knowledge/Skills/Tools） |
| 采用广度 | ☆☆/5 | 社区早期阶段，有社区 Agent、MCP、Skills 仓库 |
| 时间新鲜 | ☆☆☆☆☆/5 | Show HN 2026-09，版本 1.6.0，首发 < 3 个月 |
| 社区热度 | ☆☆/5 | Show HN 50 points，GitHub 早期 |
| **总体判断** | ✅ | **新范式** — Agent 组织化操作系统 |

## 技术定义 (What)
自托管的"Agent 公司 OS"。Agent 被组织为部门，可以互相委派、召开会议、自主运行。每个 Agent 有六个可编辑组件（Persona/Memory/Workspace/Knowledge/Skills/Tools），运行在内核沙箱中。

## 行业痛点 (Why)
现有 Agent 框架只解决"如何构建单个 Agent"，不解决"如何像运转公司一样运转一群 Agent"。

## 旧范式 vs 新范式
- **旧做法**：用 LangChain/AutoGen 等库以代码编排 Agent，缺乏组织级抽象
- **新做法**：Agent 按部门+角色+共享模式运行，内置委派、会议、调度、电话

## 生产力影响 (How)
中小企业一命令安装，即可拥有由 Agent 组成的数字团队，Agent 可编辑 Office 文档、定时执行任务、接打电话。

## 采用成本
Linux 服务器 + Docker，一行安装。使用 Claude Code/Codex 订阅。学习曲线中等。

## 采用案例
- 社区已贡献大量 Agent、MCP 工具、Skills
- Agent 本身被用于制作宣传视频

## 风险/局限
- 早期项目，生态尚小
- 依赖 Claude Code/Codex 订阅
- 安全模型依赖内核沙箱，需审计

## 核心线索
- GitHub：https://github.com/OtoDock/oto-dock
- 首发来源：Show HN
- 发布时间：2026-09
- 当前状态：活跃（v1.6.0）