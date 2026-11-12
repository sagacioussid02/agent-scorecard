from agent_scorecard.model import CheckResult, CheckSpec, Layer, Severity, Status
from agent_scorecard.repo import RepoIndex
from agent_scorecard.scanner import build_scorecard, grade_for, score_layer


def result(sev: Severity, status: Status, layer: Layer = Layer.TOOLS, cid: str = "X-01") -> CheckResult:
    spec = CheckSpec(cid, layer, "t", sev, "w", "l", "f", "p", "fix")
    return CheckResult(spec, status, "s")


def test_layer_score_is_severity_weighted():
    rs = [result(Severity.CRITICAL, Status.PASS), result(Severity.MEDIUM, Status.MISSING)]
    assert score_layer(rs) == round(100 * 6 / 8, 1)


def test_not_applicable_checks_are_excluded():
    assert score_layer([result(Severity.HIGH, Status.PASS), result(Severity.CRITICAL, Status.NOT_APPLICABLE)]) == 100.0
    assert score_layer([result(Severity.HIGH, Status.NOT_APPLICABLE)]) is None


def test_partial_is_half_credit():
    assert score_layer([result(Severity.HIGH, Status.PARTIAL)]) == 50.0


def test_grade_bands():
    assert [grade_for(s) for s in (100, 85, 84.9, 70, 55, 40, 39.9, 0)] == ["A", "A", "B", "B", "C", "D", "F", "F"]


def _card(results):
    return build_scorecard(RepoIndex.from_mapping({}), results, "t", [])


def test_overall_is_mean_of_scored_layers():
    rs = [result(Severity.HIGH, Status.PASS, Layer.TOOLS, "A"), result(Severity.HIGH, Status.MISSING, Layer.AUDIT, "B")]
    card = _card(rs)
    assert card.overall == 50.0
    assert [ls.score for ls in card.layers if ls.score is not None] == [100.0, 0.0]


def test_missing_critical_caps_grade_at_c():
    rs = [result(Severity.HIGH, Status.PASS, layer, layer.value) for layer in Layer]
    rs.append(result(Severity.CRITICAL, Status.MISSING, Layer.TOOLS, "CRIT"))
    card = _card(rs)
    assert card.overall >= 85
    assert card.grade == "C" and card.grade_capped
    assert [r.spec.id for r in card.critical_gaps] == ["CRIT"]


def test_cap_never_raises_a_grade():
    rs = [result(Severity.CRITICAL, Status.MISSING, layer, layer.value) for layer in Layer]
    card = _card(rs)
    assert card.grade == "F" and not card.grade_capped
