# 10 - 与 Hermes/OpenClaw 对比

## 概述

本文档对比 Harness 项目与 Hermes Agent 和 OpenClaw 的设计差异，明确本项目的定位和独特价值。

## 竞品概览

### Hermes Agent

- **开发方**: Nous Research
- **定位**: 自学习个人运行时
- **特点**:
  - 自动从重复模式生成技能
  - 搜索历史对话
  - 多平台接入（Telegram、Discord 等）
  - Web UI Dashboard
- **Stars**: 100,000+ (GitHub)
- **License**: MIT

### OpenClaw

- **开发方**: OpenAI 社区
- **定位**: 多代理控制平面
- **特点**:
  - 持久代理团队
  - 多渠道路由
  - ClawHub 技能市场
  - TaskFlow 工作流
- **Stars**: 极高
- **License**: Open Source

### 本 Harness

- **定位**: 可内嵌 SDK
- **特点**:
  - 嵌入用户系统
  - 最小依赖
  - 完全控制数据
  - 高度定制化

## 详细对比

### 架构对比

| 特性 | Hermes | OpenClaw | 本 Harness |
|------|--------|----------|------------|
| **架构模式** | 独立服务 | 独立服务 | **SDK 库** |
| **部署方式** | 独立进程/容器 | 独立进程/容器 | **嵌入应用** |
| **主要入口** | CLI + Gateway | CLI + Dashboard | **Python API** |
| **运行时** | Python + Gateway | Python + Runtime | **纯 Python** |

```
Hermes/OpenClaw 架构:
┌─────────────────────────────────────────────────────┐
│                   独立服务                            │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐       │
│  │   CLI     │  │  Gateway  │  │ Dashboard │       │
│  └───────────┘  └───────────┘  └───────────┘       │
│                        ↓                             │
│  ┌───────────────────────────────────────────┐     │
│  │              Agent Runtime                 │     │
│  └───────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
            ↑ 外部 API调用 ↑

本 Harness 架构:
┌─────────────────────────────────────────────────────┐
│                   用户应用                            │
│  ┌───────────────────────────────────────────┐     │
│  │           业务代码                          │     │
│  │  ┌───────────────────────────────────┐   │     │
│  │  │         Harness SDK (嵌入)          │   │     │
│  │  │  ┌─────────┐ ┌─────────┐          │   │     │
│  │  │  │ Agent   │ │ Memory  │          │   │     │
│  │  │  │ Loop    │ │ System  │          │   │     │
│  │  │  └─────────┘ └─────────┘          │   │     │
│  │  └───────────────────────────────────┘   │     │
│  └───────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────┘
            无外部依赖，纯代码调用
```

### 功能对比

| 功能类别 | Hermes | OpenClaw | 本 Harness |
|----------|--------|----------|------------|
| **代理循环** | ✓ | ✓ | ✓ |
| **工具系统** | ✓ (丰富) | ✓ (丰富) | ✓ (可扩展) |
| **记忆系统** | ✓ (搜索优先) | ✓ (层级丰富) | ✓ (可配置后端) |
| **技能系统** | ✓ (自学习) | ✓ (静态+市场) | ✓ (文件+可扩展) |
| **触发器** | ✓ (cron+gateway) | ✓ (TaskFlow) | ✓ (cron+webhook+事件) |
| **多代理** | 父子模式 | 团队模式 | 支持 (可扩展) |
| **多渠道** | ✓ (22+) | ✓ (原生) | 可扩展 |
| **MCP 支持** | ✓ | ✓ | ✓ |
| **自学习** | ✓ | 部分 | 可选 |
| **市场/生态** | 稀疏 | ClawHub | 用户自建 |
| **Web UI** | ✓ | ✓ | 不含 (用户自建) |

### 内嵌能力对比

| 内嵌场景 | Hermes | OpenClaw | 本 Harness |
|----------|--------|----------|------------|
| Python 应用 | 需要外部调用 | 需要外部调用 | **直接 import** |
| FastAPI 集成 | 需要网关 | 需要网关 | **直接集成** |
| Celery 任务 | 需要外部触发 | 需要外部触发 | **直接调用** |
| 数据处理脚本 | 需要外部进程 | 需要外部进程 | **同进程执行** |
| 测试环境 | 需要启动服务 | 需要启动服务 | **Mock 内嵌** |

```python
# Hermes/OpenClaw 使用方式（需要外部服务）
import requests

response = requests.post(
    "http://localhost:8080/chat",
    json={"message": "分析代码"}
)

# 本 Harness 使用方式（直接嵌入）
from harness import AgentHarness

agent = AgentHarness()
result = await agent.run("分析代码")
print(result.content)
```

### 数据控制对比

| 数据类型 | Hermes | OpenClaw | 本 Harness |
|----------|--------|----------|------------|
| 会话数据 | Gateway 存储 | Runtime 存储 | **用户控制** |
| 记忆文件 | ~/.hermes | ~/.claw | **可配置路径** |
| 技能文件 | ~/.hermes/skills | ClawHub + local | **用户目录** |
| 日志/审计 | Gateway logs | Runtime logs | **用户控制** |
| API 密钥 | Gateway 管理 | Dashboard 管理 | **用户管理** |

### 性能对比

| 维度 | Hermes | OpenClaw | 本 Harness |
|------|--------|----------|------------|
| **启动延迟** | 需启动服务 | 启动服务 | **零延迟** |
| **调用开销** | HTTP/API | HTTP/API | **函数调用** |
| **资源占用** | 独立进程 | 独立进程 | **共享进程** |
| **并发处理** | Gateway 处理 | Runtime 处理 | **用户控制** |

### 定制化对比

| 定制维度 | Hermes | OpenClaw | 本 Harness |
|----------|--------|----------|------------|
| 工具扩展 | Skills + MCP | Skills + MCP | **Python 函数** |
| 记忆后端 | 固定 | 固定 | **可选多种** |
| LLM 后端 | 多种支持 | 多种支持 | **插件式** |
| 触发器类型 | Gateway 定义 | TaskFlow 定义 | **可自定义** |
| 输出通道 | Gateway 路由 | Dashboard 定义 | **用户控制** |
| 权限模型 | Gateway 配置 | Runtime 配置 | **代码级控制** |

## 本 Harness 的独特价值

### 1. 零外部依赖

```python
# 无需启动任何外部服务
agent = AgentHarness()
result = await agent.run("任务")
# 完成，无需任何外部进程
```

### 2. 完全数据控制

```python
# 数据完全在用户控制下
agent = AgentHarness(
    memory_dir="/secure/location",
    audit_log_dir="/compliant/logs"
)
# 数据不经过任何外部系统
```

### 3. 代码级定制

```python
# 可以深度定制每个组件
agent = AgentHarness()

# 自定义工具
@agent.tool()
def my_custom_tool(data: dict) -> str:
    return process_data(data)

# 自定义记忆后端
agent.memory = MyCustomMemoryStore()

# 自定义权限检查
agent.permissions = MyPermissionSet()
```

### 4. 测试友好

```python
# 内嵌测试，无需启动服务
from harness.testing import MockHarness

agent = MockHarness()
agent.expect("分析代码").respond("分析结果")

result = await agent.run("分析代码")
assert result.content == "分析结果"
```

### 5. 部署简单

```python
# 随应用部署，无需额外步骤
# 在现有应用中添加：
from harness import AgentHarness

agent = AgentHarness.from_config("harness.yaml")

# 集成到 FastAPI
@app.post("/ai")
async def ai_endpoint(message: str):
    return await agent.run(message)
```

## 适用场景对比

| 场景 | 推荐 |
|------|------|
| **个人自动化** | Hermes (自学习) |
| **多渠道代理系统** | OpenClaw (多渠道原生) |
| **需要技能市场** | OpenClaw (ClawHub) |
| **嵌入现有应用** | **本 Harness** |
| **数据敏感场景** | **本 Harness** |
| **深度定制需求** | **本 Harness** |
| **测试环境集成** | **本 Harness** |
| **轻量部署** | **本 Harness** |

## 取舍说明

### 本 Harness 的取舍

**选择舍弃的功能**:

1. **Web UI Dashboard**: 用户可自行开发或集成现有 UI
2. **技能市场**: 用户自建技能库更灵活
3. **Gateway 多渠道**: 用户按需集成
4. **自学习**: 可选功能，Phase 3+ 实现

**选择保留的核心**:

1. **Agent Loop**: 核心功能
2. **工具系统**: 必需能力
3. **记忆系统**: 持久化必需
4. **技能系统**: 行为指导必需
5. **触发器**: 自主运行必需
6. **安全系统**: 内嵌必需

### 学习借鉴

**从 Hermes 学习**:

- 自学习机制设计
- 搜索历史对话的检索策略
- 技能生成模式

**从 OpenClaw 学习**:

- TaskFlow 工作流概念
- 持久代理团队设计
- 多代理协调模式

**改进方向**:

- 内嵌优先设计
- 更简洁的 API
- 更灵活的组件替换
- 更完善的安全模型

## 互操作性

### 共享格式

本 Harness 支持与 Hermes/OpenClaw 共享的部分：

```python
# 共享技能文件格式 (.md)
# 可以直接加载 Hermes/OpenClaw 的技能文件
agent.load_skill("hermes_skill.md")

# 共享记忆文件格式 (MEMORY.md)
# 可以读取相同的记忆文件

# 共享 AGENTS.md 格式
# 项目上下文文件兼容
```

### 迁移路径

```python
# 从 Hermes 迁移
# Hermes 的 ~/.hermes/skills 可直接加载
agent = AgentHarness()
agent.skills.add_skill_dir("~/.hermes/skills")

# 从 OpenClaw 迁移
# OpenClaw 的 ClawHub 技能可下载后加载
agent.load_skill("downloaded_from_clawhub.md")
```

## 总结

本 Harness 的定位是 **"可内嵌的 AI Agent SDK"**，而非独立服务：

- **Hermes**: 自学习的个人代理运行时，适合自动化场景
- **OpenClaw**: 多代理控制平面，适合复杂代理系统
- **本 Harness**: 内嵌 SDK，适合集成到用户自己的系统

三者互补而非替代，用户可以根据需求选择：
- 需要独立服务 → Hermes/OpenClaw
- 需要内嵌集成 → 本 Harness
- 可以混合使用 → 共享技能/记忆格式