"""Command line interface.

    agent-scorecard scan PATH [--format md|json] [--out FILE] [--fail-under N]
    agent-scorecard rubric [--out FILE]
    agent-scorecard explain CHECK_ID
    agent-scorecard mcp            # run as an MCP server over stdio
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .report import explain, rubric_markdown, to_json, to_markdown
from .scanner import scan


def _write(text: str, out: str | None) -> None:
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent-scorecard", description="Score how safely an AI agent codebase is built.")
    p.add_argument("--version", action="version", version=f"agent-scorecard {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("scan", help="scan a local repository")
    s.add_argument("path", help="path to the repository")
    s.add_argument("--name", help="name to print on the scorecard (default: folder name)")
    s.add_argument("--format", choices=("md", "json"), default="md")
    s.add_argument("--out", help="write to this file instead of stdout")
    s.add_argument("--no-evidence", action="store_true", help="omit the evidence section")
    s.add_argument("--only", help="comma-separated check ids to run")
    s.add_argument("--fail-under", type=float, metavar="SCORE",
                   help="exit with status 1 when the overall score is below SCORE (for CI)")

    r = sub.add_parser("rubric", help="print the rubric as Markdown")
    r.add_argument("--out")

    e = sub.add_parser("explain", help="explain one check")
    e.add_argument("check_id")

    sub.add_parser("mcp", help="run as an MCP server on stdio")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        try:
            card = scan(args.path, name=args.name, only=args.only.split(",") if args.only else None)
        except NotADirectoryError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        text = to_json(card) if args.format == "json" else to_markdown(card, evidence=not args.no_evidence)
        _write(text, args.out)
        if args.fail_under is not None and card.overall < args.fail_under:
            print(f"score {card.overall:.0f} is below --fail-under {args.fail_under:.0f}", file=sys.stderr)
            return 1
        return 0
    if args.command == "rubric":
        _write(rubric_markdown(), args.out)
        return 0
    if args.command == "explain":
        text = explain(args.check_id)
        if text is None:
            print(f"error: unknown check {args.check_id}", file=sys.stderr)
            return 2
        _write(text, None)
        return 0
    if args.command == "mcp":
        from .mcp_server import serve

        serve()
        return 0
    return 2
