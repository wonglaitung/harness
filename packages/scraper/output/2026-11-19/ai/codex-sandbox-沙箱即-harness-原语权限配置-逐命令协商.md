# Codex Sandbox — 沙箱即 Harness 原语（权限配置 + 逐命令协商）

## 技术定义 (What)
Codex 不做 Docker/VM 迁移，而是直接调用各平台原生沙箱（macOS seatbelt / Linux Landlock+seccomp / Windows），在用户真实环境内约束命令。核心抽象有三层：(1) permission profile（如 :workspace 允许写工作区、.git/.codex 只读、默认禁网）；(2) 统一跨平台 API spawn_command_under_sandbox(command, profile, proxy)，子进程继承父级约束，整棵进程树持续受控；(3) 逐命令权限协商——模型可请求 use_default / with_additional_permissions / require_escalated，但由 harness 依据用户偏好裁决，而非模型自决。

## 行业痛点 (Why)
Agent 跑 shell 命令是最高风险动作。Docker 路线的问题：开发者笔记本是"定制环境"，重建进容器成本高；更致命的是 iOS 构建、模拟器等宿主机原生工具链在容器里根本跑不了，若委托回宿主则等于沙箱失效。同时"全程要授权"和"全程不授权"都不可用，需要细粒度的、可继承的、可协商的权限边界。

## 旧范式 vs 新范式
- **旧做法**：要么把 agent 关进 Docker/VM 里做隔离（牺牲环境保真度，还常因原生工具链被迫逃逸）；要么干脆不沙箱、靠模型对齐+用户逐次点击确认（不可审计、不可继承、易被社工）。
- **新做法**：沙箱成为 harness 的一等原语而非外部包装：环境原地保真、约束由 profile 声明、进程树继承、权限可逐命令协商且由 harness 而非模型裁决，并把这套机制以统一 API 暴露给第三方开发者复用。

## 生产力影响 (How)
让"agent 直接在你的真机上干活"变得可部署：默认 profile 就能覆盖大部分日常开发（写工作区、禁网防外泄），企业可按需定制并在统一 API 上构建自己的 agent 工具。文章亦诚实指出残余风险——agent 污染 node_modules/prettier 这类被 git 忽略的本地包，用户编辑器保存文件时即在沙箱外执行，故沙箱必须与训练对齐叠加（defense in depth）。

## 采用成本
低。终端用户改 profile；开发者复用其跨平台 API（需自带网络代理以执行细粒度网络限制）；企业侧有现成 security cookbook。跨三平台一致行为是主要学习成本。

## 核心线索
- GitHub：https://github.com/openai/codex
- 来源：https://openai.com/index/inside-the-codex-sandbox
- 发布时间：2026-11-19
