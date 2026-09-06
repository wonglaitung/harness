# Magnitude — Agent-First 本地推理新范式

## 技术定义 (What)
Magnitude 是一个专为 AI Coding Agent 设计的开源本地推理服务器。不同于通用推理引擎（如 Ollama），它的核心差异在于：1）自动检测硬件配置并推荐最优模型；2）Agent-first 安装流程——只需给 Agent 发送一条 prompt 即可完成配置；3）模型按需加载/卸载（JIT loading），空闲时释放内存。支持 Pi、OpenCode、Hermes、Codex、Claude Code 等主流 Coding Agent。

## 行业痛点 (Why)
当前开发者用 Ollama 跑本地模型时，Agent 不知道硬件配置、不知道该选哪个量化版本、不知道推理速度——需要大量手动配置。Agent 开发者需要非技术人员也能一键使用本地模型。

## 旧范式 vs 新范式
- **旧做法**：使用 Ollama/llama.cpp 时：手动下载模型、手动选量化版本、手动配置 Agent 连接、模型常驻内存浪费资源、Agent 无法感知硬件约束
- **新做法**：Magnitude 新范式：Agent 驱动安装（一条 prompt）、硬件自动画像+模型推荐、JIT 模型加载/卸载、原生集成主流 Coding Agent、模型切换由 Agent 通过 CLI 自主完成

## 生产力影响 (How)
大幅降低 Agent 使用本地模型的门槛——从"需要了解 GGUF/量化/显存"变为"发一条 prompt"。让非技术用户也能享受免费、私密的本地推理，同时为专业用户提供智能化的资源管理。

## 采用成本
npm install -g @magnitudedev/cli；免费开源（Apache 2.0）；学习成本极低（Agent 引导）；需要 Apple Silicon Mac 或 Linux

## 核心线索
- GitHub：https://github.com/magnitudedev/magnitude
- 来源：https://github.com/magnitudedev/magnitude
- 发布时间：2026-09-07
