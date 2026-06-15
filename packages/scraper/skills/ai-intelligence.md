# AI 情报提取技能

从网络资源中提取 AI 行业情报，识别范式级技术、工具和概念。

## 领域聚焦

AI/ML 行业：模型、框架、工具、协议、评估系统。

## 工具清单

### AI 情报工具

| 工具 | 用途 | 建议使用场景 |
|-----|------|-------------|
| `fetch_rss` | 抓取 RSS 文章 | 获取官方博客、新闻源 |
| `fetch_hn` | 抓取 HN 高分帖子 | 发现已被社区验证的热门讨论 |
| `fetch_show_hn` | 抓取 Show HN 早期项目 | 发现刚发布的早期新项目 |
| `fetch_github_trending` | 抓取 GitHub Trending | 发现正在爆发的开源项目 |
| `fetch_url` | 深度抓取 URL 内容 | 获取 README、技术文章全文 |

### 输出工具

| 工具 | 用途 | 参数说明 |
|-----|------|---------|
| `save_one_pager` | 保存情报一页纸（自动记录到 MEMORY.md） | domain="ai"（默认） |

## 判断标准

### 三类新范式

**类型 A：新范式/新概念**
- 社区形成的新概念词
- 示例：taste-skill（AI 前端美学）、vibe-coding、prompt-engineering

**类型 B：新模型架构/微调方法**
- 新模型架构、训练方法、推理框架
- 示例：Hermes 系列、Agent runtime、MoE 架构

**类型 C：新评估/脚手架工具**
- 自动化评估框架、新协议、新标准
- 示例：MCP（Model Context Protocol）、Harness 评估框架、GGUF

### ✅ 应标记为新范式

| 情况 | 示例 | 原因 |
|------|------|------|
| 新项目（< 3 个月） | karpathy/autoresearch | 刚发布，定义新的自动化范式 |
| 新概念/新词 | taste-skill, vibe-coding | 新社区术语，代表认知升级 |
| 新协议/新标准 | MCP, GGUF | 定义新的互操作方式 |
| 新工具类别 | browser-use（AI 操作浏览器） | 开拓新的 Agent 能力边界 |

### ❌ 不应标记为新范式

| 情况 | 示例 | 原因 |
|------|------|------|
| 成熟项目 | vLLM, LangChain, Ollama | 存在超过 3 个月，广泛使用 |
| 纯教程/最佳实践 | "如何用 LangChain 构建" | 无新概念，只是使用指南 |
| 增量更新 | "vLLM 0.5.0 发布" | 版本升级，非范式转变 |
| 纯应用 | "AI 邮件助手" | 用现有技术解决特定应用，无创新 |

## 已知成熟项目（跳过）

**推理框架**：vLLM, TGI, llama.cpp, Ollama
**应用框架**：LangChain, LlamaIndex, Haystack, Semantic Kernel
**模型**：LLaMA, Mistral, Qwen, ChatGLM
**工具**：Transformers, PyTorch, TensorFlow
**向量数据库**：Pinecone, Weaviate, Qdrant, Milvus

## 工作流程

1. 使用 `fetch_rss` 获取官方博客（OpenAI, Anthropic, Google AI, Hugging Face）
2. 使用 `fetch_hn` 获取高分帖子（min_points=150）
3. 使用 `fetch_show_hn` 获取早期项目（min_points=50）
4. 使用 `fetch_github_trending` 获取 Python/TypeScript trending
5. 对有潜力的项目，使用 `fetch_url` 获取 README/全文
6. 使用 `save_one_pager` 保存情报

## One-Pager 模板

```markdown
# [项目名称]

## 技术定义 (What)
[通俗易懂的解释]

## 行业痛点 (Why)
[解决什么问题]

## 旧范式 vs 新范式
- **旧做法**：[旧方法]
- **新做法**：[新方法]

## 生产力影响 (How)
[对开发者的实际价值]

## 采用成本
[时间、金钱、学习曲线]

## 核心线索
- GitHub：[URL]
- 来源：[来源]
- 发布时间：[日期]
```

## 输出要求

1. **语言**：One-Pager 必须使用中文，无论来源语言
2. **简洁**：每个字段 2-3 句话
3. **可操作**：提供 GitHub 链接以便深入探索
4. **领域选择**：
   - AI/ML 内容：`save_one_pager(... domain="ai")`（默认）
   - 股票/金融内容：`save_one_pager(... domain="stocks")`
   - 如果内容涉及股票、回购、财经新闻，必须使用 `domain="stocks"`

## 注意事项

- 宁缺毋滥，保持高标准
- 关注"首次提出时间"，而非 GitHub trending 时间
- 区分"热度"与"创新"——高热度 ≠ 新技术
