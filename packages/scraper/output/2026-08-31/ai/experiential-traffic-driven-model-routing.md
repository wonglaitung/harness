# Experiential — Traffic-Driven Model Routing

## 技术定义 (What)
Experiential 是一个开源 API 网关和路由器，专为 Agent 工作流设计。它提供统一的 OpenAI 兼容 API，支持托管模型、BYOK（自带密钥）和本地模型；通过身份/Agent/预算三维访问控制管理模型使用；核心创新在于"从生产流量中学习"——收集 Agent 调用的 OpenTelemetry traces，自动构建仿真环境并优化路由策略，最终可微调出自有模型。

## 行业痛点 (Why)
Agent 应用每天产生海量 LLM 调用，不同任务对模型的质量、速度、成本需求各异。人工为每个 Agent、每个场景选择模型既低效又易出错。同时，企业需要统一的访问控制、预算管理和可观测性。

## 旧范式 vs 新范式
- **旧做法**：静态路由：开发者手动配置"用哪个模型做哪类任务"，或使用简单的 fallback 链。路由策略依赖人工经验，无法随流量模式自适应优化。
- **新做法**：流量驱动路由：收集 Agent 实际调用 trace → 构建仿真 → 优化路由策略 → 可选微调自有模型。模型选择不再靠人工经验和静态规则，而是由实际流量数据驱动，自动为每个请求选择最优模型（质量/速度/成本权衡）。

## 生产力影响 (How)
(1) 一条命令启动本地网关，所有 AI 编码工具（Claude Code、Cursor、Codex 等）一键接入；(2) 从自身流量中自动学习最优路由，降低推理成本同时保持质量；(3) 身份/Agent/预算三维管控满足企业合规需求；(4) 最终可微调自有模型，摆脱对第三方 API 的依赖。

## 采用成本
低：pip install experiential 即可启动；BYOK 模式无额外成本；优化路由需收集自身流量数据

## 核心线索
- GitHub：https://github.com/experientiallabs/experiential
- 来源：https://news.ycombinator.com/show — Show HN 220 points
- 发布时间：2026-08-31
