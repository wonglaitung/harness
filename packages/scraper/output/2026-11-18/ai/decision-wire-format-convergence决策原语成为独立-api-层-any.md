# Decision Wire-Format Convergence（决策原语成为独立 API 层 + Any-slot 抽象）

## 技术定义 (What)
「决策」正在从"用 LLM 生成文本再解析"中剥离，成为一个独立的 API 语义层：只有三类原语——noul（是/否概率）、choice（多选一）、score（有序量表打分），返回值是带概率与置信度的类型化结果，而不是文本。AnyDecisionModel 是 Swift 侧的统一客户端：同一 `DecisionSession` API 下可切换六种后端（Jev / Ollama / System One 自定义服务 / Gemini Decisions / 本地 MLX、Core AI、llama.cpp 的 next-token scoring / 模型内置 decision head）。这种「一个槽位、多种实现」的抽象（Any-slot）此前已被 AnyLanguageModel、AnySpeechRecognizer 用于语言与语音。

## 行业痛点 (Why)
在客服分流、合规判定、评审打分、意图识别等场景里，团队被迫用大模型生成自由文本再解析，付出三类成本：解析失败与格式漂移、无法获得校准置信度、token 与延迟开销远高于所需。而各供应商给出的决策接口格式互不兼容，切换成本又把团队锁死在单一云。

## 旧范式 vs 新范式
- **旧做法**：决策 = 提示词 + JSON schema + 输出解析 + 人工置信度阈值；换模型=重写适配层；置信度靠 self-report 或 logprob hack。
- **新做法**：决策 = 类型化原语调用（noul / choice / score），直接从允许答案的下一 token 概率或专用 decision head 读出期望值与置信度；wire format 层出现事实标准竞争（TypeSafe System One 的 `POST /v1/systemone`、Google Gemini Decisions、OpenAI Decisions API），而客户端用「Any-slot」抽象把实现细节全部下沉。

## 生产力影响 (How)
应用层可以按场景混搭：高价值判定走云端专业决策模型（Gemini 可读图/音/视频/文档），高频低价值判定走端侧 4bit Qwen3 + MLX/llama.cpp 的 next-token scoring。开发者拿到的是 `Double` 概率与 `Choice<T>` 类型，可直接接入业务阈值与审计日志，无需解析文本。切换供应商=改一行 backend 构造。

## 采用成本
低：Swift Package，无 trait 时零第三方依赖；本地后端需 Metal toolchain 或 Core AI（macOS 27 / iOS 27）；模型下载 600MB–2.4GB 量级。主要成本是「把业务问题改写成 noul/choice/score」的建模工作，以及为决策模型单独做评测与校准。

## 核心线索
- GitHub：https://github.com/mattt/AnyDecisionModel
- 来源：https://huggingface.co/blog/anydecisionmodel
- 发布时间：2026-11-18
