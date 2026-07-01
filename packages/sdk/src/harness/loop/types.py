"""
Loop Engineering types - Goal-driven execution type definitions.

This module defines the core types for Loop Engineering:
- GoalConfig: Configuration for goal-driven execution
- GoalResult: Result of a goal execution
- GoalStatus: Status of goal achievement
- VerificationRecord: Record of verification attempts
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harness.types import LoopResult, Session


class GoalStatus(Enum):
    """
    Status of goal execution.

    Attributes:
        ACHIEVED: Goal has been successfully achieved
        TIMEOUT: Execution exceeded timeout limit
        MAX_ITERATIONS: Maximum iterations reached
        MAX_RESETS: Maximum context resets reached
        ERROR: Agent execution error
        VERIFIER_FAULT: Verifier failed (API rate limit, JSON parse error, etc.)
        CANCELLED: User cancelled execution
    """

    ACHIEVED = "achieved"
    TIMEOUT = "timeout"
    MAX_ITERATIONS = "max_iterations"
    MAX_RESETS = "max_resets"
    ERROR = "error"
    VERIFIER_FAULT = "verifier_fault"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        """Check if this is a terminal state (execution stopped)."""
        return self != GoalStatus.ACHIEVED

    def is_success(self) -> bool:
        """Check if this represents successful completion."""
        return self == GoalStatus.ACHIEVED


class VerificationMethod(Enum):
    """Method used for goal verification."""

    LLM = "llm"  # LLM-based verification
    CUSTOM = "custom"  # User-provided verification function
    TOOL = "tool"  # Tool-based verification (tests, lint, etc.)


@dataclass
class GoalConfig:
    """
    Configuration for goal-driven execution.

    This configuration defines how a goal should be executed and verified.

    Attributes:
        description: Human-readable description of the goal
        success_criteria: Optional specific criteria for success
        workspace_dir: Working directory for execution (Phase 3: worktree path)
        max_iterations: Maximum iterations per context window
        max_context_resets: Maximum context reset attempts
        timeout_seconds: Total execution timeout in seconds
        verification_method: Method for verifying goal achievement
        custom_verifier: Optional custom verification function (async recommended)
        verifier_max_retries: Maximum retries for verifier failures
        verifier_retry_delay: Initial retry delay in seconds
        verifier_retry_backoff: Backoff multiplier for retries
        max_tokens: Optional token budget limit
        max_cost_usd: Optional cost budget in USD
        context_reset_threshold: Context usage threshold for reset (0.0-1.0)
        preserve_messages: Number of messages to preserve on context reset

    Example:
        ```python
        config = GoalConfig(
            description="Fix all type errors in src/",
            workspace_dir="/tmp/worktree-feature-a",
            max_iterations=50,
            custom_verifier=async_verify_types,
        )
        ```
    """

    # Goal definition
    description: str
    success_criteria: str | None = None

    # Session for context continuity
    session_id: str | None = None

    # Execution environment (Phase 3 Worktrees support)
    workspace_dir: str = "."

    # Iteration control
    max_iterations: int = 50
    max_context_resets: int = 5
    timeout_seconds: int = 3600

    # Verification configuration
    verification_method: VerificationMethod = VerificationMethod.LLM
    custom_verifier: Callable[[LoopResult], bool] | Callable[[LoopResult], Any] | None = None

    # Verifier fault tolerance
    verifier_max_retries: int = 3
    verifier_retry_delay: float = 1.0
    verifier_retry_backoff: float = 2.0

    # Cost control
    max_tokens: int | None = None
    max_cost_usd: float | None = None

    # Context management
    context_reset_threshold: float = 0.7
    preserve_messages: int = 2

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.description:
            raise ValueError("Goal description cannot be empty")

        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

        if self.max_context_resets < 0:
            raise ValueError("max_context_resets cannot be negative")

        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be at least 1")

        if not 0.0 < self.context_reset_threshold <= 1.0:
            raise ValueError("context_reset_threshold must be between 0 and 1")

        # Validate custom_verifier if verification_method is CUSTOM
        if self.verification_method == VerificationMethod.CUSTOM and self.custom_verifier is None:
            raise ValueError("custom_verifier is required when verification_method is CUSTOM")


@dataclass
class VerificationRecord:
    """
    Record of a single verification attempt.

    Tracks the result and reasoning of each verification during goal execution.

    Attributes:
        iteration: The iteration number when verification occurred
        achieved: Whether the goal was achieved
        confidence: Confidence level (0.0-1.0)
        reasoning: Explanation of the verification result
        timestamp: When the verification occurred
        method: Method used for verification
        error: Error message if verification failed
    """

    iteration: int
    achieved: bool
    confidence: float
    reasoning: str
    timestamp: datetime = field(default_factory=datetime.now)
    method: VerificationMethod = VerificationMethod.LLM
    error: str | None = None

    def __post_init__(self):
        """Validate confidence range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class VerificationResult:
    """
    Result of a verification attempt.

    Returned by GoalVerifier.verify() to indicate goal achievement status.

    Attributes:
        achieved: Whether the goal has been achieved
        confidence: Confidence level of the result (0.0-1.0)
        reasoning: Explanation of why the goal is/isn't achieved
        should_retry: Whether to retry verification (for VERIFIER_FAULT)
        error: Error message if verification failed
    """

    achieved: bool
    confidence: float = 0.5
    reasoning: str = ""
    should_retry: bool = False
    error: str | None = None

    @classmethod
    def success(cls, reasoning: str = "", confidence: float = 1.0) -> VerificationResult:
        """Create a successful verification result."""
        return cls(achieved=True, confidence=confidence, reasoning=reasoning)

    @classmethod
    def failure(cls, reasoning: str = "", confidence: float = 0.0) -> VerificationResult:
        """Create a failure verification result."""
        return cls(achieved=False, confidence=confidence, reasoning=reasoning)

    @classmethod
    def fault(cls, error: str, should_retry: bool = True) -> VerificationResult:
        """Create a verifier fault result."""
        return cls(
            achieved=False,
            confidence=0.0,
            reasoning=f"Verifier fault: {error}",
            should_retry=should_retry,
            error=error,
        )


@dataclass
class GoalResult:
    """
    Result of goal-driven execution.

    Contains comprehensive information about the execution including
    status, statistics, and verification history.

    Attributes:
        goal: Original goal description
        status: Final status of goal execution
        total_iterations: Total number of iterations executed
        context_resets: Number of context resets performed
        total_tokens: Total token usage
        duration_seconds: Total execution duration in seconds
        final_response: Final response from the agent
        session: Complete session data
        verification_log: History of verification attempts
        error: Error message if execution failed

    Example:
        ```python
        result = await agent.run_goal("Fix type errors")

        if result.status == GoalStatus.ACHIEVED:
            print(f"Goal achieved in {result.total_iterations} iterations")
        elif result.status == GoalStatus.VERIFIER_FAULT:
            print(f"Verifier failed: {result.error}")
        ```
    """

    # Basic info
    goal: str
    status: GoalStatus

    # Execution statistics
    total_iterations: int = 0
    context_resets: int = 0
    total_tokens: dict[str, int] = field(default_factory=lambda: {"input": 0, "output": 0})
    duration_seconds: float = 0.0

    # Results
    final_response: str = ""
    session: Session | None = None
    verification_log: list[VerificationRecord] = field(default_factory=list)

    # Error info
    error: str | None = None

    @property
    def achieved(self) -> bool:
        """Check if the goal was achieved."""
        return self.status == GoalStatus.ACHIEVED

    @property
    def failed(self) -> bool:
        """Check if the goal execution failed (any non-achieved terminal state)."""
        return self.status != GoalStatus.ACHIEVED

    def get_verification_summary(self) -> str:
        """Get a summary of verification attempts."""
        if not self.verification_log:
            return "No verification attempts"

        achieved_count = sum(1 for v in self.verification_log if v.achieved)
        total = len(self.verification_log)

        return f"{achieved_count}/{total} verifications passed"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging/storage."""
        return {
            "goal": self.goal,
            "status": self.status.value,
            "total_iterations": self.total_iterations,
            "context_resets": self.context_resets,
            "total_tokens": self.total_tokens,
            "duration_seconds": self.duration_seconds,
            "final_response": self.final_response[:500] if self.final_response else None,
            "verification_count": len(self.verification_log),
            "error": self.error,
        }
