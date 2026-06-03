# SDK 改进路线图

基于对 `packages/sdk/docs/02-agent-loop.md` 的深度评审，整理出以下改进建议与优先级。

---

## 结论与优先级

**核心改进方向**：
1. 可取消/中断真实网络请求和工具执行
2. 精确 token 计数与预估（调用前拒绝超预算请求）
3. asyncio.Queue + 高/低水位实施强背压
4. 语义重复/低信息增益检测补强 Stuck Detection

---

## 短期改进（0-2周，高价值）

### 1. 可取消性与中断

**问题**：`interrupt()` 无法终止正在进行的 LLM HTTP 请求或耗时工具。

**方案**：
- 将 LLM 调用与工具执行包装为 `asyncio.Task`，在 `interrupt()` 时调用 `task.cancel()`
- 选用支持取消的 HTTP 客户端（httpx.AsyncClient）
- 对工具执行使用进程隔离 + 强制超时 kill

**实现要点**：
```python
# 可取消 LLM 调用模式
call_task = asyncio.create_task(self.llm.call(...))
await asyncio.wait([call_task], timeout=...)
# 中断时
call_task.cancel()
await safe_cancel(call_task)  # 清理资源
```

### 2. 流式背压重构

**问题**：当前 `StreamingHandler` 用 `deque + pause_on_backpressure`，上游停发依赖 sleep。

**方案**：
- 用 `asyncio.Queue(bounded)` 作为 buffer
- 生产者 `await queue.put(...)` 自然阻塞
- 高/低水位控制：`queue.qsize() >= high → pause; <= low → resume`

**实现要点**：
```python
# 生产者
await queue.put(chunk)  # 满时自动 await

# 消费者
chunk = await queue.get()
process(chunk)
queue.task_done()
```

### 3. 精确 Token 计数

**问题**：需更精确高效的 token 计数。

**方案**：
- OpenAI: tiktoken
- Anthropic: 官方 tokenizer 或通用 BPE
- 调用前预估：`count_messages + estimate_tool_overhead + reserved_output`
- 超预算 → context compression 或拒绝请求

### 4. 基础监控指标

导出关键指标到 Prometheus：
- `llm_call_latency` (histogram)
- `llm_input_tokens / llm_output_tokens` (counter)
- `queue_size / backpressure_events` (gauge)
- `stuck_detections_total` (counter)

---

## 中期改进（2-6周）

### 5. 语义 Stuck Detection

**问题**：当前基于"连续空/错误"，漏掉"重复输出/低信息增益"。

**方案**：
- Embedding-based 相似度检测
- 最近 K 轮 embedding 序列
- 连续 M 次高相似度 → stuck
- 参数：`similarity_threshold=0.92`, `consecutive_similar_rounds=3`

**详见**：`packages/sdk/docs/stuck-detection-embedding.md`

### 6. 工具执行隔离

- 迁移到子进程/进程池
- 强制超时 + kill
- 审计日志与权限模型

### 7. 动态 ModelSelector

- 根据预算/latency/质量历史选择模型
- 预算紧时切换 cheaper model

### 8. 安全增强

- 容器/gVisor/Firecracker 隔离
- Capability/permission 元数据
- Prompt 注入校验

---

## 期改进（6-12周）

### 9. 集中化 CostStorage

- Postgres/Redis 支持
- 多实例并发访问 + 原子计数

### 10. 自适应反馈

- 基于真实指标自动调整阈值
- ML 模型判断置信度

### 11. 强沙箱执行

- 容器/VM 级隔离
- 生产高安全需求

---

## 技术选型参考

| 功能 | 推荐库 |
|------|--------|
| Tokenizers | tiktoken, anthropic-tokenizer, HuggingFace tokenizers |
| HTTP clients | httpx.AsyncClient, aiohttp |
| Retry/backoff | tenacity |
| Circuit breaker | pybreaker（参考），自实现 |
| Embeddings | sentence-transformers, OpenAI embeddings |
| Observability | opentelemetry + prometheus_client |
| Isolation | subprocess + seccomp, gVisor, Firecracker |
| Caching | Redis, SQLite, Postgres |

---

## 已实现：Embedding-based Stuck Detection

实现文件：
- `packages/sdk/src/harness/core/stuck_detector.py` - 核心检测器
- `packages/sdk/tests/test_stuck_detector.py` - 单元测试

**关键组件**：
1. `EmbeddingProvider` - 抽象接口
2. `SentenceTransformersProvider` - 本地实现
3. `StuckDetector` - 检测逻辑
4. `EmbeddingCache` - 缓存层

**参数**：
- `similarity_threshold`: 0.92
- `consecutive_similar_rounds`: 3
- `window_size`: 6
- `min_chars_for_embedding`: 30

---

## 下一步行动

1. 将 Stuck Detection 实现集成到 AgentLoop
2. 实现可取消 LLM 调用层
3. 用 asyncio.Queue 替换 deque 背压
4. 添加 tiktoken token 计数