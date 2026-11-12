import json
from datetime import date
from pathlib import Path

from agent_scorecard.checks import REGISTRY
from agent_scorecard.model import Layer
from agent_scorecard.report import explain, rubric_markdown, to_dict, to_json, to_markdown
from agent_scorecard.scanner import scan

ROOT = Path(__file__).parent.parent


def test_rubric_file_is_in_sync_with_the_registry():
    """RUBRIC.md is generated. If this fails, run: agent-scorecard rubric --out RUBRIC.md"""
    assert (ROOT / "RUBRIC.md").read_text(encoding="utf-8") == rubric_markdown()


def test_rubric_covers_every_layer_and_check():
    text = rubric_markdown()
    for layer in Layer:
        assert layer.title in text
    for c in REGISTRY.ordered():
        assert f"### {c.spec.id} " in text


def test_rubric_size_and_shape():
    checks = REGISTRY.ordered()
    assert 24 <= len(checks) <= 30
    assert {c.spec.layer for c in checks} == set(Layer)
    for c in checks:
        s = c.spec
        assert s.why and s.look_for and s.full_credit and s.partial_credit and s.fix
        assert s.id[:2] in {"TB", "AG", "AU", "SE", "BL", "UI", "ER"}


def test_markdown_scorecard(good_agent):
    md = to_markdown(scan(good_agent), today=date(2026, 11, 9))
    assert md.startswith("# Agent Safety Scorecard: good_agent")
    assert "Grade A" in md
    for section in ("## Layers", "## Checks", "## Evidence"):
        assert section in md
    assert "2026-11-09" in md
    assert "| TB-01 |" in md


def test_markdown_escapes_table_pipes():
    from agent_scorecard.report import _cell
    assert _cell("a|b\nc") == "a\\|b c"


def test_json_is_complete(good_agent):
    data = json.loads(to_json(scan(good_agent)))
    assert data["grade"] == "A"
    assert len(data["checks"]) == len(REGISTRY.ordered())
    assert {"id", "status", "evidence", "severity", "layer"} <= set(data["checks"][0])
    assert data == to_dict(scan(good_agent))


def test_explain():
    assert explain("ag-01").startswith("AG-01")
    assert explain("NOPE-99") is None
