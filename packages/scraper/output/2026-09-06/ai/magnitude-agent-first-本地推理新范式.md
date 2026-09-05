# Magnitude — 硬件感知本地推理服务器

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | Agent-first setup + 硬件自动感知 + 模型推荐引擎，将推理服务器从"工具"变为"Agent 基础设施" |
| 采用广度 | ☆☆☆/5 | 已集成 8 个主流 Agent harness（Pi, OpenCode, Hermes, Codex, Claude Code 等） |
| 时间新鲜 | ☆☆☆☆/5 | GitHub 趋势日增 686★，社区活跃 |
| 社区热度 | ☆☆☆☆/5 | TypeScript trending #3，Discord 社区活跃，Apache 2.0 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)

Magnitude 是一个开源本地推理服务器（Apache 2.0），核心创新在于 **Agent-first 硬件感知**：它自动检测你的芯片、内存和带宽，推荐最适合你硬件的本地模型，预估 tok/s 性能，然后一键下载、调优、运行。支持 macOS/Linux，完全离线。

## 行业痛点 (Why)

当前本地推理方案（Ollama、llama.cpp）需要用户手动：(1) 判断自己硬件能跑什么模型，(2) 选择合适的量化版本，(3) 配置推理参数。Agent 不知道你的硬件限制，只能盲目猜测。这导致非技术用户被排除在本地 AI 之外。

## 旧范式 vs 新范式
- **旧做法**：用户手动研究硬件→手动选模型→手动调参数→手动配 Agent。Agent 对硬件一无所知。
- **新做法**：一条 prompt `Set up local models for me` → Agent 调用 Magnitude 自动检测硬件 → 获得推荐模型目录 → 自动下载安装 → 无缝接入正在使用的 Agent。

## 生产力影响 (How)
- 将本地 AI 部署从"需要研究 2 小时"降到"一条 prompt 搞定"
- 模型按需加载/卸载，节省内存；空闲时自动释放
- 支持 speculative decoding 和并发优化，端到端调优

## 采用成本
极低 — `npm i -g @magnitudedev/cli && magnitude setup`。主要成本是模型下载时间和本地存储空间。

## 采用案例
- OpenCode：通过 Magnitude 接入本地模型，完全离线编程
- Claude Code / Codex：降低 API 成本，文件不外传
- Pi / Hermes / OpenClaw / Cline：均已原生集成

## 风险/局限
- 依赖 GGUF 生态，模型选择受限于已量化的模型
- 大型模型仍需大量内存（无魔术压缩）
- Windows 仅支持 WSL

## 核心线索
- GitHub：https://github.com/magnitudedev/magnitude
- 首发来源：GitHub Trending (TypeScript #3, 2026-09-06)
- 当前状态：活跃（Apache 2.0）