# aisuite

## 技术定义 (What)
aisuite 是 Andrew Ng 发布的轻量级 Python 库，提供两层 API：统一 Chat Completions API（跨提供商）和 Agents API（工具调用 + 工具包 + MCP）。支持 OpenAI、Anthropic、Google、Ollama 等，模型切换只需改一个字符串。附带 OpenCoworker 桌面应用。

## 行业痛点 (Why)
不同 LLM 提供商 API 格式各异，工具调用实现差异大，构建跨模型应用需要维护多套代码。Agent 工具调用需要手动管理循环、执行、结果返回。缺乏统一的工具包和 MCP 集成。

## 旧范式 vs 新范式
- **旧做法**：为每个 LLM 提供商写适配器：OpenAI SDK、Anthropic SDK、Google SDK... 工具调用手动实现循环：模型返回 tool_call → 执行函数 → 返回结果 → 再次调用。工具包各项目重复造轮子。
- **新做法**：统一接口：model="openai:gpt-4o" 或 "anthropic:claude-3-5-sonnet"，一个 API 调所有模型。工具调用一行：tools=[will_it_rain], max_turns=2，自动执行循环。工具包开箱：toolkits.files、toolkits.git、toolkits.shell。MCP 原生：任何 MCP server 的工具可直接传入。

## 生产力影响 (How)
开发效率大幅提升：跨模型应用从多套代码简化为一套。工具调用从手动循环变成一行代码。自带桌面应用 OpenCoworker，可直接使用（支持 macOS、Windows）。扩展性强：新提供商只需实现适配器，自动加载。

## 采用成本
开源免费（MIT 协议）。安装：pip install aisuite 或 pip install 'aisuite[all]'。需自备 API Key（OpenAI、Anthropic、Google）或本地运行 Ollama。学习成本低，API 类似 OpenAI 风格。

## 核心线索
- GitHub：https://github.com/andrewyng/aisuite
- 来源：https://github.com/trending/python
- 发布时间：2026-06-15
