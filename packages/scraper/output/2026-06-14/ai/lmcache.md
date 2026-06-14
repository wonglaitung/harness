# LMCache

## 技术定义 (What)
LLM KV Cache 加速层，支持跨 vLLM 实例共享前缀 KV Cache，显著降低长上下文场景的首 token 延迟（TTFT）。可将 KV Cache 存储到远程后端，实现多实例间缓存复用。

## 行业痛点 (Why)
长上下文 LLM 应用的首 token 延迟高，相同前缀在多实例间重复计算，GPU 内存利用率低，无法共享计算结果。

## 旧范式 vs 新范式
- **旧做法**：每个 vLLM 实例独立计算 KV Cache，相同前缀重复计算，长上下文场景 TTFT 可达数秒甚至数十秒。
- **新做法**：KV Cache 外置存储，跨实例共享前缀缓存，相同前缀只需计算一次。支持本地磁盘、远程服务器等多种存储后端。

## 生产力影响 (How)
长上下文 QA 应用中，第二轮问答延迟可降低 50%以上；多实例部署时 GPU 内存效率显著提升；适合 RAG、多轮对话等场景。

## 采用成本
Python 3.10+，需修改 vLLM 启动参数添加 LMCache 配置，提供 Docker 镜像。学习成本中等，需理解 KV Cache 原理。

## 核心线索
- GitHub：https://github.com/LMCache/LMCache
- 来源：https://github.com/LMCache/LMCache
- 发布时间：2026-06-14
