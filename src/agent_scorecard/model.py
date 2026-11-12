"""Core data model: layers, severities, statuses, evidence and results.

Everything here is a plain, immutable dataclass or enum so results can be
serialised to JSON, compared in tests and rendered by any reporter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Layer(str, Enum):
    """The seven safety layers of a production-ready agent."""

    TOOLS = "tools"
    APPROVALS = "approvals"
    AUDIT = "audit"
    SECRETS = "secrets"
    BUDGETS = "budgets"
    UNTRUSTED_INPUT = "untrusted_input"
    EVALS = "evals"

    @property
    def title(self) -> str:
        return _LAYER_TITLES[self]

    @property
    def number(self) -> int:
        return list(Layer).index(self) + 1


_LAYER_TITLES = {
    Layer.TOOLS: "Tool boundaries",
    Layer.APPROVALS: "Human approval gates",
    Layer.AUDIT: "Audit trail and observability",
    Layer.SECRETS: "Secrets and egress",
    Layer.BUDGETS: "Budgets and limits",
    Layer.UNTRUSTED_INPUT: "Untrusted input handling",
    Layer.EVALS: "Evals, testing and rollback",
}


class Severity(str, Enum):
    """How much a check matters. The weight feeds the score."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"

    @property
    def weight(self) -> int:
        return {"critical": 3, "high": 2, "medium": 1}[self.value]


class Status(str, Enum):
    PASS = "pass"
    PARTIAL = "partial"
    MISSING = "missing"
    NOT_APPLICABLE = "n/a"

    @property
    def points(self) -> int | None:
        """Points out of 2. None means the check is excluded from scoring."""
        return {"pass": 2, "partial": 1, "missing": 0, "n/a": None}[self.value]


@dataclass(frozen=True)
class Evidence:
    """One place in the scanned repo that supports (or undermines) a check."""

    path: str
    line: int
    snippet: str
    negative: bool = False  # True when the evidence is an anti-pattern

    def location(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass(frozen=True)
class CheckSpec:
    """Static description of a check. This is the rubric."""

    id: str
    layer: Layer
    title: str
    severity: Severity
    why: str
    look_for: str
    full_credit: str
    partial_credit: str
    fix: str


@dataclass(frozen=True)
class CheckResult:
    spec: CheckSpec
    status: Status
    summary: str
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class LayerScore:
    layer: Layer
    score: float | None  # 0-100, None when every check was n/a
    results: tuple[CheckResult, ...]


@dataclass(frozen=True)
class Scorecard:
    target: str
    commit: str | None
    scanner_version: str
    frameworks: tuple[str, ...]
    files_scanned: int
    overall: float
    grade: str
    grade_capped: bool
    layers: tuple[LayerScore, ...]
    critical_gaps: tuple[CheckResult, ...] = field(default_factory=tuple)

    @property
    def results(self) -> list[CheckResult]:
        return [r for layer in self.layers for r in layer.results]
