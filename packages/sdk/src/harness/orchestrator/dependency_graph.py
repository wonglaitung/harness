"""
Dependency Graph - Workflow step dependency resolution.

This module provides the DependencyGraph class for:
- Managing step dependencies
- Detecting circular dependencies (deadlock)
- Supporting cascading skip operations
- Determining which steps are ready to execute
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.orchestrator.types import WorkflowStep

logger = logging.getLogger(__name__)


class DependencyGraph:
    """
    Step dependency graph.

    Manages dependencies between workflow steps and supports:
    - Topological ordering for execution
    - Circular dependency (deadlock) detection
    - Cascading skip operations for conditional execution
    - Runtime state tracking (completed, skipped)

    State Management:
    - _completed: Steps that have finished (success or failure)
    - _skipped: Steps that were skipped (condition not met or dependency skipped)
    """

    def __init__(self):
        self._steps: dict[str, WorkflowStep] = {}
        self._dependencies: dict[str, set[str]] = {}
        self._completed: set[str] = set()
        self._skipped: set[str] = set()

    def add_step(self, step: WorkflowStep) -> None:
        """
        Add a step to the graph.

        Args:
            step: Workflow step to add
        """
        self._steps[step.name] = step
        if step.name not in self._dependencies:
            self._dependencies[step.name] = set()

    def add_dependency(self, step_name: str, depends_on: str) -> None:
        """
        Add a dependency relationship.

        Args:
            step_name: Step that has the dependency
            depends_on: Step that must complete first
        """
        if step_name not in self._dependencies:
            self._dependencies[step_name] = set()
        self._dependencies[step_name].add(depends_on)

    def has_pending(self) -> bool:
        """
        Check if there are pending steps.

        Returns:
            True if there are steps not yet completed or skipped
        """
        resolved = len(self._completed) + len(self._skipped)
        return resolved < len(self._steps)

    def has_only_skipped_pending(self) -> bool:
        """
        Check if all pending steps depend on skipped steps.

        This indicates we should gracefully end execution rather than
        raising a deadlock error.

        Returns:
            True if all pending steps have skipped dependencies
        """
        for name, step in self._steps.items():
            if name in self._completed or name in self._skipped:
                continue

            # Check if any dependency is not skipped
            deps = self._dependencies.get(name, set())
            if not deps or not deps.issubset(self._skipped):
                return False

        return True

    def get_ready_steps(self) -> list[WorkflowStep]:
        """
        Get steps that are ready to execute.

        A step is ready if:
        - It hasn't been completed or skipped
        - All its dependencies have been completed (not skipped)

        Note: Steps with skipped dependencies are NOT returned here,
        they should be handled by the cascade skip logic.

        Returns:
            List of steps ready for execution
        """
        ready = []
        for name, step in self._steps.items():
            if name in self._completed or name in self._skipped:
                continue

            deps = self._dependencies.get(name, set())
            skipped_deps = deps.intersection(self._skipped)

            # If any dependency was skipped, this step should be skipped too
            if skipped_deps:
                continue

            # All dependencies completed
            if deps.issubset(self._completed):
                ready.append(step)

        return ready

    def mark_completed(self, step_name: str) -> None:
        """
        Mark a step as completed.

        Args:
            step_name: Name of the completed step
        """
        self._completed.add(step_name)
        logger.debug(f"Step '{step_name}' marked as completed")

    def mark_skipped(self, step_name: str) -> None:
        """
        Mark a step as skipped and cascade to dependent steps.

        When a step is skipped, all steps that depend on it should
        also be skipped (cascade skip). This is done recursively to
        handle transitive dependencies.

        Args:
            step_name: Name of the skipped step
        """
        if step_name in self._skipped:
            return  # Already skipped

        self._skipped.add(step_name)
        logger.debug(f"Step '{step_name}' marked as skipped")

        # Find and skip all direct dependents
        dependents = self.get_dependents(step_name)
        for dependent in dependents:
            if dependent not in self._completed and dependent not in self._skipped:
                # Recursively skip this dependent and its dependents
                self.mark_skipped(dependent)

    def detect_deadlock(self) -> bool:
        """
        Detect circular dependencies (deadlock).

        Uses depth-first search to detect cycles in the dependency graph.

        Returns:
            True if a cycle is detected (deadlock)
        """
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
                    logger.warning(f"Deadlock detected: cycle involving '{node}' -> '{dep}'")
                    return True

            rec_stack.remove(node)
            return False

        for step_name in self._steps:
            if step_name not in visited:
                if has_cycle(step_name):
                    return True

        return False

    def get_step(self, step_name: str) -> WorkflowStep | None:
        """Get a step by name."""
        return self._steps.get(step_name)

    def get_dependencies(self, step_name: str) -> set[str]:
        """Get dependencies for a step."""
        return self._dependencies.get(step_name, set())

    def get_dependents(self, step_name: str) -> set[str]:
        """
        Get steps that depend on the given step.

        Args:
            step_name: Step name to find dependents for

        Returns:
            Set of step names that depend on the given step
        """
        dependents = set()
        for name, deps in self._dependencies.items():
            if step_name in deps:
                dependents.add(name)
        return dependents

    def is_completed(self, step_name: str) -> bool:
        """Check if a step is completed."""
        return step_name in self._completed

    def is_skipped(self, step_name: str) -> bool:
        """Check if a step is skipped."""
        return step_name in self._skipped

    def is_resolved(self, step_name: str) -> bool:
        """Check if a step is resolved (completed or skipped)."""
        return step_name in self._completed or step_name in self._skipped

    def get_status_summary(self) -> dict:
        """
        Get a summary of the graph status.

        Returns:
            Dict with counts of steps in each state
        """
        return {
            "total": len(self._steps),
            "completed": len(self._completed),
            "skipped": len(self._skipped),
            "pending": len(self._steps) - len(self._completed) - len(self._skipped),
        }

    def reset(self) -> None:
        """Reset the graph state (keep step definitions)."""
        self._completed.clear()
        self._skipped.clear()
