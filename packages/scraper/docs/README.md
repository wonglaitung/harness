# Harness Scraper 文档

> 通用信息抓取 Agent，基于 Harness SDK

## 目录

- [01-overview.md](./01-overview.md) - 项目概述与架构
- [02-agent-design.md](./02-agent-design.md) - Agent 设计（IntelAgent + GoalAgent）
- [03-tools.md](./03-tools.md) - 工具系统
- [04-skills.md](./04-skills.md) - 技能系统
- [05-cli.md](./05-cli.md) - CLI 使用指南
- [06-configuration.md](./06-configuration.md) - 配置说明

## 项目定位

构建一个**通用信息抓取 Agent**，通过技能注入支持不同领域的情报提取：

```
Agent (通用) + Skill (领域知识) = 领域情报提取
```

### 两种 Agent 模式

| 模式 | Agent | 适用场景 |
|------|-------|----------|
| 目标驱动（推荐） | `GoalAgent` | 复杂任务，自主迭代直到目标达成 |
| 单次执行 | `IntelAgent` | 简单任务，一次性提取 |

### 与传统爬虫的区别

| 传统爬虫 | Harness Scraper |
|---------|-----------------|
| 固定流水线 | Agent 自主决策 |
| 规则过滤 | LLM 智能判断 |
| 单一领域 | 技能注入多领域 |
| 无记忆 | MEMORY.md 避免重复 |
| 无验证 | GoalAgent 自动验证目标达成 |

## 快速预览

### 最简使用

```bash
# AI 情报抽取（默认，目标驱动）
harness-scraper

# 港股异动监控
harness-scraper --skill hk-stocks-alpha

# 自定义目标
harness-scraper goal "提取 5 个 MCP 相关项目"

# 单次执行模式
harness-scraper agent "只关注 Rust 项目"
```

### Python API

```python
from harness_scraper import GoalAgent, IntelAgent
from harness_scraper.config import load_config
from harness import GoalStatus

# 方式 1：目标驱动（推荐）
agent = GoalAgent(load_config(), skill="ai-intelligence")
result = await agent.run_goal(
    goal="提取 3 个 AI 行业新范式项目",
    max_iterations=20,
)

if result.status == GoalStatus.ACHIEVED:
    print(f"✅ 目标达成，共 {result.total_iterations} 轮迭代")

# 方式 2：单次执行
agent = IntelAgent(load_config(), skill="ai-intelligence")
result = await agent.run("提取 AI 情报")
```

## 设计原则

1. **通用性**: Agent 代码与领域知识分离
2. **技能驱动**: 领域判断标准封装为 Skill
3. **SDK 复用**: 使用 AgentHarness，不自建 LLM Client
4. **可扩展**: 新领域只需写 Skill 文件