"""Run every check against a repository and turn the results into a scorecard.

Scoring, in one paragraph: each check earns 2 (pass), 1 (partial) or 0
(missing) points, weighted by severity (critical 3, high 2, medium 1). N/A
checks are left out. A layer's score is its weighted points over the maximum,
as a percentage. The overall score is the plain average of the layer scores,
because defence in depth means a perfect layer cannot make up for an absent
one. Grades: A >= 85, B >= 70, C >= 55, D >= 40, else F. Any critical check
that is missing caps the grade at C, however high the number.
"""

from __future__ import annotations

import os
from typing import Iterable

from . import __version__
from .checks import REGISTRY, ScanContext
from .model import CheckResult, Layer, LayerScore, Scorecard, Severity, Status
from .repo import RepoIndex

GRADE_BANDS = ((85, "A"), (70, "B"), (55, "C"), (40, "D"), (0, "F"))
CRITICAL_CAP = "C"


def score_layer(results: Iterable[CheckResult]) -> float | None:
    got = possible = 0
    for r in results:
        pts = r.status.points
        if pts is None:
            continue
        w = r.spec.severity.weight
        got += w * pts
        possible += w * 2
    return None if possible == 0 else round(100 * got / possible, 1)


def grade_for(score: float) -> str:
    for floor, letter in GRADE_BANDS:
        if score >= floor:
            return letter
    return "F"


def build_scorecard(index: RepoIndex, results: list[CheckResult], target: str, frameworks: list[str]) -> Scorecard:
    layers = []
    for layer in Layer:
        rs = tuple(r for r in results if r.spec.layer == layer)
        layers.append(LayerScore(layer, score_layer(rs), rs))
    scored = [ls.score for ls in layers if ls.score is not None]
    overall = round(sum(scored) / len(scored), 1) if scored else 0.0
    grade = grade_for(overall)
    gaps = tuple(r for r in results if r.spec.severity == Severity.CRITICAL and r.status == Status.MISSING)
    capped = False
    if gaps and "ABCDF".index(grade) < "ABCDF".index(CRITICAL_CAP):
        grade, capped = CRITICAL_CAP, True
    return Scorecard(
        target=target,
        commit=index.commit(),
        scanner_version=__version__,
        frameworks=tuple(frameworks),
        files_scanned=len(index.files),
        overall=overall,
        grade=grade,
        grade_capped=capped,
        layers=tuple(layers),
        critical_gaps=gaps,
    )


def scan_index(index: RepoIndex, target: str | None = None, only: Iterable[str] | None = None) -> Scorecard:
    ctx = ScanContext(index)
    wanted = {c.upper() for c in only} if only else None
    results = [c.run(ctx) for c in REGISTRY.ordered() if wanted is None or c.spec.id in wanted]
    return build_scorecard(index, results, target or os.path.basename(str(index.root)), ctx.frameworks)


def scan(path: str | os.PathLike[str], name: str | None = None, only: Iterable[str] | None = None) -> Scorecard:
    """Scan a local repository. Read-only: nothing in the target is executed."""
    index = RepoIndex.load(path)
    return scan_index(index, target=name, only=only)
