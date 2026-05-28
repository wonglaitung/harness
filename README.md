# Harness

An embeddable AI Agent SDK for Python.

## Installation

```bash
pip install harness-ai
```

## Quick Start

```python
from harness import AgentHarness, ReadTool, GlobTool

# Create agent with Anthropic Claude
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool(), GlobTool()],
)

# Run agent
result = await agent.run("Analyze the Python files in this directory")
print(result.content)
```

## LLM Providers

### Anthropic Claude (Default)

```python
from harness import AgentHarness, ReadTool

# Using environment variable ANTHROPIC_API_KEY
agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool()],
)

# Or with explicit API key
agent = AgentHarness(
    model="claude-opus-4-6",
    api_key="your-api-key",
    tools=[ReadTool()],
)
```

### OpenAI

```python
from harness import AgentHarness, ReadTool

# Using environment variable OPENAI_API_KEY
agent = AgentHarness(
    model="gpt-4o",
    provider="openai",
    tools=[ReadTool()],
)

# Or with explicit API key
agent = AgentHarness(
    model="gpt-4o",
    provider="openai",
    api_key="your-api-key",
    tools=[ReadTool()],
)
```

### OpenAI-Compatible Endpoints (Ollama, Azure, etc.)

```python
from harness import AgentHarness, OpenAIClient, ReadTool

# Ollama local LLM
agent = AgentHarness(
    model="llama3",
    provider="openai",
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Ollama doesn't require a real key
    tools=[ReadTool()],
)

# Azure OpenAI
agent = AgentHarness(
    model="gpt-4o",
    provider="openai",
    base_url="https://your-resource.openai.azure.com/openai/deployments/your-deployment",
    api_key="your-azure-key",
    tools=[ReadTool()],
)
```

### Custom LLM Client

```python
from harness import AgentHarness, LLMClient, LLMConfig, ReadTool
from harness.types import LLMResponse, StopReason, TokenUsage

class MyCustomLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "my-custom-llm"

    async def call(self, messages, tools=None, system=None, **kwargs) -> LLMResponse:
        # Implement your LLM logic here
        return LLMResponse(
            content="Response from custom LLM",
            tool_calls=[],
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=0, output_tokens=0),
        )

    async def stream(self, messages, tools=None, system=None, on_chunk=None, **kwargs):
        # Implement streaming if needed
        yield "Response"

# Use custom LLM
agent = AgentHarness(
    llm_client=MyCustomLLM(LLMConfig(model="my-custom-llm")),
    tools=[ReadTool()],
)
```

## Configuration

### Via Config Object

```python
from harness import AgentHarness, HarnessConfig, ReadTool

config = HarnessConfig(
    model="claude-sonnet-4-6",
    provider="anthropic",
    max_tokens=4096,
    temperature=0.7,
    system_prompt="You are a helpful assistant.",
    max_iterations=100,
)

agent = AgentHarness(config=config, tools=[ReadTool()])
```

### Via Config File (YAML/JSON)

```yaml
# config.yaml
model: gpt-4o
provider: openai
max_tokens: 4096
temperature: 0.7
system_prompt: "You are a helpful assistant."
```

```python
agent = AgentHarness.from_config("config.yaml")
```

## Features

- **Multi-Provider LLM**: Anthropic Claude, OpenAI, and custom LLM support
- **Agent Loop**: ReAct-style execution with tool calling
- **Tool System**: Built-in tools for file operations, search, and shell
- **Memory**: Session management with file-based persistence
- **SDK**: Simple, Pythonic API

## Documentation

See the `docs/` directory for detailed design documentation.

## License

MIT
