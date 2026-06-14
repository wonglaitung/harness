# LMCache

## 技术定义 (What)
高性能 KV Cache 层，用于加速 LLM 长上下文推理。支持跨多个 vLLM 实例共享 KV Cache，将重复前缀上下文的推理成本降低 10 倍以上。通过对象存储持久化 KV Cache，实现跨服务、跨会话的缓存复用。

## 行业痛点 (Why)
长上下文 Agent 工作流（如 SWE-bench 任务、多步骤浏览、终端会话）中，每个工具调用结果都追加到上下文，后续 token 需要对所有历史内容重新计算注意力。KV Cache 内存占用随序列长度线性增长，在 100 万 token 上下文场景下，单次推理的 KV Cache 可能占用数十 GB 显存。

## 旧范式 vs 新范式
- **旧做法**：每个 vLLM 实例独立管理 KV Cache，无法跨实例共享。长上下文推理需要重复计算相同前缀的 KV Cache，导致高延迟、高显存占用、低吞吐量。Agent 在长任务中途容易因显存不足而失败。
- **新做法**：引入独立的 LMCache 后端服务器，vLLM 实例通过配置文件连接到同一缓存后端，实现 KV Cache 跨实例共享。支持本地内存、Redis、对象存储等多种后端。首次请求计算 KV Cache 并存储，后续请求直接复用，TTFT（Time To First Token）降低 90%+。

## 生产力影响 (How)
对于共享前缀的多轮对话场景（如 RAG、文档问答、Agent 工作流），第二次及后续请求的响应延迟接近零拷贝。支持在相同硬件上部署更多 vLLM 实例（无需重复加载相同前缀），提升 GPU 利用率和吞吐量。特别适合多租户 SaaS 场景，多个用户可能查询相同文档库。

## 采用成本
中等。需要部署独立的 LMCache 后端服务器，配置 vLLM 实例连接到缓存后端。支持 Docker 部署，文档完善。对现有应用透明，只需修改启动参数即可接入。学习成本主要在于理解 KV Cache 生命周期管理和缓存策略。

## 核心线索
- GitHub：https://github.com/LMCache/LMCache
- 来源：https://github.com/LMCache/LMCache
- 发布时间：2026-06-15
