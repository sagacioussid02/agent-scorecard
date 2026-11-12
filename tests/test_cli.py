import json

from agent_scorecard.cli import main


def test_scan_markdown_to_stdout(good_agent, capsys):
    assert main(["scan", str(good_agent)]) == 0
    assert "Agent Safety Scorecard" in capsys.readouterr().out


def test_scan_json_to_file(good_agent, tmp_path):
    out = tmp_path / "card.json"
    assert main(["scan", str(good_agent), "--format", "json", "--out", str(out), "--name", "demo"]) == 0
    assert json.loads(out.read_text())["target"] == "demo"


def test_fail_under_gates_ci(tmp_path, capsys):
    (tmp_path / "a.py").write_text("x = 1\n")
    assert main(["scan", str(tmp_path), "--fail-under", "50"]) == 1
    assert "below --fail-under" in capsys.readouterr().err


def test_only_runs_selected_checks(good_agent, capsys):
    assert main(["scan", str(good_agent), "--format", "json", "--only", "TB-01,AG-01"]) == 0
    ids = [c["id"] for c in json.loads(capsys.readouterr().out)["checks"]]
    assert ids == ["TB-01", "AG-01"]


def test_bad_path(tmp_path, capsys):
    assert main(["scan", str(tmp_path / "missing")]) == 2


def test_explain_and_rubric(capsys):
    assert main(["explain", "SE-01"]) == 0
    assert "SE-01" in capsys.readouterr().out
    assert main(["explain", "ZZ-00"]) == 2
    assert main(["rubric"]) == 0
    assert "# Agent Safety Rubric" in capsys.readouterr().out
