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
    RoutingConfig,
    StorageConfig,
)
from harness.tools.base import Tool
from harness.tools.executor import ToolExecutor
from harness.tools.registry import ToolRegistry
from harness.core.hooks import HookPoint, LifecycleHook
from harness.skills import SkillInjector, SkillLoader, SkillRegistry
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
        routing: RoutingConfig | None = None,
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
            routing: Routing configuration for cost optimization (optional)
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
                routing=routing,
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
                offload_config=self._create_offload_config(),
                enable_offload=self.config.offload.enabled if self.config.offload else True,
                working_directory=self.config.sandbox_workspace,
                step_budget_config=self.config.step_budget,  # 传递 step_budget 配置
                memory_md_path=self.config.memory_md_path,  # 传递 memory_md_path
            ),
        )

        # Initialize skill system
        self._skill_registry = SkillRegistry()
        self._skill_loader = SkillLoader(self._skill_registry)
        self._skill_injector = SkillInjector(self._skill_registry)
        self._load_skills()

        # Initialize guardrails if configured
        self._init_guardrails()

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

    def _create_offload_config(self):
        """Create offload config from HarnessConfig."""
        from harness.core.output_offload import OffloadConfig as CoreOffloadConfig

        offload = self.config.offload

        if offload is None:
            # Default: larger threshold to avoid offloading most outputs
            return CoreOffloadConfig(
                size_threshold_chars=50000,
                preview_length=500,
            )

        return CoreOffloadConfig(
            size_threshold_chars=offload.size_threshold_chars,
            preview_length=offload.preview_length,
        )

    def _create_llm_client(
        self,
        model: str | None = None,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> LLMClient:
        """
        Create an LLM client based on config.

        This is the unified method for creating LLM clients, used by both
        standard agent creation and routing downstream clients.

        Reuses model_presets.py for provider auto-detection when provider="auto".

        Args:
            model: Model name (defaults to config.model)
            provider: Provider type - "anthropic", "openai", or "auto" (uses model_presets)
            api_key: API key (defaults to config.api_key)
            base_url: API base URL (defaults to config.base_url)

        Returns:
            LLMClient instance (AnthropicClient or OpenAIClient)
        """
        # If routing is configured and no override, create routing client
        if self.config.routing and model is None:
            return self._create_routing_client()

        # Resolve effective values (override or fallback to config)
        effective_model = model or self.config.model
        effective_provider = provider or self.config.provider
        effective_api_key = api_key or self.config.api_key
        effective_base_url = base_url or self.config.base_url
        max_tokens = self.config.get_max_tokens()

        # Use model_presets for provider auto-detection
        if effective_provider == "auto":
            from harness.model_presets import get_model_preset
            preset = get_model_preset(effective_model)
            effective_provider = preset.provider

        # Create client based on provider
        if effective_provider == "anthropic":
            return AnthropicClient(
                api_key=effective_api_key,
                model=effective_model,
                max_tokens=max_tokens,
                temperature=self.config.temperature,
                tool_result_role=self.config.tool_result_role,
            )
        else:
            # OpenAI format (including third-party compatible APIs)
            return OpenAIClient(
                api_key=effective_api_key,
                model=effective_model,
                base_url=effective_base_url,
                max_tokens=max_tokens,
                temperature=self.config.temperature,
            )

    def _create_routing_client(self) -> LLMClient:
        """Create a routing LLM client for cost optimization."""
        from harness.llm.routing import RoutingLLMClient

        routing_config = self.config.routing

        # Create downstream clients using unified _create_llm_client
        high_client = self._create_llm_client(
            model=routing_config.high_model,
            provider=routing_config.high_provider,
            api_key=routing_config.high_api_key,
            base_url=routing_config.high_base_url,
        )
        low_client = self._create_llm_client(
            model=routing_config.low_model,
            provider=routing_config.low_provider,
            api_key=routing_config.low_api_key,
            base_url=routing_config.low_base_url,
        )

        return RoutingLLMClient(
            config=routing_config,
            high_client=high_client,
            low_client=low_client,
        )

    def _load_skills(self) -> None:
        """Load skills from default directories."""
        self._skill_loader.load_defaults()

    def _init_guardrails(self) -> None:
        """Initialize guardrails hook if configured."""
        guardrails_config = self.config.guardrails
        if guardrails_config is None:
            return

        # Check if guardrails is enabled
        if not getattr(guardrails_config, "enabled", False):
            return

        try:
            from harness.guardrails import GuardrailHook

            hook = GuardrailHook(guardrails_config)
            self.add_hook(hook)

        except ImportError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Guardrails not available (missing dependencies): {e}. "
                "Install with: pip install presidio-analyzer presidio-anonymizer"
            )

    def load_skills_from_dir(self, directory: Path) -> int:
        """
        Load skills from a specific directory.

        Args:
            directory: Path to directory containing skill files

        Returns:
            Number of skills loaded
        """
        return self._skill_loader.load_from_dir(directory)

    def activate_skill(self, skill_name: str) -> bool:
        """
        Activate a skill by name.

        Args:
            skill_name: Name of the skill to activate

        Returns:
            True if activated successfully
        """
        return self._skill_registry.activate(skill_name)

    def deactivate_skill(self, skill_name: str) -> bool:
        """
        Deactivate a skill by name.

        Args:
            skill_name: Name of the skill to deactivate

        Returns:
            True if deactivated successfully
        """
        return self._skill_registry.deactivate(skill_name)

    def get_matching_skills(self, user_input: str) -> list:
        """
        Get skills that match the user input.

        Args:
            user_input: User's input text

        Returns:
            List of matching skills
        """
        return self._skill_registry.find_matching_skills(user_input)

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

        # Inject matching skills into system prompt
        enhanced_system_prompt = self._skill_injector.inject_skills(
            self.config.system_prompt,
            prompt,
        )

        # Update context builder with enhanced system prompt
        context_window = self.config.get_context_window()
        self._context_builder = ContextBuilder(
            config=ContextConfig(
                max_tokens=context_window,
                system_prompt=enhanced_system_prompt,
                window_size=self.config.session_window,
                memory_md_path=self.config.memory_md_path,
            )
        )

        # Update the loop's context builder reference
        self._loop.context = self._context_builder

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

        # Robust event loop detection using semantic API
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop -> safe to run synchronously
            return asyncio.run(self.run(prompt, session_id, **kwargs))
        else:
            # Running loop exists -> disallow sync call
            raise RuntimeError(
                "run_sync() cannot be called from async context. "
                "Use 'await agent.run()' instead."
            )

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
