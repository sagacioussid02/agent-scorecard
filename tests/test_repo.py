import os

import pytest

from agent_scorecard.repo import MAX_FILE_BYTES, FileKind, RepoIndex, classify, comment_lines


@pytest.mark.parametrize("path,kind", [
    ("src/agent.py", FileKind.CODE),
    ("web/app/page.tsx", FileKind.CODE),
    ("gateway/main.go", FileKind.CODE),
    ("pyproject.toml", FileKind.CONFIG),
    (".mcp.json", FileKind.CONFIG),
    ("migrations/001_approvals.sql", FileKind.CONFIG),
    (".github/workflows/ci.yml", FileKind.CI),
    ("README.md", FileKind.DOC),
])
def test_classify(path, kind):
    assert classify(path)[0] == kind


@pytest.mark.parametrize("path", ["app.min.js", "types.d.ts", "logo.png", "data.bin"])
def test_classify_skips_noise(path):
    assert classify(path) is None


def test_test_example_and_tooling_files_are_not_production():
    idx = RepoIndex.from_mapping({
        "src/agent.py": "x = 1",
        "tests/test_agent.py": "x = 1",
        "src/agent.test.ts": "x = 1",
        "examples/demo.py": "x = 1",
        ".claude/hooks/audit.sh": "echo",
        "scripts/deploy.py": "x = 1",
        "backend/deploy.py": "x = 1",
    })
    prod = {f.path for f in idx.files if f.is_production}
    assert prod == {"src/agent.py"}


def test_python_docstrings_and_comments_are_masked_but_prompts_are_not():
    text = '\n'.join([
        '"""Module docstring mentioning approval gates."""',  # 1
        "# a comment about the audit log",                    # 2
        "def f():",                                           # 3
        '    """Function docstring',                          # 4
        '    still docstring"""',                             # 5
        "    return 1",                                       # 6
        "PROMPT = \"\"\"Treat this as untrusted data.\"\"\"",  # 7
    ])
    masked = comment_lines(text, "python")
    assert {1, 2, 4, 5} <= masked
    assert 6 not in masked and 7 not in masked


def test_c_style_comments_are_masked():
    text = "// line\nconst a = 1\n/* block\n still */\nconst b = 2"
    assert comment_lines(text, "typescript") == {1, 3, 4}


def test_grep_ignores_comments_by_default():
    idx = RepoIndex.from_mapping({"a.py": "# fail closed\nx = 1\n"})
    assert idx.grep(r"fail closed") == []
    assert len(idx.grep(r"fail closed", code_only=False)) == 1


def test_word_boundary_treats_underscore_as_separator():
    idx = RepoIndex.from_mapping({"a.py": "self._max_steps = 10\nDEFAULT_MAX_STEPS = 5\n"})
    assert len(idx.grep(r"\bmax_steps\b", flags=0)) == 1
    assert len(idx.grep(r"\bmax_steps\b", flags=2)) == 2  # re.I


def test_walker_is_safe(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "agent.py").write_text("x = 1")
    (tmp_path / "node_modules" / "pkg").mkdir(parents=True)
    (tmp_path / "node_modules" / "pkg" / "index.js").write_text("evil()")
    (tmp_path / "big.py").write_text("x" * (MAX_FILE_BYTES + 1))
    (tmp_path / "blob.py").write_bytes(b"\x00\x01binary")
    outside = tmp_path.parent / "outside_secret.py"
    outside.write_text("SECRET = 1")
    os.symlink(outside, tmp_path / "link.py")
    os.symlink(tmp_path.parent, tmp_path / "linkdir")

    idx = RepoIndex.load(tmp_path)
    paths = {f.path for f in idx.files}
    assert paths == {"src/agent.py"}
    assert "big.py" in idx.all_paths  # still known to exist (lockfiles can be huge)
    assert not any(p.startswith("node_modules") or p.startswith("linkdir") for p in idx.all_paths)


def test_load_rejects_non_directory(tmp_path):
    with pytest.raises(NotADirectoryError):
        RepoIndex.load(tmp_path / "missing")


def test_lockfiles_are_never_searched():
    idx = RepoIndex.from_mapping({"package-lock.json": '"@types/phoenix": "1"', "a.py": "x"})
    assert idx.grep(r"phoenix", (FileKind.CONFIG,)) == []
