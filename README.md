# Harness

An embeddable AI Agent SDK for Python.

## Installation

```bash
pip install harness-ai
```

## Quick Start

```python
from harness import AgentHarness, ReadTool, GlobTool

# Create agent
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool(), GlobTool()],
)

# Run agent
result = await agent.run("Analyze the Python files in this directory")
print(result.content)
```

## LLM Configuration

### 第三方 OpenAI 格式接口（推荐）

Harness 支持任何兼容 OpenAI API 格式的第三方接口，只需提供 `base_url`、`api_key` 和 `model`：

```python
from harness import AgentHarness, ReadTool, GlobTool

agent = AgentHarness(
    base_url="https://api.your-provider.com/v1",  # 第三方接口 URL
    api_key="your-api-key",                        # API Key
    model="your-model-name",                       # 模型名称
    provider="openai",                             # 使用 OpenAI 格式
    tools=[ReadTool(), GlobTool()],
)

result = await agent.run("你的问题")
```

#### 环境变量配置

也可以通过环境变量配置：

```bash
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=https://api.your-provider.com/v1
```

```python
from harness import AgentHarness, ReadTool

# 自动读取环境变量
agent = AgentHarness(
    model="your-model-name",
    provider="openai",
    tools=[ReadTool()],
)
```

#### 配置文件方式

创建 `config.yaml`：

```yaml
model: your-model-name
provider: openai
base_url: https://api.your-provider.com/v1
api_key: your-api-key
max_tokens: 4096
temperature: 0.7
system_prompt: "你是一个有帮助的助手。"
```

```python
agent = AgentHarness.from_config("config.yaml")
```

### 其他 LLM 提供商

<details>
<summary>Anthropic Claude</summary>

```python
from harness import AgentHarness, ReadTool

# 环境变量: ANTHROPIC_API_KEY
agent = AgentHarness(
    model="claude-sonnet-4-6",
    provider="anthropic",
    tools=[ReadTool()],
)
```

</details>

<details>
<summary>OpenAI 官方</summary>

```python
from harness import AgentHarness, ReadTool

# 环境变量: OPENAI_API_KEY
agent = AgentHarness(
    model="gpt-4o",
    provider="openai",
    tools=[ReadTool()],
)
```

</details>

<details>
<summary>Ollama 本地模型</summary>

```python
from harness import AgentHarness, ReadTool

agent = AgentHarness(
    model="llama3",
    provider="openai",
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Ollama 不需要真实的 key
    tools=[ReadTool()],
)
```

</details>

<details>
<summary>自定义 LLM 客户端</summary>

```python
from harness import AgentHarness, LLMClient, LLMConfig, ReadTool
from harness.types import LLMResponse, StopReason, TokenUsage

class MyCustomLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "my-custom-llm"

    async def call(self, messages, tools=None, system=None, **kwargs) -> LLMResponse:
        # 实现你的 LLM 逻辑
        return LLMResponse(
            content="Response",
            tool_calls=[],
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )

    async def stream(self, messages, tools=None, system=None, on_chunk=None, **kwargs):
        yield "Response"

agent = AgentHarness(
    llm_client=MyCustomLLM(LLMConfig(model="my-custom-llm")),
    tools=[ReadTool()],
)
```

</details>

## 完整配置参数

```python
from harness import AgentHarness, HarnessConfig, ReadTool

config = HarnessConfig(
    # LLM 配置
    model="your-model-name",           # 模型名称
    provider="openai",                 # 提供商: "anthropic" 或 "openai"
    base_url="https://api.xxx.com/v1", # 自定义 API 地址
    api_key="your-api-key",            # API Key
    max_tokens=4096,                   # 最大输出 token
    temperature=0.7,                   # 温度参数

    # Agent 配置
    max_iterations=100,                # 最大迭代次数
    tool_timeout=30.0,                 # 工具超时时间（秒）
    system_prompt="你是一个助手",      # 系统提示词

    # Memory 配置
    memory_dir=".harness/memory",      # 会话存储目录
)

agent = AgentHarness(config=config, tools=[ReadTool()])
```

## Built-in Tools

| Tool | Description |
|------|-------------|
| `ReadTool` | 读取文件内容 |
| `WriteTool` | 写入文件 |
| `EditTool` | 编辑文件（查找替换） |
| `GlobTool` | 按模式查找文件 |
| `GrepTool` | 搜索文件内容 |
| `BashTool` | 执行 shell 命令 |

## 自定义工具

```python
from harness import AgentHarness

agent = AgentHarness(model="your-model", provider="openai")

@agent.tool(description="计算两个数的和")
def add(a: int, b: int) -> int:
    return a + b

result = await agent.run("计算 5 + 3")
```

## 测试

使用 `MockLLMClient` 进行单元测试，无需真实 API 调用：

```python
from harness import AgentHarness, ReadTool
from harness.llm import MockLLMClient, LLMConfig
from harness.llm.mock import MockResponse, create_tool_use_mock

# 创建模拟客户端
mock_client = MockLLMClient(
    model="mock-model",
    responses=[
        MockResponse(content="这是模拟响应"),
    ]
)

# 使用模拟客户端创建 agent
agent = AgentHarness(
    llm_client=mock_client,
    tools=[ReadTool()],
)

# 测试
result = await agent.run("测试问题")
assert result.content == "这是模拟响应"
```

## Features

- **多 LLM 支持**: Anthropic Claude、OpenAI、第三方 OpenAI 格式接口、自定义 LLM
- **Agent Loop**: ReAct 风格的执行循环，支持进度事件追踪
- **Tool System**: 内置工具 + 自定义工具
- **Memory**: 会话管理与持久化存储
- **SDK**: 简洁的 Python API
- **Progress Events**: 执行过程可视化，支持 UI 展示和调试

## Documentation

详细设计文档见 `docs/` 目录。

## License

MIT
