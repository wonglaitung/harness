# Agent Skills Spec

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次定义"渐进式技能发现"协议（Discovery→Activation→Execution三阶段），将Agent能力扩展从硬编码转为声明式Markdown规范 |
| 采用广度 | ☆☆☆☆☆/5 | 20+客户端已支持：Claude Code、Cursor、GitHub Copilot、Gemini CLI、OpenCode、Roo Code、Letta、OpenHands、Amp、Kiro、Goose、Mistral Vibe、Pulumi Neo、Spring AI等 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年正式发布，agentskills.io上线，被Allen AI Shippy等生产系统采用 |
| 社区热度 | ☆☆☆☆/5 | 行业级采用（非单一项目），覆盖编码Agent、企业Agent、具身Agent三大类别 |
| **总体判断** | ✅ | **新范式 — Agent能力扩展开放协议** |

## 技术定义 (What)
Agent Skills是一个**轻量级开放格式**，用于扩展AI Agent的能力和专业知识。核心是一个包含`SKILL.md`文件的文件夹，其中包含元数据（name、description）和指令。Skills还可以捆绑脚本、参考资料、模板等资源。

关键创新是**渐进式技能发现**（Progressive Disclosure）三阶段协议：
1. **Discovery（发现）**：Agent启动时仅加载每个Skill的名称和描述，仅占极小上下文
2. **Activation（激活）**：当任务匹配Skill描述时，Agent读取完整SKILL.md指令到上下文
3. **Execution（执行）**：Agent按指令执行，可选执行捆绑代码或加载引用文件

## 行业痛点 (Why)
当前Agent面临三大问题：
1. **能力硬编码**：Agent能力在开发时固定，无法按需扩展
2. **上下文浪费**：所有工具描述一次性加载，大量无关信息占用上下文窗口
3. **跨产品不可复用**：每个Agent平台有自己的工具/插件格式，同一能力需重复开发

## 旧范式 vs 新范式
- **旧做法**：Agent工具通过API定义硬编码，所有工具描述一次性注入系统提示，跨平台不兼容
- **新做法**：Agent能力以Markdown Skill声明式定义，渐进式按需加载，一次编写跨20+平台复用

## 生产力影响 (How)
1. **上下文效率**：渐进式加载意味着Agent可持有数百个Skill但仅占用极小上下文，只在需要时激活
2. **一次编写多平台复用**：开发者创建一个Skill文件夹，即可在Claude Code、Cursor、Copilot等20+平台使用
3. **领域知识可移植**：企业可将内部流程（法律审查、数据分析、报告格式）打包为Skill，跨Agent平台部署
4. **版本化可审计**：Skill以文件夹形式存在，可Git版本控制，可审计变更历史

## 采用成本
- **创建Skill**：免费，仅需编写SKILL.md（Markdown格式），学习成本极低
- **集成到Agent**：需实现三阶段加载逻辑（发现→激活→执行），约1-2天开发量
- **迁移现有工具**：将现有API工具转为Skill格式，每个工具约30分钟

## 采用案例
- **Allen AI Shippy**：海事AI Agent，使用Agent Skills规范定义Skylight API查询、EEZ/MPA边界查询、船舶轨迹解读等技能，实现高可靠性领域Agent
- **Claude Code**：Anthropic的编码Agent，原生支持Skills，用户可自定义编码工作流
- **Cursor**：AI编码编辑器，支持Skills扩展编码能力
- **GitHub Copilot**：微软的AI编程助手，已集成Skills支持
- **Mistral Vibe**：Mistral AI的Agent工具，支持Skills格式

## 风险/局限
- **标准化风险**：目前由社区驱动，尚无正式标准组织背书
- **安全考量**：Skill可捆绑可执行代码，需沙箱执行环境
- **质量参差**：开放格式意味着Skill质量无保证，需社区评审机制
- **竞争格式**：MCP（Model Context Protocol）在工具层有重叠，两者关系需厘清

## 核心线索
- 官网：https://agentskills.io
- 首发来源：Agent Skills社区
- 发布时间：2026年
- 当前状态：快速扩张中，20+客户端已支持
- 关键参考：Allen AI Shippy技术博客详细展示了Skills在生产系统中的应用