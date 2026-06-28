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

For more details, see the design document:
    packages/sdk/design/loop-engineering.md
"""

from harness.loop.goal import GoalVerifier, VerificationError
from harness.loop.goal_loop import GoalLoop
from harness.loop.types import (
    GoalConfig,
    GoalResult,
    GoalStatus,
    VerificationMethod,
    VerificationRecord,
    VerificationResult,
)

__all__ = [
    # Types
    "GoalConfig",
    "GoalResult",
    "GoalStatus",
    "VerificationMethod",
    "VerificationRecord",
    "VerificationResult",
    # Implementations
    "GoalVerifier",
    "VerificationError",
    "GoalLoop",
]
