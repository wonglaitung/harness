# 01 - 项目概述与架构

## 项目背景

### 问题陈述

传统信息抓取系统存在以下问题：

1. **流水线僵化**: 固定的抓取→过滤→输出流程，无法灵活调整
2. **领域限定**: 只能处理特定领域（如 AI、股票），扩展成本高
3. **规则维护**: 过滤规则需要持续维护，容易过时
4. **无记忆**: 不记录已处理的内容，容易重复抓取

### 解决方案

构建一个**基于 Agent 的通用信息抓取系统**：

- 使用 SDK 的 `AgentHarness` 作为核心引擎
- 工具封装数据源（RSS、HN、GitHub）
- 技能注入领域知识（判断标准、模板）
- MEMORY.md 记录已处理内容

## 架构总览

### 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER / CLI                                │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     IntelAgent                              │ │
│  │                                                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                 AgentHarness (SDK)                    │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │  │ │
│  │  │  │ Context │  │   LLM   │  │  Tool   │  │ Memory  │  │  │ │
│  │  │  │ Builder │  │  Call   │  │Executor │  │ System  │  │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                              ↓                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                   Tools (6)                           │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐               │  │ │
│  │  │  │fetch_rss│  │fetch_hn │  │fetch_url│               │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘               │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐               │  │ │
│  │  │  │show_hn  │  │github   │  │save_one │               │  │ │
│  │  │  │         │  │trending │  │ pager   │               │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘               │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                              ↓                              │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │                   Skill (packages/scraper/skills/)          │  │ │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐               │  │ │
│  │  │  │ai-intel │  │ stock   │  │ custom  │               │  │ │
│  │  │  │ ligence │  │ analysis│  │         │               │  │ │
│  │  │  └─────────┘  └─────────┘  └─────────┘               │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│         ↓                              ↓                         │
│  ┌─────────────────┐          ┌─────────────────┐               │
│  │  LLM PROVIDERS  │          │  OUTPUT         │               │
│  │  OpenAI/DeepSeek│          │ packages/scraper│               │
│  │  vLLM/Ollama    │          │ /output/        │               │
│  └─────────────────┘          └─────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件关系

```
                    ┌─────────────────┐
                    │   CLI / User    │
                    │   Input         │
                    └────────┬────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────┐
│                    IntelAgent                        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐         │
│  │ Config  │    │  Skill  │    │ Memory  │         │
│  │ Loader  │    │ Loader  │    │ Path    │         │
│  └────┬────┘    └────┬────┘    └────┬────┘         │
│       │              │              │               │
│       ↓              ↓              ↓               │
│  ┌─────────────────────────────────────────────┐   │
│  │              AgentHarness (SDK)              │   │
│  │  - System Prompt: BASE + Skill              │   │
│  │  - Tools: 8 intel + financial tools         │   │
│  │  - Memory: MEMORY.md (auto-managed)         │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                             │
                             ↓
                    ┌─────────────────┐
                    │   One-Pagers    │
                    │   + MEMORY.md   │
                    │   (auto-update) │
                    └─────────────────┘
```

## 核心概念

### Agent vs 流水线

**传统流水线**:

```
RSS → PreFilter → LLM Judge → GitHub README → One-Pager
 (固定顺序，无决策能力)
```

**Agent 模式**:

```
Agent 接收任务 → 自主决定抓取什么 → 自主判断价值 → 自主选择输出
 (灵活调整，智能决策)
```

### 技能注入

技能文件定义领域知识：

| Skill 内容 | 作用 |
|-----------|------|
| 判断标准 | 什么是高价值内容？什么是噪音？ |
| 已知实体 | 已成熟的项目/公司，避免重复 |
| 输出模板 | One-Pager 的格式要求 |
| 工作流程 | 领域特定的抓取策略 |

**示例**：

```markdown
# ai-intelligence.md

## 判断标准

✅ 新范式：新概念、新架构、新协议
❌ 噪音：成熟项目、教程、版本更新

## 已知成熟项目

vLLM, LangChain, Ollama, LLaMA, Mistral...
```

### 工具系统

所有数据源封装为 SDK Tools：

| 工具 | 数据源 | 用途 |
|------|--------|------|
| `fetch_rss` | RSS Feed | 官方博客、新闻源 |
| `fetch_hn` | Hacker News API | 高分帖子 (>150) |
| `fetch_show_hn` | Hacker News API | 早期项目 (>50) |
| `fetch_github_trending` | GitHub Trending | 热门开源项目 |
| `fetch_url` | GitHub/Jina Reader | 深度抓取 README |
| `save_one_pager` | 文件系统 | 保存 Markdown |

### 记忆系统

MEMORY.md 记录已处理内容，**由 SaveOnePagerTool 自动维护**：

```markdown
# 已提取的情报项目

## 2026-06-13 提取

### 新范式/工具
- **agent-skills-anthropic** - Anthropic Skills 规范
- **headroom** - LLM 上下文压缩
...
```

**自动管理机制**：
- 每次保存 One-Pager 时自动更新 MEMORY.md
- 超过 30 天的条目自动归档到 `archive/MEMORY-YYYY-MM.md`
- SDK 加载 MEMORY.md 注入系统提示，避免重复提取

## 数据流

### Agent 执行流程

```
用户输入: "运行情报抽取"
    │
    ↓
┌─────────────┐
│ IntelAgent  │ 加载 Config + Skill + Memory
│ __init__    │
└─────┬───────┘
      │
      ↓
┌─────────────┐
│ AgentHarness│ 构建完整上下文
│ run()       │
└─────┬───────┘
      │
      ↓
┌─────────────────────────────────────────────┐
│              Agent Loop                      │
│                                              │
│  1. LLM 接收任务                             │
│  2. LLM 决定调用 fetch_rss                   │
│  3. Tool 执行，返回文章列表                   │
│  4. LLM 判断哪些是新范式                      │
│  5. LLM 决定调用 fetch_url                   │
│  6. Tool 执行，返回 README                    │
│  7. LLM 决定调用 save_one_pager              │
│  8. Tool 执行，保存 Markdown                  │
│  9. 循环继续或结束                            │
│                                              │
└─────────────────────────────────────────────┘
      │
      ↓
┌─────────────┐
│ LoopResult  │ 返回 Agent 输出
└─────────────┘
```

## 目录结构

```
packages/scraper/
├── src/harness_scraper/
│   ├── __init__.py          # 导出 IntelAgent, Tools
│   ├── __main__.py          # CLI 入口
│   ├── agent.py             # IntelAgent 类
│   ├── cli.py               # 命令行接口
│   ├── config.py            # 配置加载
│   ├── models.py            # 配置模型 (LLMConfig, ScraperConfig)
│   └── tools/               # SDK Tools
│       ├── __init__.py
│       ├── fetch_rss.py
│       ├── fetch_hn.py      # FetchHNTool + FetchShowHNTool
│       ├── fetch_github_trending.py
│       ├── fetch_url.py
│       ├── save_one_pager.py  # 自动更新 MEMORY.md
│       ├── fetch_hkex.py      # 港股异动监控
│       └── fetch_financial_news.py  # 财经快讯
├── skills/                  # 技能文件（版本管理）
│   ├── ai-intelligence.md
│   └── hk-stocks-alpha.md
├── output/                  # 输出目录（版本管理）
│   ├── MEMORY.md            # 已处理项目（最近 30 天）
│   ├── archive/             # 月度归档
│   └── YYYY-MM-DD/          # 日期目录
│       ├── ai/              # AI 情报
│       └── stocks/          # 股票分析
├── docs/
│   ├── README.md            # 文档索引
│   ├── 01-overview.md       # 本文件
│   ├── 02-agent-design.md   # IntelAgent 设计
│   ├── 03-tools.md          # 工具详解
│   ├── 04-skills.md         # 技能系统
│   ├── 05-cli.md            # CLI 使用
│   └── 06-configuration.md  # 配置说明
├── pyproject.toml
└── README.md
```

## 与 SDK 的关系

Scraper 是 SDK 的**应用实例**：

| SDK 提供 | Scraper 使用 |
|---------|-------------|
| `AgentHarness` | IntelAgent 的核心引擎 |
| `Tool` 基类 | 所有工具的父类 |
| `ToolContext` | 工具执行上下文 |
| `ToolResult` | 工具返回结果 |
| Memory System | MEMORY.md 避免重复 |
| Skills System | 领域技能注入 |

Scraper **不重复实现** SDK 已有的功能：
- 不自建 LLM Client（使用 SDK 的 OpenAIClient）
- 不自建 Agent Loop（使用 SDK 的 AgentLoop）
- 不自建 Memory（使用 SDK 的 MemoryManager）

## 设计决策

### 为什么选择 Agent 模式？

| 优势 | 说明 |
|------|------|
| **灵活决策** | Agent 可以根据内容调整策略，不必固定流水线 |
| **多轮对话** | 用户可以说"这次多关注前端"，Agent 会调整 |
| **智能过滤** | LLM 判断而非规则，更准确、更易维护 |
| **可扩展** | 新领域只需 Skill 文件，无需改代码 |

### 为什么使用技能注入？

| 优势 | 说明 |
|------|------|
| **代码复用** | 同一个 Agent 支持多领域 |
| **知识分离** | 判断标准独立于代码，易于更新 |
| **快速扩展** | 新领域只需写 Markdown Skill |
| **用户定制** | 用户可以创建自己的 Skill |

### 为什么保留 MEMORY.md？

| 优势 | 说明 |
|------|------|
| **避免重复** | 记录已处理项目 |
| **人工编辑** | 用户可以手动添加已知项目 |
| **持久化** | 跨会话保持记忆 |
| **可追溯** | 查看历史提取记录 |

## 参考资源

- [Harness SDK 文档](../../sdk/docs/)
- [plan.md](./plan.md) - 原始设计计划
- [AgentHarness 架构](../../sdk/docs/02-agent-loop.md)