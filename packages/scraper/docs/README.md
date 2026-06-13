# Harness Scraper 文档

> 通用信息抓取 Agent，基于 Harness SDK

## 目录

- [01-overview.md](./01-overview.md) - 项目概述与架构
- [02-agent-design.md](./02-agent-design.md) - IntelAgent 设计
- [03-tools.md](./03-tools.md) - 工具系统
- [04-skills.md](./04-skills.md) - 技能系统
- [05-cli.md](./05-cli.md) - CLI 使用指南
- [06-configuration.md](./06-configuration.md) - 配置说明

## 项目定位

构建一个**通用信息抓取 Agent**，通过技能注入支持不同领域的情报提取：

```
IntelAgent (通用) + Skill (领域知识) = 领域情报提取
```

### 与传统爬虫的区别

| 传统爬虫 | Harness Scraper |
|---------|-----------------|
| 固定流水线 | Agent 自主决策 |
| 规则过滤 | LLM 智能判断 |
| 单一领域 | 技能注入多领域 |
| 无记忆 | MEMORY.md 避免重复 |

## 快速预览

### 最简使用

```bash
# AI 情报抽取（默认）
harness-scraper

# 股票分析
harness-scraper --skill stock-analysis

# 自定义技能
harness-scraper --skill my-domain
```

### Python API

```python
from harness_scraper import IntelAgent, load_config

# 创建 Agent
agent = IntelAgent(
    load_config(),
    skill="ai-intelligence",  # 领域技能
)

# 运行
result = await agent.run("提取 AI 行业新范式")
```

## 设计原则

1. **通用性**: Agent 代码与领域知识分离
2. **技能驱动**: 领域判断标准封装为 Skill
3. **SDK 复用**: 使用 AgentHarness，不自建 LLM Client
4. **可扩展**: 新领域只需写 Skill 文件