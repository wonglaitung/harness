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

## Features

- **Agent Loop**: ReAct-style execution with tool calling
- **Tool System**: Built-in tools for file operations, search, and shell
- **Memory**: Session management with file-based persistence
- **SDK**: Simple, Pythonic API

## Documentation

See the `docs/` directory for detailed design documentation.

## License

MIT