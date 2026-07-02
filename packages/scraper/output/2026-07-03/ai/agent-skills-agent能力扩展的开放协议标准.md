# Agent Skills 标准

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次定义SKILL.md渐进式技能加载协议，提出"发现→激活→执行"三阶段模型 |
| 采用广度 | ☆☆☆☆☆/5 | Anthropic发起开放标准，已被Claude Code、Codex、Cursor、Hermes等68+代理客户端采用 |
| 时间新鲜 | ☆☆☆☆/5 | 2025年末首次发布，2026年快速扩散 |
| 社区热度 | ☆☆☆☆/5 | GitHub trending持续出现，NVIDIA/Google/Vercel均发布技能包 |
| **总体判断** | ✅ | **新范式 — Agent能力扩展的开放协议标准** |

## 技术定义 (What)

Agent Skills 是一种轻量级开放格式，用于给AI代理扩展专业能力和工作流。核心是一个包含 `SKILL.md` 文件的文件夹，其中定义了元数据（名称、描述）和执行指令。技能还可捆绑脚本、参考资料、模板等资源。

关键创新在于**渐进式披露（Progressive Disclosure）**三阶段加载模型：
1. **发现（Discovery）**：启动时仅加载技能名称和描述，最小化上下文占用
2. **激活（Activation）**：任务匹配时读取完整 SKILL.md 指令
3. **执行（Execution）**：按需执行捆绑代码或加载引用文件

## 行业痛点 (Why)

当前AI代理面临两大问题：
1. **能力泛化vs专业化矛盾**：通用模型缺乏领域专业上下文，每次从零开始效率低
2. **技能不可移植**：为Claude写的prompt无法用于Codex，技能与平台强绑定

## 旧范式 vs 新范式

- **旧做法**：为每个Agent手写system prompt，技能与特定客户端绑定，无法跨产品复用；或通过API调用外部工具，上下文膨胀
- **新做法**：将领域知识打包为SKILL.md文件夹，一次构建跨68+客户端复用；渐进式披露让Agent同时拥有大量技能而上下文占用极小

## 生产力影响 (How)

- **技能复用率提升10x+**：构建一次，所有兼容Agent通用
- **上下文效率提升**：100个技能仅占发现阶段的token，按需激活
- **团队知识沉淀**：将公司内部流程、代码规范等打包为技能，新人Agent即插即用
- **生态系统效应**：NVIDIA、Google、Vercel等大厂已发布官方技能包

## 采用成本

- **时间**：创建一个基础SKILL.md约15-30分钟
- **金钱**：完全免费，开源Apache 2.0协议
- **学习曲线**：极低，仅需理解SKILL.md格式和渐进式披露概念

## 采用案例

- **Anthropic/skills**：Anthropic官方技能包，Claude Code内置支持
- **NVIDIA/skills**：NVIDIA发布的AI Agent技能，聚焦GPU计算领域
- **Vercel/skills**：前端开发技能包，`npx skills add vercel-labs/agent-skills`
- **Google/agents-cli**：Google Cloud Agent构建部署技能
- **Hermes Agent**：兼容agentskills.io标准，自动从经验创建技能

## 风险/局限

- 标准仍在快速演进，SKILL.md格式可能变化
- 不同Agent对技能的执行能力差异大
- 安全风险：技能可包含可执行脚本，需信任来源
- 渐进式披露的匹配精度依赖Agent的意图识别能力

## 核心线索

- GitHub：https://github.com/agentskills/agentskills
- 官网：https://agentskills.io
- 规范：https://agentskills.io/specification
- 首发来源：Anthropic发起
- 发布时间：2025年末
- 当前状态：快速扩散中，生态形成期