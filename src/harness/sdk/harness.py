"""
Main AgentHarness class - The primary SDK entry point.

This is the main interface users interact with to create and run agents.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from harness.core.agent_loop import AgentLoop, LoopConfig
from harness.llm.anthropic import AnthropicClient
from harness.llm.base import LLMClient, ToolDefinition
from harness.memory.context_builder import ContextBuilder
from harness.memory.session import SessionManager
from harness.memory.store import FileSessionStore
from harness.sdk.config import HarnessConfig
from harness.tools.base import Tool
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry
from harness.types import LoopResult, Session


class AgentHarness:
    """
    The main Harness SDK class.

    This class provides a simple interface to create and run AI agents
    that can use tools, maintain memory, and execute complex tasks.

    Example:
        ```python
        from harness import AgentHarness, ReadTool

        agent = AgentHarness(
            model="claude-sonnet-4-6",
            tools=[ReadTool()],
        )

        result = await agent.run("Read the main.py file")
        print(result.content)
        ```
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        tools: list[Tool] | None = None,
        config: HarnessConfig | None = None,
        **kwargs,
    ):
        """
        Initialize the Harness agent.

        Args:
            model: LLM model to use
            api_key: API key (or set ANTHROPIC_API_KEY env var)
            tools: List of tools to make available
            config: Full configuration object
            **kwargs: Additional config options
        """
        # Merge config
        if config:
            self.config = config
        else:
            self.config = HarnessConfig(
                model=model,
                api_key=api_key,
                **kwargs,
            )

        # Initialize LLM client
        self._llm = self._create_llm_client()

        # Initialize tool registry
        self._tool_registry = ToolRegistry()
        if tools:
            for tool in tools:
                self._tool_registry.register(tool)

        # Initialize tool executor
        self._tool_executor = ToolExecutor(self._tool_registry)

        # Initialize memory
        memory_dir = Path(self.config.memory_dir)
        memory_dir.mkdir(parents=True, exist_ok=True)

        self._session_store = FileSessionStore(str(memory_dir / "sessions"))
        self._session_manager = SessionManager(self._session_store)

        # Initialize context builder
        self._context_builder = ContextBuilder()
        if self.config.system_prompt:
            self._context_builder.set_system_prompt(self.config.system_prompt)

        # Initialize agent loop
        self._loop = AgentLoop(
            llm_client=self._llm,
            tool_executor=self._tool_executor,
            context_builder=self._context_builder,
            session_manager=self._session_manager,
            config=LoopConfig(
                max_iterations=self.config.max_iterations,
                timeout_per_tool=self.config.tool_timeout,
            ),
        )

    def _create_llm_client(self) -> LLMClient:
        """Create the LLM client based on config."""
        # Currently only support Anthropic
        return AnthropicClient(
            api_key=self.config.api_key,
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )

    async def run(
        self,
        prompt: str,
        session_id: str | None = None,
        **kwargs,
    ) -> LoopResult:
        """
        Run the agent with a prompt.

        Args:
            prompt: User input
            session_id: Optional session ID for conversation continuity
            **kwargs: Additional options

        Returns:
            LoopResult: Result of the agent execution
        """
        # Get or create session
        session = self._session_manager.get_or_create(session_id)

        # Get tool definitions
        tool_defs = [
            ToolDefinition(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
            )
            for t in self._tool_registry.get_all()
        ]

        # Run the loop
        result = await self._loop.run(
            prompt=prompt,
            session=session,
            tools=tool_defs if tool_defs else None,
        )

        # Save session
        self._session_manager.update_session(result.session)

        return result

    def run_sync(
        self,
        prompt: str,
        session_id: str | None = None,
        **kwargs,
    ) -> LoopResult:
        """
        Synchronous version of run().

        Note: This should NOT be called from async contexts.
        Use await agent.run() instead.
        """
        import asyncio

        # Check for running event loop
        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "run_sync() cannot be called from async context. "
                "Use 'await agent.run()' instead."
            )
        except RuntimeError as e:
            if "no running event loop" not in str(e):
                raise

        return asyncio.run(self.run(prompt, session_id, **kwargs))

    def register_tool(
        self,
        tool: Tool,
        category: str = "custom",
    ) -> None:
        """
        Register a tool with the agent.

        Args:
            tool: Tool instance to register
            category: Category for organization
        """
        self._tool_registry.register(tool, category)

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
    ) -> Callable:
        """
        Decorator to register a function as a tool.

        Example:
            ```python
            @agent.tool(description="Say hello")
            def hello(name: str) -> str:
                return f"Hello, {name}!"
            ```
        """
        def decorator(func: Callable) -> Callable:
            # Create a tool wrapper
            import inspect

            from harness.tools.base import Tool, ToolContext
            from harness.types import ToolResult

            class FunctionTool(Tool):
                def __init__(self, func, name, description):
                    self._func = func
                    self._name = name or func.__name__
                    self._description = description or func.__doc__ or ""

                @property
                def name(self) -> str:
                    return self._name

                @property
                def description(self) -> str:
                    return self._description

                @property
                def input_schema(self) -> dict[str, Any]:
                    # Generate schema from function signature
                    sig = inspect.signature(self._func)
                    properties = {}
                    required = []

                    for param_name, param in sig.parameters.items():
                        if param_name == "self":
                            continue

                        param_type = "string"  # Default
                        if param.annotation != inspect.Parameter.empty:
                            if param.annotation is int:
                                param_type = "integer"
                            elif param.annotation is float:
                                param_type = "number"
                            elif param.annotation is bool:
                                param_type = "boolean"

                        properties[param_name] = {"type": param_type}

                        if param.default == inspect.Parameter.empty:
                            required.append(param_name)

                    return {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    }

                async def execute(
                    self,
                    arguments: dict[str, Any],
                    context: ToolContext,
                ) -> ToolResult:
                    try:
                        result = self._func(**arguments)
                        return ToolResult(
                            tool_call_id="",
                            success=True,
                            content=str(result),
                        )
                    except Exception as e:
                        return ToolResult(
                            tool_call_id="",
                            success=False,
                            content="",
                            error=str(e),
                        )

            tool_instance = FunctionTool(func, name, description)
            self.register_tool(tool_instance)
            return func

        return decorator

    def get_session(self, session_id: str) -> Session | None:
        """Get an existing session."""
        return self._session_manager.get_session(session_id)

    def clear_session(self, session_id: str) -> None:
        """Clear a session's messages."""
        self._session_manager.clear_session(session_id)

    def interrupt(self) -> None:
        """Interrupt the current execution."""
        self._loop.interrupt()

    @classmethod
    def from_config(cls, path: str) -> "AgentHarness":
        """
        Create an agent from a config file.

        Args:
            path: Path to YAML or JSON config file

        Returns:
            AgentHarness instance
        """
        config = HarnessConfig.from_file(path)
        return cls(config=config)
