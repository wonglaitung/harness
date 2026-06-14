# LMCache

## 技术定义 (What)
首个专门优化 LLM KV 缓存的加速层，支持跨 vLLM 实例共享前缀 KV 缓存，显著降低长上下文场景的 TTFT（Time To First Token）。

## 行业痛点 (Why)
长上下文场景下，每次请求都需要重新计算 KV 缓存，导致 TTFT 过长，GPU 资源浪费，无法复用已计算的缓存。

## 旧范式 vs 新范式
- **旧做法**：每个 vLLM 实例独立计算 KV 缓存，相同前缀无法复用，长上下文首次响应延迟可达数十秒。
- **新做法**：独立缓存服务器存储 KV 缓存，多个 vLLM 实例可共享前缀缓存，相同上下文第二次请求 TTFT 降低 80% 以上。

## 生产力影响 (How)
支持多租户场景下的缓存共享，降低 GPU 内存占用，提升吞吐量，适合文档问答、代码助手等长上下文应用。

## 采用成本
开源免费，支持 vLLM 集成，需额外部署 LMCache 服务器，提供 Docker 镜像快速启动。

## 核心线索
- GitHub：https://github.com/LMCache/LMCache
- 来源：https://github.com/LMCache/LMCache
- 发布时间：2026-06-14
