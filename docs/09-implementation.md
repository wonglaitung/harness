# 09 - 实施路线图

## 概述

本文档规划了 Harness 项目的实施路线图，按阶段划分，确保从 MVP 到生产就绪的渐进式开发。

## 项目结构

```
harness/
├── src/
│   └── harness/
│       ├── __init__.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── agent_loop.py
│       │   ├── context.py
│       │   └── result.py
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   └── local.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── executor.py
│       │   ├── file.py
│       │   ├── shell.py
│       │   ├── web.py
│       │   └── mcp.py
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── session.py
│       │   ├── store.py
│       │   ├── context_builder.py
│       │   └── compressor.py
│       ├── skills/
│       │   ├── __init__.py
│       │   ├── skill.py
│       │   ├── registry.py
│       │   ├── loader.py
│       │   └── generator.py
│       ├── triggers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── cron.py
│       │   ├── webhook.py
│       │   └── manager.py
│       ├── security/
│       │   ├── __init__.py
│       │   ├── permissions.py
│       │   ├── sandbox.py
│       │   ├── validator.py
│       │   └── audit.py
│       ├── sdk/
│       │   ├── __init__.py
│       │   ├── harness.py
│       │   └── config.py
│       └── cli/
│           ├── __init__.py
│           └── main.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
├── examples/
├── skills/
│   └── default/
├── pyproject.toml
├── setup.py
└── README.md
```

## Phase 1: MVP 核心功能 (Week 1-3)

### 目标

构建最小可用版本，验证核心架构。

### 任务清单

#### Week 1: Agent Loop & LLM 客户端

| 任务 | 优先级 | 状态 |
|------|--------|------|
| AgentLoop 核心循环实现 | P0 | - |
| 基础状态机 | P0 | - |
| LLMClient 抽象接口 | P0 | - |
| AnthropicClient 实现 | P0 | - |
| OpenAIClient 实现 | P1 | - |
| Token 计数器 | P1 | - |
| 基础错误处理 | P0 | - |
| 单元测试 | P0 | - |

**交付物**:
- `src/harness/core/agent_loop.py`
- `src/harness/llm/`
- `tests/unit/test_agent_loop.py`

#### Week 2: 工具系统

| 任务 | 优先级 | 状态 |
|------|--------|------|
| Tool 基类定义 | P0 | - |
| ToolRegistry 实现 | P0 | - |
| ToolExecutor 实现 | P0 | - |
| File Tools (Read, Write, Edit) | P0 | - |
| Glob/Grep Tools | P0 | - |
| Bash Tool (基础版) | P1 | - |
| PermissionSet 实现 | P0 | - |
| 工具权限检查 | P0 | - |

**交付物**:
- `src/harness/tools/`
- `tests/unit/test_tools.py`

#### Week 3: 记忆系统基础

| 任务 | 优先级 | 状态 |
|------|--------|------|
| Session 数据结构 | P0 | - |
| FileSessionStore | P0 | - |
| ContextBuilder 基础版 | P0 | - |
| Token 预算管理 | P1 | - |
| 会话持久化 | P0 | - |

**交付物**:
- `src/harness/memory/`
- `tests/unit/test_memory.py`

### MVP 示例代码

```python
from harness import AgentHarness

# 最简使用
agent = AgentHarness(
    model="claude-sonnet-4-6",
    api_key="your-key"
)

# 运行
result = await agent.run("读取 main.py 并分析其结构")
print(result.content)
```

## Phase 2: 增强功能 (Week 4-6)

### 目标

增加高级特性，提升易用性和可靠性。

### 任务清单

#### Week 4: 上下文管理增强

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 上下文压缩器 | P1 | - |
| 会话摘要生成 | P1 | - |
| SQLite 存储 | P1 | - |
| 记忆检索基础 | P2 | - |

#### Week 5: 技能系统

| 任务 | 优先级 | 状态 |
|------|--------|------|
| Skill 文件格式 | P0 | - |
| SkillRegistry | P0 | - |
| SkillLoader | P0 | - |
| SkillInjector | P0 | - |
| 预置技能库 (5-10个) | P1 | - |

#### Week 6: 安全增强 & Web 工具

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 沙箱执行器 | P0 | - |
| 输入验证器 | P1 | - |
| WebSearch Tool | P1 | - |
| WebFetch Tool | P1 | - |
| 审计日志 | P1 | - |

### Phase 2 示例

```python
# 技能激活
agent = AgentHarness()
agent.load_skill("skills/code-review.md")
agent.activate_skill("code-review")

result = await agent.run("review this code")
```

## Phase 3: 高级特性 (Week 7-10)

### 目标

实现自主运行、多代理协调等高级特性。

### 任务清单

#### Week 7-8: 触发器系统

| 任务 | 优先级 | 状态 |
|------|--------|------|
| Trigger 基类 | P0 | - |
| CronTrigger | P0 | - |
| WebhookTrigger | P0 | - |
| HeartbeatTrigger | P1 | - |
| FileWatchTrigger | P2 | - |
| TriggerManager | P0 | - |
| OutputHandler | P1 | - |

#### Week 9: 多代理协调

| 任务 | 优先级 | 状态 |
|------|--------|------|
| EventBus | P1 | - |
| AgentTeam | P2 | - |
| MultiAgentOrchestrator | P2 | - |
| 并行/顺序分发 | P2 | - |

#### Week 10: MCP 支持

| 任务 | 优先级 | 状态 |
|------|--------|------|
| MCP 协议实现 | P1 | - |
| MCP Connector | P1 | - |
| MCP Tool 包装 | P1 | - |

### Phase 3 示例

```python
# 定时任务
agent.on_schedule("0 9 * * *", "生成每日报告")

# Webhook
agent.on_webhook("/github/pr", "Review PR changes")

# 启动后台服务
await agent.start()
```

## Phase 4: 生产就绪 (Week 11-12)

### 目标

完善文档、测试、性能优化，确保生产可用。

### 任务清单

#### Week 11: 完善与优化

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 完整类型注解 | P0 | - |
| 文档完善 | P0 | - |
| 性能优化 | P1 | - |
| 错误处理完善 | P0 | - |
| 日志系统 | P1 | - |
| 指标收集 | P2 | - |

#### Week 12: 测试与发布

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 单元测试覆盖 80%+ | P0 | - |
| 集成测试 | P0 | - |
| E2E 测试 | P1 | - |
| CI/CD 配置 | P0 | - |
| PyPI 发布准备 | P0 | - |
| 示例项目 | P1 | - |

### 发布清单

- [ ] 所有单元测试通过
- [ ] 集成测试通过
- [ ] 文档完整
- [ ] CHANGELOG 更新
- [ ] 版本号确定
- [ ] PyPI 发布
- [ ] GitHub Release

## 技术债务管理

### 已知技术债务

| 项目 | 描述 | 优先级 | 计划处理 |
|------|------|--------|----------|
| 流式输出优化 | 大文件流式处理性能 | P1 | Phase 4 |
| Token 计数精度 | 不同模型的 token 计数 | P2 | Phase 4 |
| 错误恢复 | 更健壮的错误恢复机制 | P1 | Phase 3 |
| 缓存机制 | LLM 响应缓存 | P2 | Phase 3 |

## 依赖管理

### 核心依赖

```toml
[project]
dependencies = [
    "anthropic>=0.18.0",
    "openai>=1.0.0",
    "aiohttp>=3.9.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "jsonschema>=4.0.0",
    "croniter>=2.0.0",
    "watchdog>=3.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
vector = [
    "chromadb>=0.4.0",
    "tiktoken>=0.5.0",
]
docker = [
    "docker>=6.0.0",
]
```

## 测试策略

### 测试金字塔

```
        ┌─────────┐
        │   E2E   │  ← 少量，关键流程
        │  Tests  │
        ├─────────┤
        │Integration│ ← 中等，组件交互
        │   Tests   │
        ├───────────┤
        │   Unit    │  ← 大量，函数级别
        │   Tests   │
        └───────────┘
```

### 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|-----------|
| core/ | 90% |
| llm/ | 85% |
| tools/ | 85% |
| memory/ | 80% |
| skills/ | 80% |
| triggers/ | 75% |
| security/ | 90% |

### CI/CD 流程

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run linting
        run: |
          ruff check src/
          black --check src/
          mypy src/

      - name: Run tests
        run: pytest --cov=src/harness tests/

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 发布计划

### 版本规划

| 版本 | 时间 | 内容 |
|------|------|------|
| 0.1.0 | Week 3 | MVP |
| 0.2.0 | Week 6 | 增强功能 |
| 0.3.0 | Week 10 | 高级特性 |
| 1.0.0 | Week 12 | 生产就绪 |

### 版本策略

- **0.x.x**: 开发版本，API 可能变更
- **1.x.x**: 稳定版本，遵循语义化版本
- **主版本号**: 不兼容的 API 变更
- **次版本号**: 向后兼容的功能新增
- **修订号**: 向后兼容的问题修复

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| LLM API 变更 | 高 | 抽象层隔离，快速适配 |
| 性能瓶颈 | 中 | 性能测试，优化关键路径 |
| 安全漏洞 | 高 | 安全审计，沙箱隔离 |
| 依赖冲突 | 低 | 版本锁定，可选依赖 |

## 后续规划

### v1.1+ 考虑的功能

- TypeScript SDK
- Rust 核心（性能优化）
- 更多 LLM 后端支持
- Web UI Dashboard
- 云端部署方案
- 更多预置技能
- 自学习增强
- 多模态支持

---

## MVP 范围定义

### ✅ MVP 必须有

| 功能 | 说明 |
|------|------|
| Agent Loop | 核心循环 + 并行工具 + 重试 + 熔断 |
| Tool System | 内置工具 + 权限控制 + 轻量沙箱 |
| Memory (基础) | File/SQLite 存储 + 滑动窗口 |
| Skills (基础) | 加载 + 激活 + 注入（无冲突解决） |
| 成本控制 | 会话级 Token 限制 |

### ⚠️ MVP 简化版

| 功能 | 简化方案 |
|------|----------|
| 上下文压缩 | 启发式摘要（不用 LLM） |
| 技能激活 | 最多 1 个（无冲突处理） |
| 触发器 | 只支持 Cron |

### ❌ MVP 不做

| 功能 | 延后原因 |
|------|----------|
| 向量检索 | 复杂度高，非核心 |
| 自动学习技能 | 实验性功能 |
| 多代理编排 | 需要先验证单代理 |
| Docker 沙箱 | 启动延迟高，依赖特权 |

### ✂️ 延后/移除的功能

| 功能 | 原计划 | 调整 | 原因 |
|------|--------|------|------|
| 多代理编排 | Phase 3 | v2.0 | 掩盖底层 Bug，需先验证单代理 |
| Skill 自学习 | Phase 2 | 独立插件 `harness-ml` | 不可控行为，实验性功能 |
| Webhook Trigger | MVP | Phase 2 | 应由宿主应用处理，SDK 不绑定路由 |
| FileWatch Trigger | Phase 2 | Phase 3 | 非核心，复杂度高 |

### 🚀 MVP 必须强化的功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 流式输出背压处理 | P0 | 定义 AsyncGenerator 缓冲行为 |
| 中断与恢复 | P0 | 长任务优雅中断 + 状态持久化 |
| Mock 测试工具链 | P0 | pytest 插件 |
| OpenTelemetry 集成 | P1 | 替代自研 LoopTracer |
| 增量 Token 计数 | P1 | 缓存历史 Token，避免重复计算 |

---

## 性能基准

### 目标指标

| 指标 | MVP 目标 | 生产目标 |
|------|----------|----------|
| 单次请求延迟 | < 5s | < 2s |
| 并发会话数 | 10 | 1000 |
| 会话最大消息数 | 100 | 10000 |
| 内存占用（空闲） | < 100MB | < 50MB |
| 内存占用（运行） | < 500MB | < 200MB |

### 测试场景

1. **短会话测试**: 10 条消息，验证基础流程
2. **长会话测试**: 1000 条消息，验证扩展性
3. **并发测试**: 100 并发请求，验证资源隔离
4. **成本测试**: 1000 次请求，验证成本追踪