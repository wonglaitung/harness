# LMCache

## 技术定义 (What)
LLM KV Cache 加速层，支持跨 vLLM 实例共享和复用 KV Cache，将长上下文推理的首 token 延迟降低 50-90%。通过内存缓存、磁盘持久化、对象存储后端等多种存储方式，大幅降低 GPU 显存占用。

## 行业痛点 (Why)
长上下文 Agent 应用（如 SWE-bench、多轮工具调用）每次推理都要重新计算 KV Cache，导致：1）首 token 延迟高；2）GPU 显存快速耗尽；3）跨实例无法共享已计算的上下文状态。

## 旧范式 vs 新范式
- **旧做法**：每个 vLLM 实例独立计算和存储 KV Cache，相同前缀上下文被重复计算。长上下文场景下，单个请求的 KV Cache 就可能占用数 GB 显存，限制并发能力和上下文长度。
- **新做法**：引入独立的 KV Cache 存储层，支持：1）相同前缀的 KV Cache 跨请求复用；2）跨多个 vLLM 实例共享缓存；3）从 GPU 显存卸载到 CPU/磁盘/对象存储。通过缓存命中大幅降低推理延迟和显存占用。

## 生产力影响 (How)
长上下文场景下可将首 token 延迟从数十秒降至秒级，显存占用降低 70-90%。支持多实例共享缓存，适合需要处理大量文档或长对话历史的 Agent 应用。与 vLLM 深度集成，迁移成本低。

## 采用成本
需要修改 vLLM 启动配置（添加 --lmcache-config-file），部署 LMCache 后端服务（可选）。学习曲线中等，需要理解 KV Cache 的生命周期和缓存策略。适合已有 vLLM 基础设施的场景。

## 核心线索
- GitHub：https://github.com/LMCache/LMCache
- 来源：https://github.com/LMCache/LMCache
- 发布时间：2026-06-14
