# MCP Apps — MCP工具内嵌交互式UI协议

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次定义MCP工具的UI资源声明协议（ui://），实现工具返回从纯文本到交互式UI的范式跃迁 |
| 采用广度 | ☆☆☆☆/5 | 已被ChatGPT、Claude、VS Code、Goose、Postman等6+主流客户端支持 |
| 时间新鲜 | ☆☆☆☆☆/5 | 规范日期2026-01-26，极其新鲜 |
| 社区热度 | ☆☆☆☆/5 | MCP官方扩展规范，GitHub持续活跃，npm包发布 |
| **总体判断** | ✅ | **新范式 — AI对话中交互式UI的标准协议** |

## 技术定义 (What)

MCP Apps 是 Model Context Protocol 的官方扩展规范，定义了一种标准化方式让MCP服务器中的工具声明交互式UI资源。核心机制：

1. **工具定义**：工具声明 `ui://` 资源，包含HTML界面
2. **工具调用**：LLM调用服务器上的工具
3. **宿主渲染**：宿主客户端获取资源并在沙箱iframe中渲染
4. **双向通信**：宿主通过通知将工具数据传给UI，UI可通过宿主调用其他工具

关键创新：MCP工具不再只能返回文本和结构化数据，可以返回图表、表单、设计画布、视频播放器等完整交互式UI，直接内嵌在对话中渲染。

## 行业痛点 (Why)

1. **MCP工具的表达力瓶颈**：当前MCP工具只能返回文本/JSON，无法表达图表、表单、画布等交互界面
2. **AI对话的交互天花板**：用户需要可视化操作时必须跳出对话到外部应用
3. **工具UI碎片化**：每个AI客户端自行定义工具UI渲染方式，无法互操作

## 旧范式 vs 新范式

- **旧做法**：MCP工具返回纯文本/JSON，用户需自行解读；或各客户端自定义工具UI，互不兼容
- **新做法**：工具声明 `ui://` 资源，宿主客户端标准化渲染iframe，支持双向通信；一次构建，ChatGPT/Claude/VS Code等所有合规客户端通用

## 生产力影响 (How)

- **工具表达力质变**：从"返回文本"到"返回交互式应用"，MCP工具可构建完整可视化界面
- **用户体验飞跃**：用户在对话中直接操作图表、填写表单、使用设计工具
- **开发效率**：SDK提供App类、React hooks（useApp、useHostStyles）、App Bridge三套API，覆盖开发者/宿主/服务器三种角色
- **Agent Skills集成**：内置4个Agent Skills（create-mcp-app、migrate-oai-app、add-app-to-server、convert-web-app），AI编码代理可自动构建MCP App

## 采用成本

- **时间**：使用SDK构建基础MCP App约1-2小时
- **金钱**：完全免费，Apache 2.0开源
- **学习曲线**：中等，需理解MCP协议基础和iframe沙箱通信

## 采用案例

- **Excalidraw MCP App**：在Claude中直接运行Excalidraw画板
- **ChatGPT集成**：OpenAI官方文档已发布MCP Apps指南
- **Claude集成**：Anthropic官方文档支持MCP Apps构建
- **VS Code集成**：2026-01-26博客宣布支持

## 风险/局限

- 沙箱iframe可能存在性能限制
- 宿主客户端支持度不一，功能可能有差异
- UI复杂度受限于单工具场景
- 安全性依赖沙箱隔离，需持续审计

## 核心线索

- GitHub：https://github.com/modelcontextprotocol/ext-apps
- 规范：https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx
- API文档：https://apps.extensions.modelcontextprotocol.io/api/
- npm包：@modelcontextprotocol/ext-apps
- 发布时间：2026-01-26
- 当前状态：官方规范，快速推进中