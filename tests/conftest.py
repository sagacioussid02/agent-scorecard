from __future__ import annotations

from pathlib import Path

import pytest

from agent_scorecard.checks import REGISTRY, ScanContext
from agent_scorecard.model import CheckResult
from agent_scorecard.repo import RepoIndex

FIXTURES = Path(__file__).parent / "fixtures"


def run_check(check_id: str, files: dict[str, str]) -> CheckResult:
    """Run one check against an in-memory repo given as {path: text}."""
    index = RepoIndex.from_mapping(files)
    return REGISTRY.get(check_id).run(ScanContext(index))


def fake_key(prefix: str, n: int = 40) -> str:
    """A secret-shaped value assembled at runtime, so no scanner (ours, GitHub's,
    gitleaks) ever sees a key-looking literal in this repository."""
    alphabet = "aB3dE5fG7hJ9kL2mN4pQ6rS8tU0vW1xY"
    return prefix + "".join(alphabet[(i * 7) % len(alphabet)] for i in range(n))


@pytest.fixture
def good_agent() -> Path:
    return FIXTURES / "good_agent"
