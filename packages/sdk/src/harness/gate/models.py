"""Deterministic gate models.

All decision objects used by the deterministic gate pipeline. These are pure
data structures with no LLM dependency — gate verdicts are produced by 100%
deterministic code, never by the model.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FindingType(Enum):
    """Which validator produced a finding."""

    FORMAT = "format"
    FACT = "fact"
    LOGIC = "logic"
    RECONCILIATION = "reconciliation"


class GateSeverity(Enum):
    """Severity of a gate finding."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Backoff(Enum):
    """Retry backoff strategy."""

    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


@dataclass
class GateFinding:
    """A single issue found by a gate validator."""

    id: str
    type: FindingType
    severity: GateSeverity
    message: str
    field: str | None = None
    evidence: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "field": self.field,
            "evidence": self.evidence,
        }


@dataclass
class GateVerdict:
    """Result of running the deterministic gate over a delivery.

    Attributes:
        passed: True when no ERROR-severity finding exists. WARNING-level
            findings still pass but are reported so callers can flag content.
        findings: All findings produced by validators + reconciliation.
        delivered_content: The content to actually deliver. By default it equals
            the input; callers may choose to strip/flag unsourced segments.
        reconciliation_report: Structured cross-check report (claim <-> source).
    """

    passed: bool
    findings: list[GateFinding] = field(default_factory=list)
    delivered_content: str = ""
    reconciliation_report: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[GateFinding]:
        return [f for f in self.findings if f.severity == GateSeverity.ERROR]

    @property
    def warnings(self) -> list[GateFinding]:
        return [f for f in self.findings if f.severity == GateSeverity.WARNING]

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "findings": [f.as_dict() for f in self.findings],
            "delivered_content": self.delivered_content,
            "reconciliation_report": self.reconciliation_report,
        }


@dataclass
class RetryPolicy:
    """Deterministic retry policy with backoff and retryable-error filtering.

    Used by goal-level and workflow-step execution. Retries are local
    self-healing: on exhaustion the caller escalates to termination/downgrade
    or the human review queue.
    """

    max_retries: int = 3
    backoff: Backoff = Backoff.EXPONENTIAL
    backoff_base: float = 1.0
    backoff_cap: float = 30.0
    retryable_errors: tuple[type[Exception], ...] = ()

    def should_retry(self, attempt: int, error: Exception) -> bool:
        """Whether to retry given the (0-based) attempt count and the error."""
        return attempt < self.max_retries and (
            not self.retryable_errors or isinstance(error, self.retryable_errors)
        )

    def delay_for(self, attempt: int) -> float:
        """Deterministic delay (seconds) before the next attempt."""
        if self.backoff == Backoff.CONSTANT:
            return min(self.backoff_base, self.backoff_cap)
        if self.backoff == Backoff.LINEAR:
            return min(self.backoff_base * (attempt + 1), self.backoff_cap)
        # Exponential
        return float(min(self.backoff_base * (2**attempt), self.backoff_cap))


# A rule is a pure function: (content, sources) -> list[GateFinding]
GateRule = Callable[[str, list[str]], list[GateFinding]]
