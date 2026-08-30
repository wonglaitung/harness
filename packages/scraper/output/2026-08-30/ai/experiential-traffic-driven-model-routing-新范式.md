## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 核心创新：Agent 生产流量 → 构建模拟器 → 训练路由策略 → 部署优化路由，形成完整数据飞轮 |
| 采用广度 | ☆☆/5 | Show HN 215pts，尚在早期 |
| 时间新鲜 | ☆☆☆☆/5 | 活跃开发中，2026-08 首次 Show HN |
| 社区热度 | ☆☆☆/5 | Show HN 215pts，Discord 社区 |
| **总体判断** | ✅ | **新范式 — 流量驱动的 Agent 模型路由优化** |

## 技术定义 (What)
开源网关和路由器：将所有 LLM 提供商（OpenAI、Anthropic、Gemini、Azure 等）统一为一个 OpenAI 兼容 API。核心创新是「从流量中学习」：收集 Agent 调用的 OpenTelemetry traces → 构建模拟器 → 优化路由策略，使每类任务自动选择最优模型（质量/速度/成本）。

## 行业痛点 (Why)
当前 Agent 工作流中模型选择靠人工经验：需要手动判断哪个模型适合哪个任务. Experiential 让 Agent 的日常使用流量自动「训练」出最优路由策略，形成「用得越多，路由越聪明」的正循环。

## 旧范式 vs 新范式
- **旧做法**：人工配置模型路由，或简单成本优先路由
- **新做法**：从 Agent 流量 traces 构建项目级模拟器，离线优化路由策略，部署后持续从流量中学习

## 生产力影响 (How)
- 降低 30-50% API 成本（自动选择更便宜的模型处理简单任务）
- 消除人工模型选择决策
- 实现模型供应商无感切换

## 采用成本
pip install experiential，15分钟上手。BUILD 需要历史 trace 数据。optimize 需要 Tinker 平台。

## 采用案例
- 自举案例：收集 Claude Code/Cursor/Codex 的 agent trace，构建项目路由器
- 公开数据集：terminal-tasks OTLP dataset 用于实验

## 风险/局限
- 路由精度依赖 trace 数据质量
- fine-tune 环节需要 Tinker 平台，有 vendor lock-in 风险
- 目前生态规模较小

## 核心线索
- GitHub：https://github.com/experientiallabs/experiential
- Show HN：https://news.ycombinator.com/item?id=讨论帖
- 发布时间：2026-08（Show HN）
- 当前状态：活跃开发中