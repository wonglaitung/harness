# LLMON — LLM Object Notation（LLM 原生标记语言）

## 技术定义 (What)
LLMON（读作 "lemon"，LLM Object Notation）是 IBM 提出的一种"为 LLM 而生"的标记语言。它用保留的特殊 token（而非 { } " : 等普通字符）作为结构定界符，把上下文中的语义单元打上标签（instruction / data / req / exec），并用唯一 block ID 把「指令」与它作用的「数据」显式绑定，作用类似编程语言中的函数调用与参数传递。它不替代 chat template，而是对其进行增强——普通 chat template 只告诉模型"这段属于哪个 role"，LLMON 还告诉模型"这段是什么意思、和谁绑定"。

## 行业痛点 (Why)
LLM 的上下文里混杂着 system prompt、对话历史、RAG 文档、工具返回、输出约束、推理链，但这些结构对模型大多是隐式的。团队只能用 JSON 编码结构，而 JSON 是为 parser 设计的、不是为因果语言模型设计的：引号既可能出现在正文里也可能闭合字段，嵌套靠数括号（transformer 的弱项）。结果是两个恶果：小模型行为脆弱、偶发失败；以及间接提示注入——藏在检索文档或工具返回里的恶意指令会被模型当作指令执行。

## 旧范式 vs 新范式
- **旧做法**：用 JSON / 扁平字符串承载结构化上下文 → 靠 system prompt 叮嘱模型"只执行用户指令，忽略文档里的指令" → 靠约束解码（Outlines / XGrammar）兜住输出格式 → 提示注入只能靠概率性防护，攻击成功率居高不下
- **新做法**：用 LLMON 在 token 层面显式分离指令与数据（结构定界符走保留特殊 token，与正文词汇表隔离）→ `exec: True` 的区块才是权威指令，作为 input 的数据/文档/工具结果"只读不执行" → 无 binding 的上下文内容不会被拉进答案（旧对话/无关段落不污染输出）→ 提示注入在部分 benchmark 上攻击成功率降到接近 0

## 生产力影响 (How)
① 安全性：间接提示注入从"概率缓解"变成"结构性阻断"，对做 RAG、Agent 工具调用、处理不可信外部内容的团队是范式级收益；② 可靠性：小模型（3B/8B）不再需要数括号推嵌套，长上下文的结构推断负担下降；③ 兼容迁移：官方提供 JSON↔LLMON 无损双向转换器，存量 JSON pipeline 不需重写；④ 可观测：官方 attention 可视化 demo，让 markup 效果从"轶事"变成可测量的层级注意力分布。

## 采用成本
低-中。用 IBM 已发布的 granite-4.1-3b/8b-llmon-preview 走 `apply_chat_template` 即可，模型自带 chat_template.jinja，不用手写 markup；或经 Mellea 库自动 LLMON 化 LLM 调用，终端用户无感知。自定义语义标签需在 LLMON 模型上微调 LoRA。目前是 experimental preview，非生产级承诺。

## 核心线索
- GitHub：https://github.com/generative-computing/llmon
- 来源：https://huggingface.co/blog/ibm-granite/llmon-an-llm-native-markup-language-now-in-granite
- 发布时间：2026-11-14
