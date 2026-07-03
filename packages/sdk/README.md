# Harness SDK

An embeddable AI Agent SDK for Python.

## Installation

```bash
pip install harness-ai
```

### Optional Extensions

```bash
pip install "harness-ai[openai]"        # OpenAI support
pip install "harness-ai[observability]" # OpenTelemetry observability
pip install "harness-ai[sqlite]"        # SQLite session storage
pip install "harness-ai[web]"           # Web scraping tools
pip install "harness-ai[guardrails]"    # PII detection and content safety

# Install multiple extensions
pip install "harness-ai[openai,sqlite,web,guardrails]"
```

### Development Mode

```bash
pip install -e ".[dev]"                    # Development dependencies
pip install -e ".[dev,openai,observability]"  # Development + all extensions
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

### Third-Party OpenAI-Compatible APIs (Recommended)

Harness supports any OpenAI-compatible API:

```python
from harness import AgentHarness, ReadTool

agent = AgentHarness(
    base_url="https://api.your-provider.com/v1",
    api_key="your-api-key",
    model="your-model-name",
    provider="openai",
    tools=[ReadTool()],
)

result = await agent.run("Your question")
```

#### Environment Variables

```bash
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=https://api.your-provider.com/v1
```

```python
from harness import AgentHarness

agent = AgentHarness(
    model="your-model-name",
    provider="openai",
)
```

#### Config File

```yaml
# config.yaml
model: your-model-name
provider: openai
base_url: https://api.your-provider.com/v1
api_key: your-api-key
max_tokens: 4096
temperature: 0.7
system_prompt: "You are a helpful assistant."
```

```python
agent = AgentHarness.from_config("config.yaml")
```

### Other LLM Providers

<details>
<summary>Anthropic Claude</summary>

```python
from harness import AgentHarness

# Environment variable: ANTHROPIC_API_KEY
agent = AgentHarness(
    model="claude-sonnet-4-6",
    provider="anthropic",
)
```

</details>

<details>
<summary>OpenAI Official</summary>

```python
from harness import AgentHarness

# Environment variable: OPENAI_API_KEY
agent = AgentHarness(
    model="gpt-4o",
    provider="openai",
)
```

</details>

<details>
<summary>Ollama Local Models</summary>

```python
from harness import AgentHarness

agent = AgentHarness(
    model="llama3",
    provider="openai",
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Ollama doesn't need a real key
)
```

</details>

<details>
<summary>Custom LLM Client</summary>

```python
from harness import AgentHarness, LLMClient, LLMConfig
from harness.types import LLMResponse, StopReason, TokenUsage

class MyCustomLLM(LLMClient):
    @property
    def model_name(self) -> str:
        return "my-custom-llm"

    async def call(self, messages, tools=None, system=None, **kwargs) -> LLMResponse:
        # Implement your LLM logic
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
)
```

</details>

## Configuration

```python
from harness import AgentHarness, HarnessConfig, ReadTool

config = HarnessConfig(
    # LLM configuration
    model="your-model-name",
    provider="openai",
    base_url="https://api.xxx.com/v1",
    api_key="your-api-key",
    context_window="auto",  # "auto", "32k", "64k", "128k", "200k" or specific number
    max_tokens="auto",      # "auto" or specific number
    temperature=0.7,

    # Agent configuration
    max_iterations=100,
    tool_timeout=30.0,
    system_prompt="You are a helpful assistant",

    # Memory configuration
    memory_dir=".harness/memory",
)

agent = AgentHarness(config=config, tools=[ReadTool()])
```

### Model Context Window Auto-Detection

```python
from harness import AgentHarness

# Auto-detect (recommended)
agent = AgentHarness(model="glm-5")  # Auto-uses 64K context

# Manual override
agent = AgentHarness(
    model="unknown-model",
    context_window="64k",  # "32k", "64k", "128k", "200k"
)
```

## Built-in Tools

| Tool | Description |
|------|-------------|
| `ReadTool` | Read file contents |
| `WriteTool` | Write to files |
| `EditTool` | Edit files (find and replace) |
| `GlobTool` | Find files by pattern |
| `GrepTool` | Search file contents |
| `BashTool` | Execute shell commands |
| `WebSearchTool` | Web search (DuckDuckGo free API) |
| `WebFetchTool` | Fetch web page content |
| `WebToMarkdownTool` | Fetch and convert to Markdown |

### Web Tools Example

```python
from harness import AgentHarness, WebSearchTool, WebFetchTool, WebToMarkdownTool

agent = AgentHarness(
    model="your-model",
    provider="openai",
    tools=[WebSearchTool(), WebFetchTool(), WebToMarkdownTool()],
)

result = await agent.run("Search for Python asyncio best practices")
```

**Dependencies**:
```bash
pip install aiohttp beautifulsoup4
```

## Custom Tools

```python
from harness import AgentHarness

agent = AgentHarness(model="your-model", provider="openai")

@agent.tool(description="Calculate the sum of two numbers")
def add(a: int, b: int) -> int:
    return a + b

result = await agent.run("Calculate 5 + 3")
```

## Testing

### MockHarness (Recommended)

```python
from harness.testing import MockHarness, MockResponse
from harness.types import StopReason, ToolCall

# Simple test
mock = MockHarness(responses=[
    MockResponse(content="This is a mock response"),
])

result = await mock.run("Test question")
assert result.content == "This is a mock response"

# Mock tool calls
mock = MockHarness(responses=[
    MockResponse(
        tool_calls=[ToolCall(id="1", name="read", arguments={"path": "/test.txt"})],
        stop_reason=StopReason.TOOL_USE,
    ),
    MockResponse(content="File content: test data"),
])
mock.add_tool_result("read", "test data")

result = await mock.run("Read file")
assert "test data" in result.content
```

### RecordingHarness (Record Real Interactions)

```python
from harness.testing import RecordingHarness, RecordingConfig
from harness import AgentHarness

# Record
agent = AgentHarness(model="claude-sonnet-4-6")
recorder = RecordingHarness(agent)

result = await recorder.run("Complex task")
recorder.save_recording("test_fixture")

# Playback
mock = MockHarness()
mock.load_recording("test_fixture.json")

result = await mock.run("Complex task")  # No real API call
```

## Guardrails (PII Detection)

Guardrails provides two-layer protection:
- **Layer 1: PII Rule Detection** - Fast (<1ms), regex + surname database
- **Layer 2: LLM Judge** - Semantic detection (~100ms), optional

### Quick Start

```python
from harness import AgentHarness, ReadTool
from harness.guardrails import GuardrailConfig

agent = AgentHarness(
    model="claude-sonnet-4-6",
    tools=[ReadTool()],
    guardrails=GuardrailConfig(
        enabled=True,
        layer1_enabled=True,
        layer2_enabled=False,
    ),
)

result = await agent.run("My phone number is 13812345678")
# PII redacted to: "My phone number is <手机号>"
```

### Supported PII Types

| Type | Example | Placeholder |
|------|---------|-------------|
| China Mobile | 13812345678 | `<手机号>` |
| China ID Card | 110101199001011234 | `<身份证号>` |
| Bank Card | 6222021234567890123 | `<银行卡号>` |
| Passport | G12345678 | `<护照号>` |
| Social Credit Code | 91110000000000000X | `<信用代码>` |
| License Plate | 京A12345 | `<车牌号>` |
| Email | test@example.com | `<邮箱>` |
| IP Address | 192.168.1.1 | `<IP地址>` |
| Hong Kong Mobile | 5123 4567 | `<香港手机号>` |
| Hong Kong ID | A123456(7) | `<香港身份证>` |
| Chinese Name | 张三、欧阳锋 | `<姓名>` |

### Direct PII Functions

```python
from harness.guardrails import check_pii, scan_pii, redact_pii, PIIEntity

# check_pii() returns tuple: (safe_text, entities, has_pii)
safe_text, entities, has_pii = check_pii("My phone is 13812345678")

# PIIEntity attributes
for entity in entities:
    print(f"Type: {entity.entity_type}")  # "PHONE_NUMBER"
    print(f"Text: {entity.text}")          # "13812345678"
    print(f"Start: {entity.start}")
    print(f"End: {entity.end}")
    print(f"Score: {entity.score}")

# scan_pii() returns object
result = scan_pii(text)
print(result.entities)
print(result.has_pii)

# Quick redact
redacted = redact_pii(text)
```

## Loop Engineering

**Loop Engineering** is a new paradigm: instead of prompting at each step, design automated loop systems to drive the agent.

### Goal-Driven Execution

Let the agent run autonomously until a goal is achieved:

```python
from harness import AgentHarness, GoalStatus

agent = AgentHarness(model="claude-sonnet-4-6")

# Basic usage
result = await agent.run_goal("Fix all type errors in src/")

# Check result
if result.status == GoalStatus.ACHIEVED:
    print(f"Goal achieved in {result.total_iterations} iterations")
```

### Custom Verification

```python
async def check_coverage(result):
    """Check if test coverage reaches 80%"""
    proc = await asyncio.create_subprocess_exec(
        "pytest", "--cov", "--cov-report=term",
        stdout=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return "TOTAL.*80%" in stdout.decode()

result = await agent.run_goal(
    goal="Increase test coverage to 80%",
    custom_verifier=check_coverage,
    max_iterations=50,
)
```

### Tool Verification

Run tests, lint, and type checks to verify goals:

```python
from harness.loop import GoalConfig, VerificationMethod
from harness.loop.tool_verification import ToolVerificationConfig

# Python project verification
result = await agent.run_goal(
    goal=GoalConfig(
        description="Fix all type errors",
        verification_method=VerificationMethod.TOOL,
        tool_verification_config=ToolVerificationConfig.python_defaults(),
    ),
)

# Custom commands
config = ToolVerificationConfig(
    commands=[
        ("pytest", "pytest", "tests/", "-v"),
        ("mypy", "mypy", "src/"),
        ("ruff", "ruff", "check", "src/"),
    ],
    timeout_seconds=300,
)

# Presets available
ToolVerificationConfig.python_defaults()   # pytest + mypy + ruff
ToolVerificationConfig.gradle_defaults()   # gradle test + check
ToolVerificationConfig.maven_defaults()    # mvn test
ToolVerificationConfig.npm_defaults()      # npm test + lint
```

### Environment Variables

Create agent from environment variables:

```python
import os
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
os.environ["HARNESS_MODEL"] = "claude-sonnet-4-6"

agent = AgentHarness.from_env()
```

**Supported environment variables**:
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`: API key
- `HARNESS_MODEL`: Model name (default: claude-sonnet-4-6)
- `HARNESS_PROVIDER`: Provider (anthropic/openai/auto)
- `HARNESS_BASE_URL`: Custom API endpoint
- `HARNESS_MAX_ITERATIONS`: Max loop iterations

### Goal Status

| Status | Description |
|--------|-------------|
| `ACHIEVED` | Goal achieved |
| `TIMEOUT` | Timeout reached |
| `MAX_ITERATIONS` | Max iterations reached |
| `MAX_RESETS` | Max context resets reached |
| `ERROR` | Agent execution error |
| `VERIFIER_FAULT` | Verifier infrastructure fault |
| `CANCELLED` | User cancelled |

### Automations (Scheduled Execution)

```python
from harness.loop import Automation

# Cron schedule
automation = Automation(
    name="daily-report",
    schedule="0 9 * * *",  # Every day at 9:00
    goal="Generate daily report",
)

# Interval schedule
health_check = Automation(
    name="health-check",
    interval_seconds=300,  # Every 5 minutes
    goal="Check system health",
)

await automation.start(agent)
```

### Worktrees (Parallel Isolated Execution)

Execute multiple goals in parallel in isolated git worktrees:

```python
from harness.loop import WorktreeOrchestrator, WorktreeConfig

orchestrator = WorktreeOrchestrator(agent, ".")

results = await orchestrator.run_parallel([
    WorktreeConfig(name="feature-a", goal="Implement feature A"),
    WorktreeConfig(name="feature-b", goal="Implement feature B"),
])

merge_result = await orchestrator.merge_successful(results)
```

### Connectors (External System Integration)

Integrate with Slack, GitHub, and other external systems:

```python
from harness.connectors import ConnectorManager, SlackConnector, SlackConfig

manager = ConnectorManager(trigger_manager)

slack = SlackConnector(config=SlackConfig(
    bot_token="xoxb-...",
    app_token="xapp-...",
))
manager.register_connector(slack)

await manager.start()
```

### Orchestrator (Workflow Orchestration)

#### Declarative Workflow

```python
from harness.orchestrator import LoopOrchestrator, WorkflowConfig, WorkflowStep

orchestrator = LoopOrchestrator(agent)

workflow = WorkflowConfig(
    name="code-review",
    steps=[
        WorkflowStep(name="analyze", goal="Analyze code structure"),
        WorkflowStep(name="lint", goal="Run lint checks"),
        WorkflowStep(name="review", goal="Code review", depends_on=["analyze", "lint"]),
    ],
)
orchestrator.create_workflow(workflow)

result = await orchestrator.run_workflow("code-review")
```

#### YAML Workflow

```yaml
# cicd.yaml
name: cicd
default_mode: parallel

steps:
  - name: lint
    goal: "Run ruff check"
  - name: test
    goal: "Run pytest"
  - name: deploy
    goal: "Deploy"
    depends_on: [lint, test]
```

```python
result = await orchestrator.run_workflow("cicd.yaml")
```

#### Multi-Agent Team Collaboration

```python
from harness.orchestrator import TeamConfig, AgentRole, CoordinationMode

team = TeamConfig(
    name="dev-team",
    roles=[
        AgentRole(name="architect", description="System design", skills=["architecture"]),
        AgentRole(name="developer", description="Implementation", skills=["coding"]),
    ],
    coordination_mode=CoordinationMode.SEQUENTIAL,
)
orchestrator.create_team(team)

result = await orchestrator.run_team("dev-team", "Implement login feature")
```

## Features

- **Multi-LLM Support**: Anthropic Claude, OpenAI, third-party OpenAI-compatible APIs, custom LLM
- **Agent Loop**: ReAct-style execution loop with progress event tracking
- **Loop Engineering**:
  - Goal-Driven Execution - Autonomous goal achievement
  - Automations - Scheduled/interval triggers
  - Worktrees - Parallel isolated execution
  - Connectors - External system integration (Slack, GitHub, Webhook)
  - Orchestrator - Workflow orchestration (YAML support)
- **Streaming**: Streaming output with backpressure control
- **Interrupt/Recovery**: Interrupt and resume from snapshot
- **Tool System**: Built-in tools + custom tools + JSON Schema validation
- **Skills**: Progressive loading (Level 1: metadata, Level 2: content, Level 3: references)
- **Memory**: Session management, SQLite persistence, async WAL mode
- **Guardrails**: PII detection + LLM Judge content safety (Simplified/Traditional/English)
- **Cost Control**: Multi-level budget control (session, user, global)
- **Observability**: OpenTelemetry integration (Jaeger, Datadog, Langfuse)
- **Testing**: MockHarness + RecordingHarness complete test toolchain
- **MCP Support**: Model Context Protocol with multi-transport (Stdio, HTTP+SSE, Streamable HTTP)
- **Spring Cloud Integration**: W3C TraceContext, Prometheus metrics, Redis distributed storage, Nacos/Eureka service discovery

## Documentation

Detailed design documentation in `docs/` directory.

## License

MIT
