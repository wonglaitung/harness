"""
Loop Engineering module - Goal-driven execution for AI agents.

This module implements the Loop Engineering paradigm, where agents
run autonomously until a goal is achieved, rather than requiring
manual prompting at each step.

Core components:
- GoalConfig: Configuration for goal-driven execution
- GoalResult: Result of goal execution
- GoalStatus: Status of goal achievement
- GoalVerifier: Verifies if a goal has been achieved
- GoalLoop: Executes the goal-driven loop
- Automation: Simplified API for scheduled/periodic execution (Phase 2)
- WorktreeOrchestrator: Parallel execution in isolated worktrees (Phase 3)

Example:
    ```python
    from harness import AgentHarness
    from harness.loop import GoalStatus

    agent = AgentHarness()

    result = await agent.run_goal(
        goal="Fix all type errors in src/",
        max_iterations=50,
    )

    if result.status == GoalStatus.ACHIEVED:
        print("Goal achieved!")
    ```

    ```python
    # Phase 2: Automation
    from harness.loop import Automation

    automation = Automation(
        name="daily-report",
        schedule="0 9 * * *",
        goal="Generate daily report",
    )
    await automation.start(agent)
    ```

    ```python
    # Phase 3: Parallel Worktrees
    from harness.loop import WorktreeOrchestrator, WorktreeConfig

    orchestrator = WorktreeOrchestrator(agent, ".")
    results = await orchestrator.run_parallel([
        WorktreeConfig(name="feature-a", goal="Implement feature A"),
        WorktreeConfig(name="feature-b", goal="Implement feature B"),
    ])
    ```

For more details, see the design document:
    packages/sdk/design/loop-engineering.md
"""

from harness.loop.automation import (
    Automation,
    AutomationConfig,
    AutomationResult,
    AutomationStatus,
)
from harness.loop.goal import GoalVerifier, VerificationError
from harness.loop.goal_loop import GoalLoop
from harness.loop.tool_verification import (
    CommandResult,
    ToolVerificationConfig,
    VerificationCommand,
    execute_verification_command,
    run_tool_verification,
)
from harness.loop.types import (
    GoalConfig,
    GoalResult,
    GoalStatus,
    VerificationMethod,
    VerificationRecord,
    VerificationResult,
)
from harness.loop.worktree_manager import WorktreeManager
from harness.loop.worktree_orchestrator import WorktreeOrchestrator
from harness.loop.worktree_types import (
    WORKTREES_DIR,
    MergeResult,
    WorktreeConfig,
    WorktreeError,
    WorktreeResult,
)

__all__ = [
    # Types
    "GoalConfig",
    "GoalResult",
    "GoalStatus",
    "VerificationMethod",
    "VerificationRecord",
    "VerificationResult",
    # Tool Verification
    "ToolVerificationConfig",
    "VerificationCommand",
    "CommandResult",
    "execute_verification_command",
    "run_tool_verification",
    # Implementations
    "GoalVerifier",
    "VerificationError",
    "GoalLoop",
    # Phase 2: Automation
    "Automation",
    "AutomationConfig",
    "AutomationResult",
    "AutomationStatus",
    # Phase 3: Worktrees
    "WorktreeManager",
    "WorktreeOrchestrator",
    "WorktreeConfig",
    "WorktreeResult",
    "WorktreeError",
    "MergeResult",
    "WORKTREES_DIR",
]
