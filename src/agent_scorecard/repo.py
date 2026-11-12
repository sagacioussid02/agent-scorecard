"""Read-only index of a repository on disk.

The scanner never executes, imports or installs anything from the target.
It walks the tree once, classifies files and keeps their text in memory so
every check can search it cheaply.

Safety properties of the walker:
- symlinks are never followed (a hostile repo cannot point us at ~/.ssh);
- vendored, generated and dependency directories are skipped;
- files over ``MAX_FILE_BYTES`` and binary files are skipped;
- the total number of files read is capped.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from functools import cached_property
from enum import Enum
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator

from .model import Evidence

MAX_FILE_BYTES = 512 * 1024
MAX_FILES = 20_000
SNIPPET_CHARS = 140

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env", "__pycache__",
    "dist", "build", "out", ".next", ".nuxt", ".turbo", "vendor", "third_party",
    "site-packages", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "coverage", ".terraform", "target", ".idea", ".vscode", "bower_components",
}

CODE_EXT = {
    ".py": "python", ".pyi": "python",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin", ".rb": "ruby",
    ".cs": "csharp", ".php": "php", ".sh": "shell", ".bash": "shell",
}
CONFIG_EXT = {
    ".json": "json", ".jsonc": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".ini": "ini", ".cfg": "ini", ".env": "env", ".tf": "terraform",
    ".lock": "lock", ".sql": "sql",
}
CONFIG_NAMES = {
    "dockerfile": "docker", "makefile": "make", ".gitignore": "gitignore",
    "requirements.txt": "requirements", "requirements-dev.txt": "requirements",
    "go.mod": "gomod", "go.sum": "lock", "uv.lock": "lock", "poetry.lock": "lock",
    "package-lock.json": "lock", "pnpm-lock.yaml": "lock", "yarn.lock": "lock",
    "bun.lockb": "lock", "pipfile.lock": "lock", "cargo.lock": "lock",
    ".pre-commit-config.yaml": "yaml", ".gitleaks.toml": "toml",
}
DOC_EXT = {".md": "markdown", ".mdx": "markdown", ".rst": "rst", ".txt": "text"}

_TEST_PARTS = re.compile(r"(^|/)(tests?|__tests__|spec|specs|e2e|testing)(/|$)", re.I)
_TEST_FILE = re.compile(r"(^test_.*|.*_test\.(py|go)|.*\.(test|spec)\.[jt]sx?|conftest\.py)$", re.I)
_EXAMPLE_PARTS = re.compile(r"(^|/)(examples?|samples?|demos?|cookbook|notebooks?|tutorials?|docs?)(/|$)", re.I)
# Developer tooling and ops scripts: real code, but not the agent's runtime.
_TOOLING = re.compile(
    r"(^|/)\.(claude|cursor|agents|husky|devcontainer|vscode|idea|windsurf|codex|gemini|openhands)/"
    r"|(^|/)(scripts?|hack)/"
    r"|(^|/)(deploy|build|setup|install|release|noxfile|fabfile|tasks)[\w-]*\.(py|ts|js|mjs|sh)$",
    re.I,
)


class FileKind(str, Enum):
    CODE = "code"
    CONFIG = "config"
    CI = "ci"
    DOC = "doc"


@dataclass(frozen=True, eq=False)
class SourceFile:
    path: str  # repo-relative, POSIX separators
    kind: FileKind
    lang: str
    is_test: bool
    is_example: bool
    text: str
    is_tooling: bool = False

    @property
    def name(self) -> str:
        return PurePosixPath(self.path).name

    @property
    def is_production(self) -> bool:
        return not (self.is_test or self.is_example or self.is_tooling)

    @cached_property
    def comment_lines(self) -> frozenset[int]:
        return frozenset(comment_lines(self.text, self.lang))


def classify(rel: str) -> tuple[FileKind, str] | None:
    p = PurePosixPath(rel)
    name = p.name.lower()
    suffix = p.suffix.lower()
    if rel.startswith(".github/workflows/") or name in {".gitlab-ci.yml", "azure-pipelines.yml", "jenkinsfile"} \
            or rel.startswith(".circleci/") or rel.startswith(".buildkite/"):
        return FileKind.CI, "ci"
    if name in CONFIG_NAMES:
        return FileKind.CONFIG, CONFIG_NAMES[name]
    if name.startswith(".env"):
        return FileKind.CONFIG, "env"
    if suffix in CODE_EXT:
        if name.endswith(".min.js") or name.endswith(".d.ts"):
            return None
        return FileKind.CODE, CODE_EXT[suffix]
    if suffix in CONFIG_EXT:
        return FileKind.CONFIG, CONFIG_EXT[suffix]
    if suffix in DOC_EXT:
        return FileKind.DOC, DOC_EXT[suffix]
    return None


class RepoIndex:
    """All readable text files of one repository, classified."""

    def __init__(self, root: Path, files: list[SourceFile], all_paths: list[str] | None = None):
        self.root = root
        self.files = files
        # Every path in the tree, including files too large or binary to read.
        self.all_paths = all_paths if all_paths is not None else [f.path for f in files]
        self._by_path = {f.path: f for f in files}

    # ---------- construction ----------
    @classmethod
    def load(cls, root: str | os.PathLike[str]) -> "RepoIndex":
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise NotADirectoryError(f"not a directory: {root}")
        files: list[SourceFile] = []
        all_paths: list[str] = []
        for rel in _walk(root_path):
            all_paths.append(rel)
            if len(files) >= MAX_FILES:
                break
            cls_ = classify(rel)
            if cls_ is None:
                continue
            full = root_path / rel
            try:
                if full.stat().st_size > MAX_FILE_BYTES:
                    continue
                raw = full.read_bytes()
            except OSError:
                continue
            if b"\x00" in raw[:4096]:
                continue
            text = raw.decode("utf-8", errors="replace")
            files.append(_make(rel, cls_, text))
        return cls(root_path, files, all_paths)

    @classmethod
    def from_mapping(cls, mapping: dict[str, str], root: str = "<memory>") -> "RepoIndex":
        """Build an index from {path: text}. Used by tests."""
        files = []
        for rel, text in sorted(mapping.items()):
            cls_ = classify(rel)
            if cls_ is None:
                continue
            files.append(_make(rel, cls_, text))
        return cls(Path(root), files, sorted(mapping))

    # ---------- queries ----------
    def get(self, path: str) -> SourceFile | None:
        return self._by_path.get(path)

    def exists(self, pattern: str) -> list[SourceFile]:
        """Readable files whose path matches a regex (searched, case-insensitive)."""
        rx = _compile(pattern, re.I)
        return [f for f in self.files if rx.search(f.path)]

    def paths(self, pattern: str) -> list[str]:
        """All paths (readable or not) matching a regex, case-insensitive."""
        rx = _compile(pattern, re.I)
        return [p for p in self.all_paths if rx.search(p)]

    def select(
        self,
        kinds: Iterable[FileKind] = (FileKind.CODE,),
        *,
        production_only: bool = True,
        tests_only: bool = False,
        langs: Iterable[str] | None = None,
    ) -> Iterator[SourceFile]:
        kind_set = set(kinds)
        lang_set = set(langs) if langs else None
        for f in self.files:
            if f.kind not in kind_set or f.lang == "lock":
                continue
            if tests_only and not f.is_test:
                continue
            if production_only and not tests_only and not f.is_production:
                continue
            if lang_set and f.lang not in lang_set:
                continue
            yield f

    def grep(
        self,
        pattern: str,
        kinds: Iterable[FileKind] = (FileKind.CODE,),
        *,
        production_only: bool = True,
        tests_only: bool = False,
        langs: Iterable[str] | None = None,
        flags: int = 0,
        limit: int = 50,
        negative: bool = False,
        code_only: bool = True,
        paths: set[str] | None = None,
    ) -> list[Evidence]:
        """Search files. ``code_only`` skips comments and docstrings, so prose
        about a control does not count as the control."""
        rx = _compile(pattern, flags | re.M)
        hits: list[Evidence] = []
        for f in self.select(kinds, production_only=production_only, tests_only=tests_only, langs=langs):
            if paths is not None and f.path not in paths:
                continue
            for m in rx.finditer(f.text):
                line_no = f.text.count("\n", 0, m.start()) + 1
                if code_only and line_no in f.comment_lines:
                    continue
                hits.append(Evidence(f.path, line_no, _snippet(f.text, m.start()), negative=negative))
                if len(hits) >= limit:
                    return hits
        return hits

    def files_matching(
        self,
        pattern: str,
        kinds: Iterable[FileKind] = (FileKind.CODE,),
        *,
        production_only: bool = True,
        flags: int = 0,
    ) -> set[str]:
        rx = _compile(pattern, flags | re.M)
        return {f.path for f in self.select(kinds, production_only=production_only) if rx.search(f.text)}

    def commit(self) -> str | None:
        if not (self.root / ".git").exists():
            return None
        try:
            out = subprocess.run(
                ["git", "-C", str(self.root), "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=10, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip() or None


def _make(rel: str, cls_: tuple[FileKind, str], text: str) -> SourceFile:
    kind, lang = cls_
    return SourceFile(
        path=rel, kind=kind, lang=lang,
        is_test=bool(_TEST_PARTS.search(rel) or _TEST_FILE.match(PurePosixPath(rel).name)),
        is_example=bool(_EXAMPLE_PARTS.search(rel)),
        text=text,
        is_tooling=bool(_TOOLING.search(rel)),
    )


_LINE_COMMENT = {
    "python": ("#",), "shell": ("#",), "yaml": ("#",), "toml": ("#",), "ini": ("#", ";"), "ruby": ("#",),
    "terraform": ("#", "//"), "sql": ("--",), "env": ("#",),
}
_C_STYLE = {"typescript", "javascript", "go", "rust", "java", "kotlin", "csharp", "php", "json"}
_TRIPLE = re.compile(r'^[rRbBuUfF]{0,2}("""|\'\'\')')


def comment_lines(text: str, lang: str) -> set[int]:
    """1-based line numbers that are comments or docstrings (best effort).

    Python: '#' lines and docstrings (a triple-quoted string that opens a
    module, class or function body). Triple-quoted strings assigned to a
    name, such as prompts, are kept, because prompts are where untrusted-data
    labels live. C-style languages: '//' lines and '/* ... */' blocks.
    """
    out: set[int] = set()
    lines = text.split("\n")
    if lang == "python":
        prev_sig = ""
        in_doc: str | None = None
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            if in_doc:
                out.add(i)
                if in_doc in line:
                    in_doc = None
                continue
            if line.startswith("#"):
                out.add(i)
                continue
            m = _TRIPLE.match(line)
            if m and (prev_sig == "" or prev_sig.endswith(":")):
                out.add(i)
                quote = m.group(1)
                rest = line[m.end():]
                if quote not in rest:
                    in_doc = quote
            if line:
                prev_sig = line
        return out
    prefixes = _LINE_COMMENT.get(lang, ())
    if lang in _C_STYLE:
        in_block = False
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            if in_block:
                out.add(i)
                if "*/" in line:
                    in_block = False
                continue
            if line.startswith("//") or line.startswith("*"):
                out.add(i)
            elif line.startswith("/*"):
                out.add(i)
                if "*/" not in line:
                    in_block = True
        return out
    for i, raw in enumerate(lines, 1):
        if prefixes and raw.lstrip().startswith(prefixes):
            out.add(i)
    return out


def _walk(root: Path) -> Iterator[str]:
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not os.path.islink(os.path.join(dirpath, d)))
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            yield PurePosixPath(Path(full).relative_to(root)).as_posix()


# Word boundaries that treat "_" as a separator, so \\bmax_steps\\b also
# matches self._max_steps and DEFAULT_MAX_STEPS. Code is full of snake_case
# identifiers, and Python's \\b treats "_" as a letter, so it would miss them.
# A leading \\b becomes a single lookbehind and a trailing one a single
# lookahead, which keeps the regexes close to the speed of plain \\b.
_LEAD = r"(?<![A-Za-z0-9])"
_TRAIL = r"(?![A-Za-z0-9])"


def _ident_boundaries(pattern: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("\\\\", i):  # an escaped backslash, keep both chars
            out.append(pattern[i:i + 2])
            i += 2
            continue
        if pattern.startswith("\\b", i):
            prev = out[-1][-1:] if out else ""
            nxt = pattern[i + 2: i + 3]
            leading = prev in ("", "(", "|", ":") or (
                (nxt in ("(", "[", "\\") or nxt.isalnum()) and not (prev.isalnum() or prev in ")]")
            )
            out.append(_LEAD if leading else _TRAIL)
            i += 2
            continue
        out.append(pattern[i])
        i += 1
    return "".join(out)


@lru_cache(maxsize=1024)
def _compile(pattern: str, flags: int) -> re.Pattern[str]:
    return re.compile(_ident_boundaries(pattern), flags)


def _snippet(text: str, pos: int) -> str:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    line = text[start: end if end != -1 else len(text)].strip()
    if len(line) > SNIPPET_CHARS:
        col = pos - start
        lo = max(0, min(col - 40, len(line) - SNIPPET_CHARS))
        line = ("…" if lo else "") + line[lo: lo + SNIPPET_CHARS] + "…"
    return line
