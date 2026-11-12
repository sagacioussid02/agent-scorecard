"""Whole-repo scans of a well-built agent and a bare one."""

from agent_scorecard.scanner import scan
from conftest import fake_key


def test_reference_agent_scores_an_a(good_agent):
    card = scan(good_agent)
    assert card.grade == "A", [(r.spec.id, r.status.value) for r in card.results if r.status.value != "pass"]
    assert card.overall >= 95
    assert "LangGraph" in card.frameworks


def test_bare_agent_is_capped_and_flags_critical_gaps(tmp_path):
    (tmp_path / "requirements.txt").write_text("crewai\nanthropic\n")
    (tmp_path / "crew.py").write_text(
        "import subprocess\n"
        "from crewai import Agent, Crew, Task\n"
        f"API_KEY = '{fake_key('sk-ant-api03-')}'\n"
        "def run_shell(cmd):\n"
        "    return subprocess.run(cmd, shell=True, capture_output=True).stdout\n"
        "agent = Agent(role='ops', goal='fix prod', tools=[run_shell])\n"
        "Crew(agents=[agent], tasks=[Task(description='{page}')]).kickoff()\n"
    )
    card = scan(tmp_path)
    gaps = {r.spec.id for r in card.critical_gaps}
    assert {"SE-01", "AG-01", "TB-03", "UI-01", "BL-01"} <= gaps
    assert card.grade in {"D", "F"}
    assert "CrewAI" in card.frameworks


def test_scan_never_writes_to_the_target(good_agent):
    before = {p: p.stat().st_mtime_ns for p in good_agent.rglob("*") if p.is_file()}
    scan(good_agent)
    after = {p: p.stat().st_mtime_ns for p in good_agent.rglob("*") if p.is_file()}
    assert before == after
