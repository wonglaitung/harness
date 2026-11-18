# Elephant-Goldfish Model (EGM)

## 技术定义 (What)
Google 开源的编码 Agent 插件，把「设计」与「评审」拆成两个**上下文不对称**的角色：Elephant（大象）持有完整项目上下文、需求与既往决策，负责探索问题并起草规格；Goldfish（金鱼）**只看到文档与被引用的原始材料，看不到之前的对话**，因此无法继承作者的假设，只能暴露未言明的假设、模糊需求与实现风险。关键工程约束：Goldfish 必须运行在**全新的子 Agent 上下文**中，若宿主 Agent 无法创建新上下文，评审直接中止（而不是降级为「假独立评审」）。人负责权衡取舍与批准规格。配套 7 个技能：brainstorm（概念简报）→ draft（分节暂停取反馈）→ review（五阶段 fresh-eyes 评审）→ resolve（逐条收敛发现）→ bootstrap（为存量代码库补文档）→ drift-report（文档与源码漂移比对）→ review-loop（自定义评审组与标准）。已支持 Claude Code / Codex / Antigravity / ChatGPT 插件 / Claude Cowork。

## 行业痛点 (Why)
AI 写文档和评审自己的文档时，会继承同一套错误前提（同一个上下文里的「自洽幻觉」）：长上下文 Agent 记得自己为什么这么写，于是评审时只验证「我是否按我原先的想法写了」，而不是「这个想法是否成立」。业界做法有两个极端：要么让同一 Agent 自查（零独立性），要么花钱请人类专家评审（不可扩展）。EGM 的洞察是——独立性不必来自「更强/更贵的模型」，而来自**上下文缺失**：把对话历史当作污染源主动切除。

## 旧范式 vs 新范式
- **旧做法**：单 Agent 自我评审：起草者与评审者是同一上下文中的同一个实例，评审退化为格式检查与措辞润色；多 Agent 评审通常也只是「多开几个同样拥有完整上下文的 Agent」，共享同一套偏见，成本翻倍而独立性未增。
- **新做法**：**Asymmetric-Context Review（上下文不对称评审）**：按角色分配上下文预算——决策者（Elephant）获得最大上下文，评审者（Goldfish）获得**最小充分上下文**（文档 + 被引用的原始材料，且不含对话）。独立性成为可配置的资源分配问题，而非模型能力问题。同时把「新上下文不可得」定义为硬失败（fail-closed），防止评审质量静默腐化。同一机制可外推为 Document-as-Oracle：文档被当作唯一真相源交给评审者，文档本身的完备性因此被压测出来。

## 生产力影响 (How)
1) 让 AI 设计评审从「自己批改自己」变成可审计的对抗环节，未言明假设类缺陷的发现率随之上移；2) 上下文切除显著降低评审 token 成本（Goldfish 不背对话历史），比「开个更强的模型再审一遍」便宜得多；3) drift-report 把文档腐化变成可定期运行的检查，而不是等新人踩坑；4) 与 Claude Code 团队「Check Integrity（改动不能修改评判它的检查）」构成同一条工程主线——**评审有效性依赖结构约束，而非模型诚实度**。

## 采用成本
安装是一条命令级（`claude plugin marketplace add google/elephant-goldfish-model` / `codex plugin marketplace add ...` / `agy plugin install <url>`）。真实成本在流程改造：团队需要接受「规格先行 + 分节取反馈」的节奏，并把批准的规格存到 `docs/designs/`；Goldfish 评审要求宿主能创建全新 subagent（部分轻量 CLI 不支持则功能不可用）。另需注意 EGM 明确声明：评审不替代测试与人类判断。

## 核心线索
- GitHub：https://github.com/google/elephant-goldfish-model
- 来源：https://github.com/google/elephant-goldfish-model
- 发布时间：2026-11-18
