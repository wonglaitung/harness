# AI Intelligence Extraction Skill

Extract AI industry intelligence from web sources, identifying paradigm-shifting technologies, tools, and concepts.

## Domain Focus

AI/ML industry: models, frameworks, tools, protocols, evaluation systems.

## Judgment Criteria

### Three Types of New Paradigms

**Type A: New Paradigms/Buzzwords**
- Community-formed new concept words
- Examples: taste-skill (AI frontend aesthetics), vibe-coding, prompt-engineering

**Type B: New Model Architectures/Fine-tuning Approaches**
- New model architectures, training methods, inference frameworks
- Examples: Hermes series, Agent runtime, MoE architectures

**Type C: New Evaluation/Scaffold Tools**
- Automated evaluation frameworks, new protocols, new standards
- Examples: MCP (Model Context Protocol), Harness evaluation framework, GGUF

### ✅ Should Mark as New Paradigm

| Situation | Example | Reason |
|-----------|---------|--------|
| New project (< 3 months) | karpathy/autoresearch | Just released, defines new automation paradigm |
| New concept/buzzword | taste-skill, vibe-coding | New community term, represents cognitive upgrade |
| New protocol/standard | MCP, GGUF | Defines new interoperability method |
| New tool category | browser-use (AI operating browser) | Opens new Agent capability boundary |

### ❌ Should NOT Mark as New Paradigm

| Situation | Example | Reason |
|-----------|---------|--------|
| Mature project | vLLM, LangChain, Ollama | Exists > 3 months, widely used |
| Pure tutorial/best practices | "How to build with LangChain" | No new concept, just usage guide |
| Incremental update | "vLLM 0.5.0 released" | Version upgrade, not paradigm shift |
| Pure application | "AI email assistant" | Using existing tech for specific app, no innovation |

## Known Mature Projects (Skip These)

**Inference Frameworks**: vLLM, TGI, llama.cpp, Ollama
**Application Frameworks**: LangChain, LlamaIndex, Haystack, Semantic Kernel
**Models**: LLaMA, Mistral, Qwen, ChatGLM
**Tools**: Transformers, PyTorch, TensorFlow
**Vector Databases**: Pinecone, Weaviate, Qdrant, Milvus

## Workflow

1. Use `fetch_rss` for official blogs (OpenAI, Anthropic, Google AI, Hugging Face)
2. Use `fetch_hn` for high-score posts (min_points=150)
3. Use `fetch_show_hn` for early projects (min_points=50)
4. Use `fetch_github_trending` for Python/TypeScript trending
5. For promising items, use `fetch_url` to get README/full content
6. Use `save_one_pager` to save intelligence

## One-Pager Template

```markdown
# [Project Name]

## 技术定义 (What)
[Plain language explanation]

## 行业痛点 (Why)
[What problem does it solve]

## 旧范式 vs 新范式
- **旧做法**：[Old approach]
- **新做法**：[New approach]

## 生产力影响 (How)
[Actual value for developers]

## 采用成本
[Time, money, learning curve]

## 核心线索
- GitHub：[URL]
- 来源：[Source]
- 发布时间：[Date]
```

## Output Requirements

1. **Language**: One-Pagers must use Chinese, regardless of source language
2. **Concise**: Each field 2-3 sentences
3. **Actionable**: Provide GitHub link for further exploration
4. **Domain Selection**:
   - AI/ML content: `save_one_pager(... domain="ai")` (default)
   - Stock/financial content: `save_one_pager(... domain="stocks")`
   - If the content is about stocks, buybacks, financial news, ALWAYS use `domain="stocks"`

## Notes

- Better to miss than over-report, keep high standards
- Focus on "first proposed time", not GitHub trending time
- Distinguish "popularity" from "innovation" — high popularity ≠ new technology