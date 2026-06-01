# 13 - Production Readiness 生产就绪检查

## 概述

本文档提供将 Harness SDK 部署到生产环境的检查清单。

## 组件状态检查

### ✅ 已就绪

| 组件 | 检查项 | 验证方法 |
|------|--------|----------|
| Orchestration Loop | 熔断器启用 | `loop._circuit_breaker is not None` |
| Tools | 权限检查 | `tool_executor._check_permissions()` |
| Sandbox | 命令黑名单 | `sandbox.validate_command("rm -rf /")` |
| Error Handling | 卡住检测 | `loop._is_stuck()` |
| Cost Control | 预算控制 | `CostController.check()` |

### ⚠️ 需配置

| 组件 | 检查项 | 配置方法 |
|------|--------|----------|
| Memory | 持久化存储 | `SessionStore(path="~/.harness/sessions")` |
| Context Management | 压缩阈值 | `compression_threshold=0.8` |
| Cost Control | 预算限制 | `CostConfig(max_tokens_per_session=1000000)` |
| Audit Log | 审计日志 | `SecurityConfig(enable_audit_log=True)` |

### ❌ 待实现

| 组件 | 功能 | 替代方案 |
|------|------|----------|
| Lifecycle Hooks | 工具拦截 | 子类化 ToolExecutor |
| Ralph Loop | 长任务循环 | 手动重启 session |
| 向量检索 | 语义搜索 | 使用外部 RAG 服务 |
| MEMORY.md | 跨会话记忆 | 手动维护项目文档 |

---

## 生产部署清单

### 必需配置

- [ ] **配置持久化存储**
  ```python
  from harness import AgentHarness, SQLiteSessionStore
  
  agent = AgentHarness(
      session_store=SQLiteSessionStore("~/.harness/harness.db")
  )
  ```

- [ ] **设置成本控制预算**
  ```python
  from harness.types import CostConfig
  
  agent = AgentHarness(
      cost_config=CostConfig(
          max_tokens_per_session=1_000_000,
          daily_token_limit=10_000_000,
      )
  )
  ```

- [ ] **启用审计日志**
  ```python
  from harness.sdk.config import SecurityConfig
  
  agent = AgentHarness(
      security_config=SecurityConfig(
          enable_audit_log=True,
          audit_log_dir="/var/log/harness/audit",
      )
  )
  ```

### 推荐配置

- [ ] **配置命令白名单**
  ```python
  from harness.security import SandboxConfig
  
  agent = AgentHarness(
      sandbox_config=SandboxConfig(
          allowed_commands=["git", "npm", "pytest", "python"],
          blocked_patterns=["rm -rf /", "sudo", "chmod 777"],
      )
  )
  ```

- [ ] **设置超时限制**
  ```python
  from harness.core import LoopConfig
  
  agent = AgentHarness(
      loop_config=LoopConfig(
          max_iterations=50,
          timeout_per_tool=30.0,
      )
  )
  ```

- [ ] **准备错误恢复策略**
  ```python
  # 保存快照
  snapshot = agent._loop.create_snapshot(session, iteration)
  
  # 从快照恢复
  result = await agent._loop.resume_from_snapshot(snapshot)
  ```

---

## 监控与可观测性

### 启用 OpenTelemetry

```python
from harness import setup_observability, ObservabilityConfig

setup_observability(ObservabilityConfig(
    service_name="production-agent",
    export_otlp=True,
    otlp_endpoint="http://jaeger:4317",
))
```

### 进度事件监控

```python
def on_progress(event: ProgressEvent):
    if event.type == ProgressEventType.ERROR:
        logger.error(f"Agent error: {event.message}")
    elif event.type == ProgressEventType.LOOP_END:
        logger.info(f"Completed in {event.duration_ms}ms")

agent.set_progress_callback(on_progress)
```

---

## 安全检查清单

### 工具权限

- [ ] 检查敏感工具是否需要权限确认
- [ ] 配置沙箱隔离级别
- [ ] 验证命令黑名单是否完整

### 数据安全

- [ ] 确认 API 密钥存储安全（环境变量/密钥管理服务）
- [ ] 检查日志是否包含敏感信息
- [ ] 验证审计日志的访问权限

### 网络安全

- [ ] 配置 HTTP 超时
- [ ] 验证外部 API 调用的安全性
- [ ] 检查 MCP 服务器连接是否需要认证

---

## 性能优化建议

### Token 效率

- 启用上下文压缩（默认启用）
- 配置合理的压缩阈值（0.8-0.9）
- 使用 token 计数缓存

### 并发处理

- 启用并行工具执行（默认启用）
- 配置合理的并发限制
- 使用异步存储后端

### 内存管理

- 限制单会话消息数量
- 定期清理过期会话
- 使用增量 token 计数

---

## 故障排查指南

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| `BudgetExceededError` | Token 超限 | 增加 `max_tokens_per_session` 或优化上下文 |
| `CircuitBreakerError` | 重复调用同一工具 | 检查 Agent 是否陷入循环 |
| `TimeoutError` | 工具执行超时 | 增加 `timeout_per_tool` 或优化工具 |
| Agent 卡住 | 连续空/错误结果 | 检查 Stuck Detection 日志 |

### 日志级别

```python
import logging
logging.getLogger("harness").setLevel(logging.DEBUG)
```

---

## 版本兼容性

| Harness SDK | Python | Anthropic SDK | OpenAI SDK |
|-------------|--------|---------------|------------|
| 0.1.x | 3.10+ | 0.30+ | 1.0+ |
