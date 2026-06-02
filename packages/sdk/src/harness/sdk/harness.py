"""
Main AgentHarness class - The primary SDK entry point.

This is the main interface users interact with to create and run agents.
"""

from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from harness.core.agent_loop import AgentLoop, LoopConfig
from harness.core.observability import ObservabilityManager
from harness.llm.anthropic import AnthropicClient
from harness.llm.base import LLMClient, ToolDefinition
from harness.llm.openai import OpenAIClient
from harness.memory.context_builder import ContextBuilder, ContextConfig
from harness.memory.session import SessionManager
from harness.memory.store import FileSessionStore, SQLiteSessionStore
from harness.progress import create_progress_handler
from harness.sdk.config import (
    CostControlConfig,
    HarnessConfig,
    ObservabilityConfig,
    StorageConfig,
)
from harness.tools.base import Tool
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry
from harness.core.hooks import HookPoint, LifecycleHook
from harness.types import (
    CostConfig,
    LoopResult,
    LoopSnapshot,
    ProgressCallback,
    Session,
)


class AgentHarness:
    """
    The main Harness SDK class.

    This class provides a simple interface to create and run AI agents
    that can use tools, maintain memory, and execute complex tasks.

    Example with Anthropic:
        ```python
        from harness import AgentHarness, ReadTool

        agent = AgentHarness(
            model="claude-sonnet-4-6",
            tools=[ReadTool()],
        )

        result = await agent.run("Read the main.py file")
        print(result.content)
        ```

    Example with OpenAI:
        ```python
        agent = AgentHarness(
            model="gpt-4o",
            provider="openai",
            tools=[ReadTool()],
        )
        ```

    Example with custom LLM:
        ```python
        agent = AgentHarness(
            llm_client=MyCustomLLMClient(),
            tools=[ReadTool()],
        )
        ```
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        provider: str = "anthropic",
        base_url: str | None = None,
        tools: list[Tool] | None = None,
        config: HarnessConfig | None = None,
        llm_client: LLMClient | None = None,
        **kwargs,
    ):
        """
        Initialize the Harness agent.

        Args:
            model: LLM model to use (e.g., "claude-sonnet-4-6", "gpt-4o")
            api_key: API key (or set environment variable)
            provider: LLM provider - "anthropic", "openai", or "custom"
            base_url: Custom API endpoint (for local LLMs, Azure, etc.)
            tools: List of tools to make available
            config: Full configuration object
            llm_client: Custom LLM client instance (overrides provider detection)
            **kwargs: Additional config options
        """
        # Merge config
        if config:
            self.config = config
        else:
            self.config = HarnessConfig(
                model=model,
                api_key=api_key,
                provider=provider,
                base_url=base_url,
                **kwargs,
            )

        # Initialize LLM client
        if llm_client:
            self._llm = llm_client
        else:
            self._llm = self._create_llm_client()

        # Initialize tool registry
        self._tool_registry = ToolRegistry()
        if tools:
            for tool in tools:
                self._tool_registry.register(tool)

        # Initialize tool executor
        self._tool_executor = ToolExecutor(self._tool_registry)

        # Initialize session storage
        self._session_store = self._create_session_store()

        # Initialize session manager
        self._session_manager = SessionManager(self._session_store)

        # Initialize observability
        self._observability = self._setup_observability()

        # Get resolved context window
        context_window = self.config.get_context_window()

        # Initialize context builder with context window
        self._context_builder = ContextBuilder(
            config=ContextConfig(
                max_tokens=context_window,
                system_prompt=self.config.system_prompt,
                window_size=self.config.session_window,
            )
        )

        # Initialize agent loop
        self._loop = AgentLoop(
            llm_client=self._llm,
            tool_executor=self._tool_executor,
            context_builder=self._context_builder,
            session_manager=self._session_manager,
            config=LoopConfig(
                max_iterations=self.config.max_iterations,
                timeout_per_tool=self.config.tool_timeout,
                security_config=self.config.security,
                cost_config=self._create_cost_config(),
            ),
        )

    def _create_session_store(self):
        """Create session store based on storage config."""
        storage_config = self.config.storage

        if storage_config is None:
            # Default: file-based storage
            memory_dir = Path(self.config.memory_dir)
            memory_dir.mkdir(parents=True, exist_ok=True)
            return FileSessionStore(str(memory_dir / "sessions"))

        if storage_config.type == "sqlite":
            # Ensure directory exists
            sqlite_path = Path(storage_config.sqlite_path)
            sqlite_path.parent.mkdir(parents=True, exist_ok=True)

            if storage_config.async_mode:
                try:
                    from harness.memory.store import AsyncSQLiteSessionStore
                    return AsyncSQLiteSessionStore(
                        str(sqlite_path),
                        pool_size=storage_config.pool_size,
                    )
                except ImportError:
                    # Fall back to sync SQLite
                    return SQLiteSessionStore(str(sqlite_path))
            else:
                return SQLiteSessionStore(str(sqlite_path))
        else:
            # File-based storage
            storage_dir = Path(storage_config.storage_dir)
            storage_dir.mkdir(parents=True, exist_ok=True)
            return FileSessionStore(str(storage_dir))

    def _setup_observability(self) -> ObservabilityManager | None:
        """Set up observability based on config."""
        obs_config = self.config.observability

        if obs_config is None:
            # Default: disabled
            return None

        manager = ObservabilityManager(config=obs_config)
        if obs_config.enabled:
            manager.setup()
        return manager

    def _create_cost_config(self) -> CostConfig | None:
        """Create cost config from HarnessConfig."""
        cost_control = self.config.cost_control

        if cost_control is None:
            return None

        return CostConfig(
            max_tokens_per_session=cost_control.max_tokens_per_session,
            max_tool_calls_per_session=cost_control.max_tool_calls_per_session,
            max_iterations_per_request=cost_control.max_iterations_per_request,
            daily_token_limit=cost_control.daily_token_limit,
            hourly_request_limit=cost_control.hourly_request_limit,
            global_daily_budget_usd=cost_control.global_daily_budget_usd,
            auto_throttle=cost_control.auto_throttle,
            fallback_model=cost_control.fallback_model or "claude-haiku-4-5",
            context_reduction_ratio=cost_control.context_reduction_ratio,
            warning_threshold=cost_control.warning_threshold,
        )

    def _create_llm_client(self) -> LLMClient:
        """Create the LLM client based on config."""
        provider = self.config.provider.lower()
        max_tokens = self.config.get_max_tokens()

        # Detect provider from model name if not explicitly set
        if provider == "anthropic" or self.config.model.startswith("claude"):
            return AnthropicClient(
                api_key=self.config.api_key,
                model=self.config.model,
                max_tokens=max_tokens,
                temperature=self.config.temperature,
            )
        elif provider == "openai" or self.config.model.startswith("gpt"):
            return OpenAIClient(
                api_key=self.config.api_key,
                model=self.config.model,
                base_url=self.config.base_url,
                max_tokens=max_tokens,
                temperature=self.config.temperature,
            )
        else:
            raise ValueError(
                f"Unknown provider: {provider}. "
                "Use 'anthropic', 'openai', or provide a custom llm_client."
            )

    async def run(
        self,
        prompt: str,
        session_id: str | None = None,
        on_progress: ProgressCallback | None = None,
        verbose: bool = False,
        **kwargs,
    ) -> LoopResult:
        """
        Run the agent with a prompt.

        Args:
            prompt: User input
            session_id: Optional session ID for conversation continuity
            on_progress: Optional callback for progress events
            verbose: If True, print progress to console (ignored if on_progress is set)
            **kwargs: Additional options

        Returns:
            LoopResult: Result of the agent execution
        """
        # Set up progress callback
        progress_callback = on_progress
        if progress_callback is None and verbose:
            progress_callback = create_progress_handler("emoji")

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
            on_progress=progress_callback,
        )

        # Save session
        self._session_manager.update_session(result.session)

        return result

    async def stream(
        self,
        prompt: str,
        session_id: str | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_progress: ProgressCallback | None = None,
        verbose: bool = False,
    ) -> AsyncIterator[str]:
        """
        Stream the agent's response.

        This yields text chunks as they are generated by the LLM.
        Tool calls are handled internally but not streamed.

        Args:
            prompt: User input
            session_id: Optional session ID for conversation continuity
            on_chunk: Optional callback for each text chunk
            on_progress: Optional callback for progress events
            verbose: If True, print progress to console

        Yields:
            Text chunks from the response
        """
        # Set up progress callback
        progress_callback = on_progress
        if progress_callback is None and verbose:
            progress_callback = create_progress_handler("emoji")

        # Run the agent normally
        result = await self.run(
            prompt=prompt,
            session_id=session_id,
            on_progress=progress_callback,
        )

        # Yield the response in chunks for simulated streaming
        content = result.content
        if content:
            # Split into reasonable chunks (word boundaries)
            words = content.split()
            chunk_size = max(1, len(words) // 50)  # ~50 chunks

            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                if on_chunk:
                    on_chunk(chunk)
                yield chunk

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

    def add_hook(
        self,
        hook: LifecycleHook,
        points: list[HookPoint] | None = None,
    ) -> None:
        """
        Register a lifecycle hook.

        Hooks allow custom logic to be injected at key points in the agent loop:
        - Before/after LLM calls
        - Before/after tool execution
        - On errors
        - On loop start/end

        Args:
            hook: The hook to register (subclass of LifecycleHook)
            points: Specific hook points to register for (uses hook.hook_points if None)

        Example:
            ```python
            from harness import AgentHarness, LifecycleHook, HookPoint, HookContext, HookResult

            class MyHook(LifecycleHook):
                @property
                def hook_points(self) -> list[HookPoint]:
                    return [HookPoint.BEFORE_TOOL_EXECUTE]

                async def execute(self, context: HookContext) -> HookResult:
                    print(f"About to execute: {context.tool_name}")
                    return HookResult.continue_()

            agent = AgentHarness()
            agent.add_hook(MyHook())
            ```
        """
        self._loop.add_hook(hook, points)

    def remove_hook(self, hook: LifecycleHook) -> None:
        """
        Unregister a lifecycle hook.

        Args:
            hook: The hook to unregister
        """
        self._loop.remove_hook(hook)

    def create_snapshot(
        self,
        session_id: str | None = None,
        iteration: int = 0,
    ) -> "LoopSnapshot":
        """
        Create a snapshot of the current loop state.

        Snapshots can be used to save progress and resume later.

        Args:
            session_id: Session ID (uses current session if None)
            iteration: Current iteration number

        Returns:
            LoopSnapshot capturing the current state

        Example:
            ```python
            agent = AgentHarness()
            result = await agent.run("Long task...", session_id="my-session")

            # Save snapshot for later
            snapshot = agent.create_snapshot(session_id="my-session")
            snapshot_dict = snapshot.to_dict()

            # Resume later
            from harness import LoopSnapshot
            loaded = LoopSnapshot.from_dict(snapshot_dict)
            ```
        """
        from harness.types import LoopSnapshot

        session = None
        if session_id:
            session = self._session_manager.get_session(session_id)
        if session is None:
            session = self._session_manager.get_or_create(session_id)

        return self._loop.create_snapshot(
            session=session,
            iteration=iteration,
        )

    async def restore_from_snapshot(
        self,
        snapshot: LoopSnapshot,
        tools: list[ToolDefinition] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> LoopResult:
        """
        Resume execution from a snapshot.

        This allows continuing a previously interrupted execution.

        Args:
            snapshot: Snapshot to resume from
            tools: Available tools (uses registered tools if None)
            on_chunk: Streaming callback
            on_progress: Progress callback

        Returns:
            LoopResult from resumed execution

        Example:
            ```python
            # Save snapshot
            snapshot = agent.create_snapshot(session_id="my-session")

            # Later, resume from snapshot
            result = await agent.restore_from_snapshot(snapshot)
            ```
        """
        # Restore session from snapshot
        session = self._session_manager.get_or_create(snapshot.session_id)
        session.messages = snapshot.messages.copy()

        # Get tool definitions
        tool_defs = tools or [
            ToolDefinition(
                name=t.name,
                description=t.description,
                input_schema=t.input_schema,
            )
            for t in self._tool_registry.get_all()
        ]

        # Resume from snapshot
        return await self._loop.resume_from_snapshot(
            snapshot=snapshot,
            tools=tool_defs if tool_defs else None,
            on_chunk=on_chunk,
            on_progress=on_progress,
        )

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
