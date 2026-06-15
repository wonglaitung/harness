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
| `save_one_pager` | 保存情报一页纸（自动记录到 MEMORY.md） | domain 参数见下文分类 |

---

## 新范式判断标准

**必须同时满足至少 2 点：**

| 维度 | 标准 | 检查方式 |
|------|------|---------|
| **概念创新** | 引入新术语/框架，被独立资源明确命名 | README 是否定义新概念词 |
| **采用广度** | 被 2+ 个独立项目/组织参考/集成 | GitHub 搜索引用数 |
| **时间新鲜** | 首次公开发布 < 6 个月 | 注：首发 ≠ trending 时间 |
| **社区共鸣** | HN ≥100 分 + ≥20 评论，或 GitHub ≥1k stars | 相对于项目类型 |

### ✅ 典型新范式示例

| 项目 | 满足维度 | 判断 |
|------|---------|------|
| MCP 协议 | 概念创新 + 采用广度 + 时间新鲜 | ✅ 新范式 |
| taste-skill | 概念创新 + 社区共鸣（HN 热议） | ✅ 新范式 |
| browser-use | 新工具类别 + 采用广度 + 社区共鸣 | ✅ 新范式 |

### ❌ 非新范式示例

| 项目 | 未满足维度 | 判断 |
|------|---------|------|
| vLLM 0.5.0 | 无概念创新（版本升级） | ❌ 成熟项目更新 |
| "如何用 LangChain" | 无概念创新（教程） | ❌ 最佳实践 |
| AI 邮件助手 | 无概念创新（纯应用） | ❌ 应用层产品 |

---

## 自动排除规则

**遇到以下情况，直接跳过（无需深入评估）：**

### 等级 1：明确排除

| 规则 | 原因 |
|------|------|
| Stars > 5k 且首发 > 12 个月 | 成熟项目 |
| 主标签含 `maintenance` / `archived` | 项目终止 |
| Issue/PR 活跃度 < 1 个/月 | 项目停滞 |

### 等级 2：条件排除

| 规则 | 处理 |
|------|------|
| 纯文章/教程 | 跳过（除非首次系统总结新概念） |
| 版本号升级 | 跳过（除非涉及架构重设计） |
| 非英文/中文资源 | 先检查是否有英文版本 |

### 等级 3：深入评估

| 规则 | 处理 |
|------|------|
| < 1k stars 但提及度高 | 深入评估（可能是早期新范式） |
| 新发布但涉及新类别工具 | 深入评估（需验证概念创新） |

---

## 已知成熟项目（直接跳过）

**推理框架**：vLLM, TGI, llama.cpp, Ollama
**应用框架**：LangChain, LlamaIndex, Haystack, Semantic Kernel
**模型**：LLaMA, Mistral, Qwen, ChatGLM
**工具**：Transformers, PyTorch, TensorFlow
**向量数据库**：Pinecone, Weaviate, Qdrant, Milvus

---

## 工作流程

### 第一步：信息收集

1. `fetch_rss` — 官方博客（OpenAI, Anthropic, Google AI, Hugging Face）
2. `fetch_hn` — 高分帖子（min_points=150）
3. `fetch_show_hn` — 早期项目（min_points=50）
4. `fetch_github_trending` — Python/TypeScript trending

### 第二步：初筛

**应用自动排除规则：**
- 符合"等级 1" → 停止
- 符合"等级 2" → 标记"成熟项目"，可选继续观察
- 进入"等级 3" → 继续深度评估

### 第三步：深度评估

**使用 `fetch_url` 获取：**
- README：是否定义了新概念？
- CHANGELOG：最近活动时间
- GitHub Issues：社区讨论热度

### 第四步：范式认证

**检查引用关系（可选）：**
- GitHub 搜索 "import XXX" 或 "from XXX"
- 其他项目 README 中出现次数
- Twitter/HN 独立讨论数

### 第五步：记录决策

使用 `save_one_pager` 保存，必须记录：
- 满足判断标准中的哪几点？
- 为什么认为这是新范式？

---

## 情报分类

**domain 参数细分：**

| domain 值 | 适用范围 | 示例 |
|-----------|---------|------|
| `ai.models` | 模型架构、训练方法 | MoE, Hermes |
| `ai.frameworks` | 应用框架、SDK | LangChain（新概念时） |
| `ai.evals` | 评估框架、benchmark | Harness eval |
| `ai.agents` | Agent 范式、工作流 | AutoGen, browser-use |
| `ai.infra` | 推理框架、部署工具 | llama.cpp（新特性时） |
| `ai.protocols` | 新协议、新标准 | MCP, GGUF |
| `stocks` | 金融/股票相关 | 港股、回购 |

---

## One-Pager 模板

```markdown
# [项目名称]

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆/5 | [具体理由] |
| 采用广度 | ☆☆/5 | 被 X 个项目采用 |
| 时间新鲜 | ☆☆☆☆/5 | 发布于 [日期] |
| 社区热度 | ☆☆☆/5 | HN [分数]，GitHub [讨论] |
| **总体判断** | ✅ / ⚠️ / ❌ | **新范式 / 观察中 / 否** |

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

## 采用案例
- [项目 A]：用途、效果
- [项目 B]：用途、效果（如有）

## 风险/局限
- [已知问题]
- [适用范围边界]

## 核心线索
- GitHub：[URL]
- 首发来源：[来源]
- 发布时间：[日期]
- 当前状态：活跃 / 成熟 / 试验中
```

---

## 推荐 RSS 源

### 官方渠道
- OpenAI Blog：https://openai.com/blog/rss.xml
- Anthropic Research：https://anthropic.com/research
- Google AI Blog：https://blog.google/technology/ai/rss
- Meta AI Research：https://meta.ai/blog

### 行业媒体
- Papers with Code：https://paperswithcode.com/lib
- Hugging Face Blog：https://huggingface.co/blog/feed.xml

### 社区聚集地
- Hacker News：https://news.ycombinator.com/rss
- Product Hunt（AI）：https://producthunt.com/topics/ai

---

## 输出要求

1. **语言**：One-Pager 必须使用中文，无论来源语言
2. **简洁**：每个字段 2-3 句话
3. **可操作**：提供 GitHub 链接以便深入探索
4. **评分必填**：新范式评分表必须填写，作为判断依据

---

## 注意事项

- **宁缺毋滥**：保持高标准，不满足 2 个维度就跳过
- **首发时间**：关注"首次提出时间"，而非 GitHub trending 时间
- **热度 ≠ 创新**：高热度成熟项目 ≠ 新技术
- **记录排除**：可选记录被排除项目及原因，防止重复评估