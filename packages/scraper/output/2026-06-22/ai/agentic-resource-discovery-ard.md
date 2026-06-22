# Agentic Resource Discovery (ARD)

## 技术定义 (What)
开放规范，定义 Agent 如何发现、索引和搜索跨联邦注册中心的工具、技能和其他 Agent。将"手动安装静态目录"转变为"意图驱动的动态发现"，Agent 可以在运行时找到所需能力。

## 行业痛点 (Why)
当前 Agent 能力采用"先安装，后使用"模式。开发者需要预先配置 MCP 服务器、手动连接插件。当可用工具达到数千个时，无法预先安装所有工具，也无法在 context window 中列出所有工具描述。

## 旧范式 vs 新范式
- **旧做法**：手动配置 MCP 服务器 URL、安装插件、硬编码工具列表。Agent 只能使用预安装的工具，无法动态发现新能力。
- **新做法**：ARD 定义两层：静态清单格式 `ai-catalog.json`（发布者在已知 URL 托管能力）和动态注册 API `POST /search`（实时、排名的发现）。Agent 用自然语言搜索能力，返回 MCP 工具、Skills 或 A2A Agent。支持联邦查询，一个搜索可以跨越多个注册中心。

## 生产力影响 (How)
让 Agent 从"静态能力"进化为"动态生态"。Agent 无需预先配置即可访问数千个工具。支持运行时能力发现，降低了 Agent 部署和集成的复杂度。是 MCP/A2A/Skills 协议生态的关键补充。

## 采用成本
协议本身免费开放。Hugging Face 已实现参考实现 `hf discover`。使用 CLI：`hf discover search "query"`。集成到 Agent 需要实现 ARD 客户端或使用现有 MCP 工具。

## 核心线索
- GitHub：
- 来源：https://huggingface.co/blog/agentic-resource-discovery-launch
- 发布时间：2026-06-22
