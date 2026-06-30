# Phase 5: Loop Orchestrator 设计文档

> **状态**: 设计阶段
> **创建时间**: 2026-06-30
> **依赖**: Phase 1-4 全部组件

---

## 背景

Phase 1-4 已实现完整的 Agent 自主执行能力：

| Phase | 组件 | 功能 |
|-------|------|------|
| Phase 1 | Goal Verifier | 目标驱动执行 |
| Phase 2 | Automations | 定时触发/调度 |
| Phase 3 | Worktrees | 多 Agent 并行隔离 |
| Phase 4 | Connectors | 外部系统集成 |

Phase 5 Loop Orchestrator 的核心需求是：**提供统一 API，整合所有组件，支持复杂工作流编排**。

**设计目标**：
1. 统一入口：一个 API 控制所有组件
2. 工作流定义：声明式描述多步骤任务
3. 多 Agent 协调：支持 Agent 间通信和协作
4. 可观测性：统一的监控和日志

---

## 架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Loop Orchestrator                                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      Orchestrator API                          │  │
│  │  - create_workflow()                                           │  │
│  │  - run_workflow()                                              │  │
│  │  - create_team()                                               │  │
│  │  - run_team()                                                  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                │                                     │
│         ┌──────────────────────┼──────────────────────┐             │
│         ▼                      ▼                      ▼             │
│  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐     │
│  │  Workflow   │        │    Team     │        │   Monitor   │     │
│  │   Engine    │        │  Orchestrator│       │   Service   │     │
│  └─────────────┘        └─────────────┘        └─────────────┘     │
│         │                      │                      │             │
│         └──────────────────────┼──────────────────────┘             │
│                                │                                     │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Phase 2:      │     │   Phase 3:      │     │   Phase 4:      │
│ TriggerManager  │     │ Worktree        │     │ Connector       │
│ + Automation    │     │ Orchestrator    │     │ Manager         │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                     ┌─────────────────────┐
                     │   Phase 1: GoalLoop │
                     │   + GoalVerifier    │
                     └─────────────────────┘
```

### 组件关系

```
LoopOrchestrator
    ├── agent: AgentHarness
    ├── trigger_manager: TriggerManager (Phase 2)
    ├── worktree_orchestrator: WorktreeOrchestrator (Phase 3)
    ├── connector_manager: ConnectorManager (Phase 4)
    ├── workflow_engine: WorkflowEngine
    ├── team_orchestrator: TeamOrchestrator
    └── monitor: MonitorService
```

---

## 核心类型定义

```python
# orchestrator/types.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class WorkflowStatus(Enum):
    """工作流状态."""
    PENDING = "pending"         # 等待执行
    RUNNING = "running"         # 执行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消


class StepStatus(Enum):
    """步骤状态."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExecutionMode(Enum):
    """执行模式."""
    SEQUENTIAL = "sequential"   # 顺序执行
    PARALLEL = "parallel"       # 并行执行
    CONDITIONAL = "conditional" # 条件执行


@dataclass
class WorkflowStep:
    """
    工作流步骤.
    
    每个步骤是一个 Goal 执行单元。
    """
    name: str                           # 步骤名称
    goal: str                           # 目标描述
    
    # 执行配置
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    depends_on: list[str] = field(default_factory=list)  # 依赖的步骤
    
    # Goal 配置
    workspace_dir: str = "."
    max_iterations: int = 50
    timeout_seconds: int = 3600
    custom_verifier: Callable | None = None
    
    # 技能配置
    skills: list[str] = field(default_factory=list)
    
    # 条件执行（当 mode=CONDITIONAL）
    condition: str | None = None        # Python 表达式，如 "steps['analyze'].result.success"
    
    # 重试配置
    max_retries: int = 0
    retry_delay: float = 5.0


@dataclass
class WorkflowConfig:
    """
    工作流配置.
    
    定义一个完整的工作流。
    """
    name: str                           # 工作流名称
    description: str = ""               # 描述
    
    # 步骤定义
    steps: list[WorkflowStep] = field(default_factory=list)
    
    # 执行配置
    default_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_parallel_steps: int = 5         # 最大并行步骤数
    
    # 全局配置
    workspace_dir: str = "."
    
    # 触发配置（可选）
    trigger_on: str | None = None       # cron 表达式或事件类型
    
    # 输出配置
    output_channels: list[str] = field(default_factory=list)


@dataclass
class StepResult:
    """步骤执行结果."""
    step_name: str
    status: StepStatus
    goal_result: GoalResult | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class WorkflowResult:
    """工作流执行结果."""
    workflow_name: str
    status: WorkflowStatus
    steps: dict[str, StepResult]
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    
    @property
    def success(self) -> bool:
        return self.status == WorkflowStatus.COMPLETED
    
    @property
    def duration_seconds(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


# =============================================================================
# Team Orchestration Types
# =============================================================================

@dataclass
class AgentRole:
    """Agent 角色."""
    name: str                           # 角色名称（如 "analyzer", "developer"）
    description: str                    # 角色描述
    
    # 技能配置
    skills: list[str] = field(default_factory=list)
    
    # 工具配置（可选，用于限制工具）
    allowed_tools: list[str] | None = None
    
    # 系统提示词（可选）
    system_prompt: str | None = None
    
    # 迭代限制
    max_iterations: int = 20


@dataclass
class TeamConfig:
    """
    Agent 团队配置.
    
    定义多 Agent 协作团队。
    """
    name: str                           # 团队名称
    description: str = ""
    
    # 角色定义
    roles: list[AgentRole] = field(default_factory=list)
    
    # 协作模式
    coordination_mode: str = "broadcast"  # "broadcast" | "sequential" | "hierarchical"
    
    # 通信配置
    shared_memory: bool = True          # 是否共享记忆
    message_bus: str = "internal"       # "internal" | "redis" | "eventbus"


@dataclass
class TeamResult:
    """团队执行结果."""
    team_name: str
    success: bool
    agent_results: dict[str, GoalResult]
    total_iterations: int
    total_tokens: int
    duration_seconds: float
    error: str | None = None
```

---

## WorkflowEngine

```python
# orchestrator/workflow_engine.py

class WorkflowEngine:
    """
    工作流执行引擎.
    
    负责解析和执行 WorkflowConfig。
    """
    
    def __init__(
        self,
        orchestrator: "LoopOrchestrator",
    ):
        self.orchestrator = orchestrator
        self._active_workflows: dict[str, asyncio.Task] = {}
    
    async def run(
        self,
        config: WorkflowConfig,
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """
        执行工作流.
        
        Args:
            config: 工作流配置
            context: 执行上下文（可传递给步骤）
        
        Returns:
            工作流执行结果
        """
        result = WorkflowResult(
            workflow_name=config.name,
            status=WorkflowStatus.RUNNING,
            steps={},
            started_at=datetime.now(),
        )
        
        try:
            # 构建步骤依赖图
            graph = self._build_dependency_graph(config.steps)
            
            # 检测死锁
            if graph.detect_deadlock():
                raise RuntimeError("Deadlock detected: circular dependency in workflow")
            
            # 执行步骤
            while graph.has_pending():
                # 获取可执行的步骤（依赖已满足）
                ready_steps = graph.get_ready_steps()
                
                if not ready_steps:
                    # 没有可执行步骤但有未完成步骤 = 死锁
                    raise RuntimeError("Deadlock detected: unreachable steps in workflow")
                
                # 根据执行模式执行
                if config.default_mode == ExecutionMode.PARALLEL:
                    await self._execute_parallel(ready_steps, config, result, context, graph)
                else:
                    await self._execute_sequential(ready_steps, config, result, context, graph)
            
            # 检查所有步骤是否成功
            all_success = all(
                s.status == StepStatus.SUCCESS 
                for s in result.steps.values()
            )
            result.status = WorkflowStatus.COMPLETED if all_success else WorkflowStatus.FAILED
        
        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
        
        result.completed_at = datetime.now()
        return result
    
    async def _execute_sequential(
        self,
        steps: list[WorkflowStep],
        config: WorkflowConfig,
        result: WorkflowResult,
        context: dict[str, Any] | None,
        graph: DependencyGraph,
    ) -> None:
        """顺序执行步骤."""
        for step in steps:
            step_result = await self._execute_step(step, config, result, context)
            result.steps[step.name] = step_result
            graph.mark_completed(step.name)
            
            if step_result.status == StepStatus.FAILED:
                # 步骤失败，停止执行
                break
    
    async def _execute_parallel(
        self,
        steps: list[WorkflowStep],
        config: WorkflowConfig,
        result: WorkflowResult,
        context: dict[str, Any] | None,
        graph: DependencyGraph,
    ) -> None:
        """并行执行步骤."""
        semaphore = asyncio.Semaphore(config.max_parallel_steps)
        
        async def run_step(step: WorkflowStep) -> tuple[str, StepResult]:
            async with semaphore:
                step_result = await self._execute_step(step, config, result, context)
                graph.mark_completed(step.name)
                return step.name, step_result
        
        tasks = [run_step(step) for step in steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for step_name, step_result in results:
            if isinstance(step_result, Exception):
                result.steps[step_name] = StepResult(
                    step_name=step_name,
                    status=StepStatus.FAILED,
                    error=str(step_result),
                )
            else:
                result.steps[step_name] = step_result
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        config: WorkflowConfig,
        result: WorkflowResult,
        context: dict[str, Any] | None,
    ) -> StepResult:
        """执行单个步骤."""
        step_result = StepResult(
            step_name=step.name,
            status=StepStatus.RUNNING,
            started_at=datetime.now(),
        )
        
        try:
            # 检查条件
            if step.condition:
                if not self._evaluate_condition(step.condition, result, context):
                    step_result.status = StepStatus.SKIPPED
                    return step_result
            
            # 执行 Goal
            goal_config = GoalConfig(
                description=step.goal,
                workspace_dir=step.workspace_dir or config.workspace_dir,
                max_iterations=step.max_iterations,
                timeout_seconds=step.timeout_seconds,
                custom_verifier=step.custom_verifier,
            )
            
            # 激活技能
            for skill_name in step.skills:
                self.orchestrator.agent.activate_skill(skill_name)
            
            # 执行
            goal_result = await self.orchestrator.agent.run_goal(goal_config)
            
            step_result.goal_result = goal_result
            step_result.status = StepStatus.SUCCESS if goal_result.achieved else StepStatus.FAILED
        
        except Exception as e:
            step_result.status = StepStatus.FAILED
            step_result.error = str(e)
        
        step_result.completed_at = datetime.now()
        return step_result
    
    def _evaluate_condition(
        self,
        condition: str,
        result: WorkflowResult,
        context: dict[str, Any] | None,
    ) -> bool:
        """评估条件表达式."""
        # 构建评估上下文
        eval_context = {
            "steps": result.steps,
            "context": context or {},
            "StepStatus": StepStatus,
        }
        
        try:
            return bool(eval(condition, {"__builtins__": {}}, eval_context))
        except Exception:
            return False
    
    def _build_dependency_graph(
        self,
        steps: list[WorkflowStep],
    ) -> "DependencyGraph":
        """构建步骤依赖图."""
        graph = DependencyGraph()
        
        for step in steps:
            graph.add_step(step)
            for dep in step.depends_on:
                graph.add_dependency(step.name, dep)
        
        return graph
```

---

## TeamOrchestrator

```python
# orchestrator/team_orchestrator.py

class TeamOrchestrator:
    """
    多 Agent 团队编排器.
    
    管理多个 Agent 的协作执行。
    """
    
    def __init__(
        self,
        orchestrator: "LoopOrchestrator",
    ):
        self.orchestrator = orchestrator
        self._teams: dict[str, TeamConfig] = {}
        self._agents: dict[str, AgentHarness] = {}
    
    def create_team(
        self,
        config: TeamConfig,
    ) -> str:
        """创建 Agent 团队."""
        self._teams[config.name] = config
        
        # 为每个角色创建 Agent
        for role in config.roles:
            agent = self._create_agent_for_role(role)
            self._agents[role.name] = agent
        
        return config.name
    
    def _create_agent_for_role(
        self,
        role: AgentRole,
    ) -> AgentHarness:
        """为角色创建专用 Agent."""
        config = HarnessConfig(
            model=self.orchestrator.agent.config.model,
            system_prompt=role.system_prompt or f"You are a {role.name}. {role.description}",
            max_iterations=role.max_iterations,
        )
        
        # 创建 Agent
        agent = AgentHarness(
            llm_client=self.orchestrator.agent._llm_client,
            config=config,
        )
        
        # 激活技能
        for skill_name in role.skills:
            agent.activate_skill(skill_name)
        
        return agent
    
    async def run(
        self,
        team_name: str,
        task: str,
        coordination_mode: str | None = None,
    ) -> TeamResult:
        """
        让团队执行任务.
        
        Args:
            team_name: 团队名称
            task: 任务描述
            coordination_mode: 协作模式（覆盖团队配置）
        
        Returns:
            团队执行结果
        """
        config = self._teams.get(team_name)
        if not config:
            raise ValueError(f"Team not found: {team_name}")
        
        mode = coordination_mode or config.coordination_mode
        start_time = datetime.now()
        
        try:
            if mode == "broadcast":
                results = await self._run_broadcast(config, task)
            elif mode == "sequential":
                results = await self._run_sequential(config, task)
            elif mode == "hierarchical":
                results = await self._run_hierarchical(config, task)
            else:
                raise ValueError(f"Unknown coordination mode: {mode}")
            
            # 计算统计
            total_iterations = sum(
                r.total_iterations for r in results.values()
            )
            total_tokens = sum(
                r.total_tokens for r in results.values()
            )
            
            return TeamResult(
                team_name=team_name,
                success=all(r.achieved for r in results.values()),
                agent_results=results,
                total_iterations=total_iterations,
                total_tokens=total_tokens,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
            )
        
        except Exception as e:
            return TeamResult(
                team_name=team_name,
                success=False,
                agent_results={},
                total_iterations=0,
                total_tokens=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                error=str(e),
            )
    
    async def _run_broadcast(
        self,
        config: TeamConfig,
        task: str,
    ) -> dict[str, GoalResult]:
        """
        广播模式：所有 Agent 同时执行相同任务.
        
        适用场景：多角度分析、投票决策。
        """
        tasks = []
        for role in config.roles:
            agent = self._agents[role.name]
            tasks.append(self._run_agent(agent, task))
        
        results = await asyncio.gather(*tasks)
        
        return {
            role.name: result
            for role, result in zip(config.roles, results)
        }
    
    async def _run_sequential(
        self,
        config: TeamConfig,
        task: str,
    ) -> dict[str, GoalResult]:
        """
        顺序模式：Agent 按顺序执行，前者输出作为后者输入.
        
        适用场景：流水线处理、多阶段审核。
        """
        results = {}
        current_task = task
        
        for role in config.roles:
            agent = self._agents[role.name]
            result = await self._run_agent(agent, current_task)
            results[role.name] = result
            
            # 将结果传递给下一个 Agent
            if result.achieved:
                current_task = f"{task}\n\nPrevious agent ({role.name}) output:\n{result.final_response}"
        
        return results
    
    async def _run_hierarchical(
        self,
        config: TeamConfig,
        task: str,
    ) -> dict[str, GoalResult]:
        """
        层级模式：Leader Agent 分配任务给其他 Agent.
        
        适用场景：复杂任务分解、专家调度。
        """
        # 假设第一个角色是 Leader
        if not config.roles:
            return {}
        
        leader_role = config.roles[0]
        leader_agent = self._agents[leader_role.name]
        
        # Leader 分析任务并分配
        allocation_prompt = f"""
You are the team leader. Analyze the following task and assign subtasks to team members.

Team members:
{self._format_roles(config.roles[1:])}

Task: {task}

Provide your allocation in the following format:
- [agent_name]: [subtask]
"""
        
        allocation_result = await leader_agent.run(allocation_prompt)
        results = {leader_role.name: allocation_result}
        
        # 解析分配并执行（简化版，实际应使用结构化输出）
        # ... 解析逻辑 ...
        
        # 执行分配的任务
        for role in config.roles[1:]:
            agent = self._agents[role.name]
            subtask = f"Complete your assigned part of: {task}"
            result = await self._run_agent(agent, subtask)
            results[role.name] = result
        
        return results
    
    async def _run_agent(
        self,
        agent: AgentHarness,
        task: str,
    ) -> GoalResult:
        """运行单个 Agent."""
        return await agent.run_goal(task)
    
    def _format_roles(self, roles: list[AgentRole]) -> str:
        """格式化角色列表."""
        return "\n".join(
            f"- {r.name}: {r.description}"
            for r in roles
        )
```

---

## LoopOrchestrator 主类

```python
# orchestrator/core.py

class LoopOrchestrator:
    """
    Loop Orchestrator - 统一编排 API.
    
    整合 Phase 1-4 所有组件，提供统一的入口。
    
    Example:
        ```python
        from harness import AgentHarness
        from harness.orchestrator import LoopOrchestrator
        
        agent = AgentHarness(model="claude-sonnet-4-6")
        orchestrator = LoopOrchestrator(agent)
        
        # 运行工作流
        result = await orchestrator.run_workflow("my-workflow.yaml")
        
        # 运行团队
        orchestrator.create_team(team_config)
        result = await orchestrator.run_team("dev-team", "实现用户认证")
        ```
    """
    
    def __init__(
        self,
        agent: AgentHarness,
        config: OrchestratorConfig | None = None,
    ):
        self.agent = agent
        self.config = config or OrchestratorConfig()
        
        # 初始化子组件
        self.trigger_manager = TriggerManager(
            agent,
            max_concurrent_goals=self.config.max_concurrent_goals,
        )
        self.worktree_orchestrator: WorktreeOrchestrator | None = None
        self.connector_manager: ConnectorManager | None = None
        
        # 初始化引擎
        self.workflow_engine = WorkflowEngine(self)
        self.team_orchestrator = TeamOrchestrator(self)
        
        # 监控
        self.monitor = MonitorService(self)
        
        # 注册状态
        self._running = False
        self._workflows: dict[str, WorkflowConfig] = {}
        self._teams: dict[str, TeamConfig] = {}
    
    # =========================================================================
    # Workflow API
    # =========================================================================
    
    def create_workflow(
        self,
        config: WorkflowConfig,
    ) -> str:
        """
        创建工作流.
        
        Args:
            config: 工作流配置
        
        Returns:
            工作流名称
        """
        self._workflows[config.name] = config
        
        # 如果配置了触发器，注册到 TriggerManager
        if config.trigger_on:
            self._register_workflow_trigger(config)
        
        return config.name
    
    def create_workflow_from_yaml(
        self,
        yaml_path: str,
    ) -> str:
        """
        从 YAML 文件创建工作流.
        
        Args:
            yaml_path: YAML 文件路径
        
        Returns:
            工作流名称
        """
        config = self._parse_workflow_yaml(yaml_path)
        return self.create_workflow(config)
    
    async def run_workflow(
        self,
        name: str,
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """
        执行工作流.
        
        Args:
            name: 工作流名称
            context: 执行上下文
        
        Returns:
            工作流执行结果
        """
        config = self._workflows.get(name)
        if not config:
            raise ValueError(f"Workflow not found: {name}")
        
        return await self.workflow_engine.run(config, context)
    
    # =========================================================================
    # Team API
    # =========================================================================
    
    def create_team(
        self,
        config: TeamConfig,
    ) -> str:
        """
        创建 Agent 团队.
        
        Args:
            config: 团队配置
        
        Returns:
            团队名称
        """
        self._teams[config.name] = config
        return self.team_orchestrator.create_team(config)
    
    async def run_team(
        self,
        name: str,
        task: str,
        mode: str | None = None,
    ) -> TeamResult:
        """
        让团队执行任务.
        
        Args:
            name: 团队名称
            task: 任务描述
            mode: 协作模式（可选）
        
        Returns:
            团队执行结果
        """
        return await self.team_orchestrator.run(name, task, mode)
    
    # =========================================================================
    # Connector API
    # =========================================================================
    
    def register_connector(
        self,
        connector: Connector,
    ) -> str:
        """注册 Connector."""
        if not self.connector_manager:
            self.connector_manager = ConnectorManager(self.trigger_manager)
        return self.connector_manager.register_connector(connector)
    
    def register_output_channel(
        self,
        channel: OutputChannel,
    ) -> str:
        """注册输出通道."""
        if not self.connector_manager:
            self.connector_manager = ConnectorManager(self.trigger_manager)
        return self.connector_manager.register_output_channel(channel)
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self) -> None:
        """启动 Orchestrator 及所有子组件."""
        self._running = True
        
        # 启动 TriggerManager
        await self.trigger_manager.start()
        
        # 启动 ConnectorManager
        if self.connector_manager:
            await self.connector_manager.start()
        
        # 启动监控
        await self.monitor.start()
        
        logger.info(f"LoopOrchestrator started")
    
    async def stop(self) -> None:
        """停止 Orchestrator 及所有子组件."""
        self._running = False
        
        # 停止 ConnectorManager
        if self.connector_manager:
            await self.connector_manager.stop()
        
        # 停止 TriggerManager
        await self.trigger_manager.stop()
        
        # 停止监控
        await self.monitor.stop()
        
        logger.info("LoopOrchestrator stopped")
    
    # =========================================================================
    # Monitoring
    # =========================================================================
    
    def get_status(self) -> OrchestratorStatus:
        """获取 Orchestrator 状态."""
        return OrchestratorStatus(
            running=self._running,
            active_workflows=len(self.workflow_engine._active_workflows),
            registered_triggers=self.trigger_manager.trigger_count,
            registered_connectors=len(self.connector_manager._connectors) if self.connector_manager else 0,
        )
    
    def _register_workflow_trigger(self, config: WorkflowConfig) -> None:
        """为工作流注册触发器."""
        trigger_on = config.trigger_on
        
        if trigger_on.startswith("cron:"):
            # Cron 触发
            schedule = trigger_on[5:]
            trigger = CronTrigger(
                schedule=schedule,
                action=TriggerAction(
                    goal=f"Execute workflow: {config.name}",
                    output_channels=config.output_channels,
                ),
            )
            self.trigger_manager.register(trigger)
        
        elif trigger_on.startswith("event:"):
            # 事件触发
            event_type = trigger_on[6:]
            # 需要 ConnectorManager 支持
            # ...
```

---

## DependencyGraph

```python
# orchestrator/dependency_graph.py

class DependencyGraph:
    """
    步骤依赖图.
    
    用于解析 WorkflowStep 之间的依赖关系，
    支持拓扑排序和死锁检测。
    """
    
    def __init__(self):
        self._steps: dict[str, WorkflowStep] = {}
        self._dependencies: dict[str, set[str]] = {}
        self._completed: set[str] = set()
    
    def add_step(self, step: WorkflowStep) -> None:
        """添加步骤."""
        self._steps[step.name] = step
        if step.name not in self._dependencies:
            self._dependencies[step.name] = set()
    
    def add_dependency(self, step_name: str, depends_on: str) -> None:
        """添加依赖关系."""
        if step_name not in self._dependencies:
            self._dependencies[step_name] = set()
        self._dependencies[step_name].add(depends_on)
    
    def has_pending(self) -> bool:
        """是否还有待执行的步骤."""
        return len(self._completed) < len(self._steps)
    
    def get_ready_steps(self) -> list[WorkflowStep]:
        """
        获取可执行的步骤.
        
        可执行的条件：依赖的步骤已全部完成。
        """
        ready = []
        for name, step in self._steps.items():
            if name in self._completed:
                continue
            deps = self._dependencies.get(name, set())
            if deps.issubset(self._completed):
                ready.append(step)
        return ready
    
    def mark_completed(self, step_name: str) -> None:
        """标记步骤已完成."""
        self._completed.add(step_name)
    
    def detect_deadlock(self) -> bool:
        """
        检测是否存在死锁.
        
        死锁条件：存在循环依赖。
        """
        # 使用拓扑排序检测环
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for dep in self._dependencies.get(node, set()):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step_name in self._steps:
            if step_name not in visited:
                if has_cycle(step_name):
                    return True
        
        return False
```

---

## MonitorService

```python
# orchestrator/monitor.py

@dataclass
class OrchestratorConfig:
    """Orchestrator 配置."""
    max_concurrent_goals: int = 5       # 最大并发 Goal 数
    max_parallel_steps: int = 5         # 最大并行步骤数
    max_teams: int = 10                 # 最大团队数
    metrics_retention: int = 1000       # 保留最近 N 条指标


@dataclass
class OrchestratorStatus:
    """Orchestrator 状态."""
    running: bool
    active_workflows: int
    registered_triggers: int
    registered_connectors: int


@dataclass
class ExecutionMetric:
    """执行指标."""
    name: str
    type: str  # "workflow" | "team" | "goal"
    status: str
    duration_seconds: float
    iterations: int
    tokens_used: int
    timestamp: datetime


class MonitorService:
    """
    监控服务.
    
    提供统一的可观测性：
    - 执行历史
    - 性能指标
    - 错误追踪
    """
    
    def __init__(self, orchestrator: LoopOrchestrator):
        self.orchestrator = orchestrator
        self._metrics: list[ExecutionMetric] = []
        self._running = False
    
    async def start(self) -> None:
        """启动监控."""
        self._running = True
    
    async def stop(self) -> None:
        """停止监控."""
        self._running = False
    
    def record(self, metric: ExecutionMetric) -> None:
        """记录执行指标."""
        self._metrics.append(metric)
        
        # 保持最近 1000 条记录
        if len(self._metrics) > 1000:
            self._metrics = self._metrics[-1000:]
    
    def get_metrics(
        self,
        limit: int = 100,
        type_filter: str | None = None,
    ) -> list[ExecutionMetric]:
        """获取执行指标."""
        metrics = self._metrics
        
        if type_filter:
            metrics = [m for m in metrics if m.type == type_filter]
        
        return metrics[-limit:]
    
    def get_summary(self) -> dict[str, Any]:
        """获取执行摘要."""
        if not self._metrics:
            return {}
        
        total_duration = sum(m.duration_seconds for m in self._metrics)
        total_tokens = sum(m.tokens_used for m in self._metrics)
        success_count = sum(1 for m in self._metrics if m.status == "success")
        
        return {
            "total_executions": len(self._metrics),
            "success_rate": success_count / len(self._metrics),
            "total_duration_seconds": total_duration,
            "total_tokens": total_tokens,
            "average_duration": total_duration / len(self._metrics),
        }
```

---

## 文件结构

```
packages/sdk/src/harness/orchestrator/
├── __init__.py           # 模块入口
├── types.py              # OrchestratorConfig, WorkflowConfig, TeamConfig 等
├── core.py               # LoopOrchestrator 主类
├── workflow_engine.py    # WorkflowEngine
├── team_orchestrator.py  # TeamOrchestrator
├── dependency_graph.py   # DependencyGraph - 步骤依赖图
└── monitor.py            # MonitorService
```

---

## API 使用示例

### 基础工作流

```python
from harness import AgentHarness
from harness.orchestrator import LoopOrchestrator, WorkflowConfig, WorkflowStep

agent = AgentHarness(model="claude-sonnet-4-6")
orchestrator = LoopOrchestrator(agent)

# 定义工作流
workflow = WorkflowConfig(
    name="code-review-pipeline",
    description="代码审查流水线",
    steps=[
        WorkflowStep(
            name="analyze",
            goal="分析代码变更，识别潜在问题",
            skills=["code-analysis"],
        ),
        WorkflowStep(
            name="review",
            goal="根据分析结果进行代码审查",
            depends_on=["analyze"],
            skills=["code-review"],
        ),
        WorkflowStep(
            name="report",
            goal="生成审查报告",
            depends_on=["review"],
            output_channels=["slack:reviews"],
        ),
    ],
)

orchestrator.create_workflow(workflow)
await orchestrator.start()

# 执行工作流
result = await orchestrator.run_workflow("code-review-pipeline")
print(f"Status: {result.status}, Duration: {result.duration_seconds}s")
```

### 从 YAML 定义工作流

```yaml
# workflows/code-review.yaml
name: code-review-pipeline
description: 代码审查流水线

steps:
  - name: analyze
    goal: 分析代码变更，识别潜在问题
    skills:
      - code-analysis
  
  - name: review
    goal: 根据分析结果进行代码审查
    depends_on: [analyze]
    skills:
      - code-review
  
  - name: report
    goal: 生成审查报告
    depends_on: [review]

output_channels:
  - slack:reviews

trigger_on: "event:github.pull_request.opened"
```

```python
# 加载并执行
orchestrator.create_workflow_from_yaml("workflows/code-review.yaml")
await orchestrator.start()
```

### 多 Agent 团队

```python
from harness.orchestrator import TeamConfig, AgentRole

# 定义团队
team = TeamConfig(
    name="dev-team",
    description="开发团队",
    roles=[
        AgentRole(
            name="architect",
            description="架构师，负责系统设计",
            skills=["system-design"],
            system_prompt="You are a senior software architect...",
        ),
        AgentRole(
            name="developer",
            description="开发者，负责实现",
            skills=["coding", "testing"],
        ),
        AgentRole(
            name="reviewer",
            description="审查者，负责代码审查",
            skills=["code-review"],
        ),
    ],
    coordination_mode="sequential",
)

orchestrator.create_team(team)

# 执行任务
result = await orchestrator.run_team(
    "dev-team",
    "实现用户认证模块",
    mode="sequential",
)

print(f"Success: {result.success}")
print(f"Total iterations: {result.total_iterations}")
```

### 与 Connectors 集成

```python
from harness.connectors import SlackConnector, GitHubConnector

# 注册 Connector
slack = SlackConnector(config=SlackConfig(bot_token="xoxb-..."))
github = GitHubConnector(config=GitHubConfig(...))

orchestrator.register_connector(slack)
orchestrator.register_connector(github)

# 注册输出通道
orchestrator.register_output_channel(OutputChannel(
    type="slack",
    name="reviews",
    config={"channel": "#code-reviews"},
))

# 启动（自动启动所有组件）
await orchestrator.start()

# 当 GitHub PR 打开时，自动触发工作流
# （通过 trigger_on: "event:github.pull_request.opened"）
```

---

## 设计决策

### 1. 为什么需要 Orchestrator？

**原因**：
1. **统一入口**: 用户不需要手动管理多个组件
2. **生命周期管理**: 统一的 start/stop 流程
3. **配置简化**: 一个地方配置所有组件
4. **可观测性**: 统一的监控和日志

### 2. Workflow vs Team？

| 概念 | 用途 | 特点 |
|------|------|------|
| Workflow | 多步骤任务 | 步骤间有依赖，顺序或并行执行 |
| Team | 多 Agent 协作 | 每个 Agent 有独立角色和技能 |

**选择指南**：
- 需要多阶段处理？用 Workflow
- 需要不同视角？用 Team (broadcast)
- 需要流水线？用 Team (sequential)
- 需要专家调度？用 Team (hierarchical)

### 3. 为什么用声明式工作流？

```yaml
# 声明式（推荐）
steps:
  - name: analyze
    goal: 分析代码
  - name: review
    depends_on: [analyze]
```

```python
# 命令式（不推荐）
await analyze()
await review()
```

**原因**：
1. **可序列化**: 可保存为文件，版本控制
2. **可视化**: 可生成流程图
3. **可重试**: 记录状态，支持断点续执行
4. **可并行**: 引擎自动识别可并行步骤

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 工作流死锁 | 高 | 依赖图检测 + 超时 |
| Agent 间通信丢失 | 中 | 消息持久化 + 重试 |
| 资源耗尽 | 高 | 并发限制 + 资源配额 |
| 状态不一致 | 中 | 事务 + 补偿操作 |
| 监控数据膨胀 | 低 | 滑动窗口 + 持久化到 DB |

---

## 实施步骤

### Step 1: 创建类型定义
- [ ] 创建 `orchestrator/types.py`
- [ ] 定义 WorkflowConfig, TeamConfig 等

### Step 2: 实现 WorkflowEngine
- [ ] 创建 `orchestrator/workflow_engine.py`
- [ ] 实现依赖图解析
- [ ] 实现顺序/并行执行

### Step 3: 实现 TeamOrchestrator
- [ ] 创建 `orchestrator/team_orchestrator.py`
- [ ] 实现三种协作模式

### Step 4: 实现 LoopOrchestrator
- [ ] 创建 `orchestrator/core.py`
- [ ] 整合所有组件
- [ ] 实现 YAML 解析

### Step 5: 实现 MonitorService
- [ ] 创建 `orchestrator/monitor.py`
- [ ] 实现指标收集
- [ ] 实现状态查询

### Step 6: 集成测试
- [ ] 工作流端到端测试
- [ ] 团队协作测试
- [ ] 与 Phase 2-4 集成测试

---

## 后续扩展

### Phase 5.1: 高级工作流
- 条件分支（if-else）
- 循环（while/for）
- 子工作流调用

### Phase 5.2: 持久化
- 工作流状态持久化
- 断点续执行
- 分布式锁

### Phase 5.3: 可视化
- 工作流编辑器
- 执行可视化
- 监控仪表板
