# Flue

## 技术定义 (What)
Flue 是首个 TypeScript Agent Harness Framework，提供可编程的 Agent 线束架构。内置沙箱环境、会话管理、工具系统、技能系统、持久化执行等核心原语，让任何模型都能像 Claude Code/Codex 一样进行自主工作。支持本地 CLI 运行或部署到 Cloudflare Workers/Node.js/GitHub Actions 等任意平台。

## 行业痛点 (Why)
第一代 Agent 架构局限性：要么是简单的 LLM API 调用（仅适用于聊天机器人），要么是黑盒产品（Claude Code/Codex 不可定制）。开发者无法在自己的应用中构建同等能力的自主 Agent，缺乏会话持久化、安全沙箱、工具集成等基础设施。

## 旧范式 vs 新范式
- **旧做法**：旧做法：1) 原始 LLM API 调用，自己管理对话历史和状态；2) 使用 LangChain 等框架，但缺乏沙箱和持久化；3) 依赖 Claude Code/Codex 等黑盒产品，无法定制；4) Agent 只能做简单任务，无法安全执行文件操作、运行代码等高风险行为
- **新做法**：新做法：1) 声明式定义 Agent（model + tools + skills + sandbox + instructions）；2) 内置本地/远程沙箱，Agent 可安全执行文件操作、运行命令；3) 会话持久化 + 持久化执行，崩溃后自动恢复；4) Skills 系统封装专业知识，Agent 动态加载；5) 一次定义，随处部署（CLI/Cloudflare/Node.js）

## 生产力影响 (How)
开发者可在几天内构建 Claude Code 级别的自主 Agent，而非数月。内置沙箱让 Agent 安全执行真实工作（修改文件、运行测试、部署应用）。持久化执行让长时间任务（如重构整个代码库）可在崩溃后继续。多平台部署让 Agent 从本地原型快速变成生产服务。

## 采用成本
学习曲线：TypeScript 开发者 1-2 天上手。时间成本：定义 Agent + 编写 Skills + 配置沙箱约 1 周。金钱成本：开源免费，运行时费用取决于选择的模型和部署平台。

## 核心线索
- GitHub：https://github.com/withastro/flue
- 来源：https://github.com/trending/typescript
- 发布时间：2026-06-21
