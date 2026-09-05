"""
Workflow Engine - Workflow execution engine.

This module provides the WorkflowEngine class for:
- Parsing and executing WorkflowConfig
- Managing step dependencies
- Template rendering for goal descriptions
- Safe condition evaluation
- Export data extraction
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from harness.orchestrator.dependency_graph import DependencyGraph
from harness.orchestrator.types import (
    ExecutionMode,
    StepResult,
    StepStatus,
    WorkflowConfig,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)

if TYPE_CHECKING:
    from harness.loop.types import GoalConfig
    from harness.orchestrator.core import LoopOrchestrator

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Workflow execution engine.

    Responsible for parsing and executing WorkflowConfig with support for:
    - Template rendering: Inject previous step outputs into goals
    - Cascading skip: Automatically skip downstream of skipped steps
    - Safe condition evaluation: Use simpleeval with timeout protection
    - Export data extraction: Extract key data from GoalResult for downstream use

    Execution Flow:
    1. Build dependency graph
    2. Detect circular dependencies (deadlock)
    3. Execute steps in topological order
    4. Handle parallel execution when possible
    5. Track and propagate skip states
    """

    def __init__(self, orchestrator: LoopOrchestrator):
        """
        Initialize the workflow engine.

        Args:
            orchestrator: Parent LoopOrchestrator instance
        """
        self.orchestrator = orchestrator
        self._active_workflows: dict[str, asyncio.Task] = {}

    async def run(
        self,
        config: WorkflowConfig,
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """
        Execute a workflow.

        Args:
            config: Workflow configuration
            context: Execution context (passed to steps)

        Returns:
            Workflow execution result
        """
        result = WorkflowResult(
            workflow_name=config.name,
            status=WorkflowStatus.RUNNING,
            steps={},
            started_at=datetime.now(),
        )

        try:
            # Build dependency graph
            graph = self._build_dependency_graph(config.steps)

            # Detect deadlock (circular dependencies)
            if graph.detect_deadlock():
                raise RuntimeError("Deadlock detected: circular dependency in workflow")

            logger.info(f"Starting workflow '{config.name}' with {len(config.steps)} steps")

            # Execute steps
            while graph.has_pending():
                # Get ready steps (dependencies satisfied)
                ready_steps = graph.get_ready_steps()

                if not ready_steps:
                    # Check if all pending depend on skipped
                    if graph.has_only_skipped_pending():
                        # Add all skipped steps to result
                        self._add_skipped_steps_to_result(graph, result)
                        logger.info("All pending steps depend on skipped steps, ending gracefully")
                        break
                    # True deadlock - unreachable steps
                    raise RuntimeError("Deadlock detected: unreachable steps in workflow")

                # Execute based on mode
                if config.default_mode == ExecutionMode.PARALLEL:
                    await self._execute_parallel(ready_steps, config, result, context, graph)
                else:
                    await self._execute_sequential(ready_steps, config, result, context, graph)

            # Add any remaining skipped steps to result
            # (e.g., from cascade skip that happened during execution)
            self._add_skipped_steps_to_result(graph, result)

            # Determine final status
            all_success = all(
                s.status in (StepStatus.SUCCESS, StepStatus.SKIPPED) for s in result.steps.values()
            )
            result.status = WorkflowStatus.COMPLETED if all_success else WorkflowStatus.FAILED

            logger.info(
                f"Workflow '{config.name}' completed with status {result.status.value}, "
                f"duration: {result.duration_seconds:.2f}s"
            )

        except Exception as e:
            result.status = WorkflowStatus.FAILED
            result.error = str(e)
            logger.error(f"Workflow '{config.name}' failed: {e}")

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
        """Execute steps sequentially."""
        for step in steps:
            step_result = await self._execute_step(step, config, result, context, graph)
            result.steps[step.name] = step_result

            # Stop on failure
            if step_result.status == StepStatus.FAILED:
                logger.warning(f"Step '{step.name}' failed, stopping sequential execution")
                break

    async def _execute_parallel(
        self,
        steps: list[WorkflowStep],
        config: WorkflowConfig,
        result: WorkflowResult,
        context: dict[str, Any] | None,
        graph: DependencyGraph,
    ) -> None:
        """Execute steps in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(config.max_parallel_steps)

        async def run_step(step: WorkflowStep) -> tuple[str, StepResult]:
            async with semaphore:
                step_result = await self._execute_step(step, config, result, context, graph)
                return step.name, step_result

        tasks = [run_step(step) for step in steps]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in results:
            if isinstance(item, Exception):
                logger.error(f"Parallel execution error: {item}")
                continue

            step_name, step_result = item
            result.steps[step_name] = step_result

    async def _execute_step(
        self,
        step: WorkflowStep,
        config: WorkflowConfig,
        result: WorkflowResult,
        context: dict[str, Any] | None,
        graph: DependencyGraph,
    ) -> StepResult:
        """
        Execute a single workflow step.

        Key improvements:
        1. Template rendering: Inject previous step outputs into goal
        2. Export data extraction: Extract key data from GoalResult
        3. Graph state sync: Update graph immediately for concurrent visibility

        Args:
            step: Step configuration
            config: Workflow configuration
            result: Workflow result (accumulating)
            context: Execution context
            graph: Dependency graph for state updates
        """
        step_result = StepResult(
            step_name=step.name,
            status=StepStatus.RUNNING,
            started_at=datetime.now(),
        )

        try:
            # Check for skipped dependencies
            for dep in step.depends_on:
                dep_result = result.steps.get(dep)
                if dep_result and dep_result.status == StepStatus.SKIPPED:
                    step_result.status = StepStatus.SKIPPED
                    graph.mark_skipped(step.name)
                    logger.info(f"Step '{step.name}' skipped due to skipped dependency '{dep}'")
                    return step_result

            # Check condition
            if step.condition and not await self._evaluate_condition_safe(
                step.condition, result, context
            ):
                step_result.status = StepStatus.SKIPPED
                graph.mark_skipped(step.name)
                logger.info(f"Step '{step.name}' skipped due to condition: {step.condition}")
                return step_result

            # Render goal with template variables
            rendered_goal = self._render_goal(step.goal, result, context)

            # Build GoalConfig
            goal_config = self._build_goal_config(step, config, rendered_goal)

            # Activate skills
            for skill_name in step.skills:
                self.orchestrator.agent.activate_skill(skill_name)

            # Execute goal
            logger.info(f"Executing step '{step.name}': {rendered_goal[:100]}...")
            goal_result = await self.orchestrator.agent.run_goal(goal_config)

            step_result.goal_result = goal_result
            step_result.status = StepStatus.SUCCESS if goal_result.achieved else StepStatus.FAILED

            # Extract exports
            if step.exports and goal_result:
                step_result.exports = self._extract_exports(goal_result, step.exports)

            # Update graph state
            graph.mark_completed(step.name)

            logger.info(f"Step '{step.name}' completed with status {step_result.status.value}")

        except Exception as e:
            step_result.status = StepStatus.FAILED
            step_result.error = str(e)
            graph.mark_completed(step.name)
            logger.error(f"Step '{step.name}' failed: {e}")

        step_result.completed_at = datetime.now()
        return step_result

    def _build_goal_config(
        self,
        step: WorkflowStep,
        config: WorkflowConfig,
        rendered_goal: str,
    ) -> GoalConfig:
        """Build GoalConfig from step configuration."""
        from harness.loop.types import GoalConfig

        return GoalConfig(
            description=rendered_goal,
            workspace_dir=step.workspace_dir or config.workspace_dir,
            max_iterations=step.max_iterations,
            timeout_seconds=step.timeout_seconds,
            custom_verifier=step.custom_verifier,
        )

    def _render_goal(
        self,
        goal_template: str,
        result: WorkflowResult,
        context: dict[str, Any] | None,
    ) -> str:
        """
        Render goal template with context.

        Supports template syntax:
        - {{steps.analyze.exports.report_path}} - Reference step export
        - {{steps.analyze.goal_result.final_response}} - Reference step result
        - {{context.user_id}} - Reference context variable

        Args:
            goal_template: Goal template string
            result: Workflow result with step outputs
            context: Execution context

        Returns:
            Rendered goal string
        """
        # Build template context
        template_context = {
            "steps": {
                name: {
                    "status": sr.status.value,
                    "exports": sr.exports,
                    "goal_result": sr.goal_result.__dict__ if sr.goal_result else None,
                }
                for name, sr in result.steps.items()
            },
            "context": context or {},
        }

        # Simple template rendering
        rendered = goal_template
        pattern = r"\{\{([^}]+)\}\}"
        matches = re.findall(pattern, goal_template)

        for match in matches:
            path = match.strip()
            value = self._resolve_path(path, template_context)
            if value is not None:
                rendered = rendered.replace(f"{{{{{match}}}}}", str(value))

        return rendered

    def _resolve_path(self, path: str, context: dict) -> Any:
        """
        Resolve a dot-separated path in a nested dict.

        Args:
            path: Dot-separated path (e.g., "steps.analyze.exports.report_path")
            context: Context dictionary

        Returns:
            Value at path or None if not found
        """
        parts = path.split(".")
        current = context

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None

            if current is None:
                return None

        return current

    def _extract_exports(
        self,
        goal_result: Any,  # GoalResult
        export_config: dict[str, str],
    ) -> dict[str, Any]:
        """
        Extract exports from GoalResult.

        Export config format:
        {
            "report_path": "$.artifacts.report_file",
            "issue_count": "$.metrics.total_issues"
        }

        Args:
            goal_result: Goal execution result
            export_config: Export path mappings

        Returns:
            Dict of exported values
        """
        exports = {}

        for key, jsonpath in export_config.items():
            if jsonpath.startswith("$."):
                path = jsonpath[2:]
                value = self._resolve_path(path, goal_result.__dict__)
                if value is not None:
                    exports[key] = value

        return exports

    async def _evaluate_condition_safe(
        self,
        condition: str,
        result: WorkflowResult,
        context: dict[str, Any] | None,
    ) -> bool:
        """
        Safely evaluate a condition expression.

        Uses simpleeval for security and adds timeout protection.

        Args:
            condition: Python expression to evaluate
            result: Workflow result
            context: Execution context

        Returns:
            Boolean result of condition evaluation
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._evaluate_condition,
                    condition,
                    result,
                    context,
                ),
                timeout=5.0,
            )
        except TimeoutError:
            logger.warning(f"Condition evaluation timed out: {condition}")
            return False
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {e}")
            return False

    def _evaluate_condition(
        self,
        condition: str,
        result: WorkflowResult,
        context: dict[str, Any] | None,
    ) -> bool:
        """
        Evaluate condition expression synchronously.

        Uses simpleeval for safe evaluation.

        Args:
            condition: Python expression
            result: Workflow result
            context: Execution context

        Returns:
            Boolean result
        """
        try:
            from simpleeval import EvalWithCompoundTypes

            eval_context = {
                "steps": result.steps,
                "context": context or {},
                "StepStatus": StepStatus,
            }

            evaluator = EvalWithCompoundTypes(names=eval_context)
            return bool(evaluator.eval(condition))
        except ImportError:
            logger.warning("simpleeval not installed, using basic eval")
            # Fallback to basic eval with restricted builtins
            eval_context = {
                "steps": result.steps,
                "context": context or {},
                "StepStatus": StepStatus,
            }
            return bool(eval(condition, {"__builtins__": {}}, eval_context))
        except Exception as e:
            logger.warning(f"Condition evaluation error: {e}")
            return False

    def _build_dependency_graph(self, steps: list[WorkflowStep]) -> DependencyGraph:
        """
        Build dependency graph from step list.

        Args:
            steps: List of workflow steps

        Returns:
            Constructed dependency graph
        """
        graph = DependencyGraph()

        for step in steps:
            graph.add_step(step)
            for dep in step.depends_on:
                graph.add_dependency(step.name, dep)

        return graph

    def _add_skipped_steps_to_result(
        self,
        graph: DependencyGraph,
        result: WorkflowResult,
    ) -> None:
        """
        Add all skipped steps to the workflow result.

        When a step is skipped due to cascade, it may not be in the result
        because it was never actually executed. This method adds all skipped
        steps to the result with SKIPPED status.

        Args:
            graph: Dependency graph with skip state
            result: Workflow result to update
        """
        for step_name, _step in graph._steps.items():
            if step_name not in result.steps and graph.is_skipped(step_name):
                result.steps[step_name] = StepResult(
                    step_name=step_name,
                    status=StepStatus.SKIPPED,
                )

    def cancel_workflow(self, workflow_name: str) -> bool:
        """
        Cancel an active workflow.

        Args:
            workflow_name: Name of workflow to cancel

        Returns:
            True if workflow was cancelled
        """
        task = self._active_workflows.get(workflow_name)
        if task and not task.done():
            task.cancel()
            logger.info(f"Cancelled workflow: {workflow_name}")
            return True
        return False
