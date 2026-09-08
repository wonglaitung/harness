# Experiential — Traffic-Driven Model Routing

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首创"从生产流量学习→训练专属路由器→优化专属模型"的闭环架构 |
| 采用广度 | ☆☆☆/5 | 刚刚开源，但集成了 OpenAI、Anthropic、Gemini、Azure 等全生态 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年9月 GitHub Trending，Show HN 220分 |
| 社区热度 | ☆☆☆☆/5 | GitHub 561★/天 trending #1 Python，Show HN 220分 |
| **总体判断** | ✅ | **新范式——Agent 推理从"手动选模型"到"流量自动优化路由器"的根本转变** |

## 技术定义 (What)

Experiential 是一个开源 Gateway + Router，核心创新是 **Traffic-Driven Model Routing**：收集 Agent 的真实推理流量（OpenTelemetry traces），自动分析任务特征，构建最优路由策略，最终训练出专属于你的工作负载的优化模型。

三层架构：
1. **Gateway**：OpenAI 兼容 API，统一接入托管/BYOK/本地模型
2. **Router**：基于流量数据学习路由决策——什么任务路由到哪个模型
3. **Optimizer**：从路由流量中提取训练数据，微调开源模型

## 行业痛点 (Why)

当前 Agent 开发者面临的核心问题：手动选择模型（GPT-6 for X, Claude for Y 的试错法）、不同任务对不同模型的最优匹配未知、推理成本不可控。Experiential 把"选什么模型"这个问题本身变成可学习、可优化的系统。

## 旧范式 vs 新范式
- **旧做法**：开发者手动在代码里硬编码模型选择（if task==coding → use Sonnet），凭经验和口碑盲选
- **新做法**：部署 Gateway → 收集流量 → 自动构建 Router → 训练专属模型。Router 从真实数据中学习，持续进化

## 生产力影响 (How)

- **成本优化**：自动将简单任务路由到便宜模型、复杂任务路由到强大模型
- **质量提升**：流量数据驱动的模型选择比人工猜测更精准
- **模型自主**：最终可以训练出自己拥有的专属模型，摆脱供应商锁定
- **零摩擦接入**：OpenAI 兼容 API，现有 Agent 代码无需修改

## 采用成本
- 安装：`pip install experiential`，一行命令启动
- 学习曲线：低——现有 OpenAI SDK 代码无需修改
- 基础设施：需要收集一段时间的流量 traces 才能开始优化

## 采用案例
- 项目自带的 `wmo-terminal-tasks` 公开数据集可直接用于尝试
- 配合 Tinker（Thinking Machines 的后训练平台）可微调开源模型
- 适用于 Claude Code、Cursor、Codex、Aider 等所有主流 Coding Agent

## 风险/局限
- 需要足够的流量数据才能有效路由（冷启动问题）
- 路由策略的黑盒性可能导致调试困难
- 尚处于早期阶段，API 可能变动

## 核心线索
- GitHub：https://github.com/experientiallabs/experiential
- Show HN：220 points
- 发布时间：2026年9月
- 当前状态：活跃开发中
- 技术栈：Python，OpenTelemetry，OpenAI 兼容 API