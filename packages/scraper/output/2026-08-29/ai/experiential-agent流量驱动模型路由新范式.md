# Experiential — Agent Traffic-Optimized Model Router

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次提出"从Agent trace数据自动优化模型路由"的概念——将OpenTelemetry追踪转化为模型选择策略，而非简单的负载均衡 |
| 采用广度 | ☆☆/5 | 新项目，刚发布，但已支持Claude Code、Cursor、Codex、Aider等主流Agent |
| 时间新鲜 | ☆☆☆☆☆/5 | Show HN 2026年8月，全新发布 |
| 社区热度 | ☆☆☆☆/5 | Show HN 208分，社区高度关注 |
| **总体判断** | ✅ | **新范式 — Agent流量驱动模型路由** |

## 技术定义 (What)
Experiential 是一个开源Agent网关和路由器，核心理念是"用你的Agent实际流量来优化模型选择"：
1. 通过一个OpenAI兼容API统一接入所有模型（OpenAI、Anthropic、Gemini、本地模型等）
2. 收集OpenTelemetry traces作为"流量日志"
3. 分析实际使用模式，自动构建仿真环境并训练出最优路由策略
4. 甚至可以基于流量数据fine-tune你自己的开源模型

## 行业痛点 (Why)
当前开发者面临两个核心问题：
- **模型选择困境**：多个模型提供商，不同任务适合不同模型，手动切换效率低
- **成本失控**：Agent工作流经常调用昂贵的模型做简单任务，缺乏智能路由
- **缺乏反馈闭环**：无法从实际使用中学习哪些模型对哪些场景最有效

## 旧范式 vs 新范式
- **旧做法**：旧范式：开发者手动指定模型（"coding用Opus，简单问答用Haiku"），或使用简单的规则路由（如OpenRouter的fallback链）。路由策略是静态的、基于直觉的。
- **新做法**：新范式：Experiential从Agent实际trace数据中学习路由策略。收集你的Agent实际调用了什么模型、做了什么任务、花了多少钱 → 构建仿真 → 优化出针对你工作负载的最优路由。路由策略是基于数据的、动态进化的。

## 生产力影响 (How)
- **降低成本**：自动将简单任务路由到便宜模型，复杂任务路由到强模型
- **提升质量**：基于实际数据而非直觉做路由决策
- **统一管理**：一个API管理所有模型、用户权限、预算
- **持续优化**：随着更多trace数据积累，路由策略自动改进

## 采用成本
pip install experiential 即可本地运行；托管版按用量付费。学习成本低（OpenAI兼容API）。主要成本在于需要积累足够的Agent trace数据才能有效优化路由。

## 采用案例
- 企业内部多个Agent（Claude Code、Cursor、Codex等）统一通过Experiential网关接入，实现集中预算控制和智能路由
- 结合Tinker平台（Thinking Machines），可将优化后的路由策略fine-tune为自有模型

## 风险/局限
- 需要足够的trace数据积累才能有效优化
- 路由策略依赖trace质量
- 作为新项目，生态和稳定性待验证

## 核心线索
- GitHub：https://github.com/experientiallabs/experiential
- 首发来源：Show HN
- 发布时间：2026年8月
- 当前状态：活跃（早期项目）