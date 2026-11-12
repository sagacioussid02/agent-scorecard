"""Tools available to the agent, each with a risk tier."""
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse

import docker
from pydantic import BaseModel, Field

from .settings import ALLOWED_DOMAINS

WORKSPACE_ROOT = Path("/workspace").resolve()


class ToolTier(str, Enum):
    READ = "read"
    WRITE = "write"
    IRREVERSIBLE = "irreversible"


class WriteFileArgs(BaseModel):
    path: str = Field(max_length=200)
    content: str = Field(max_length=100_000)


def confine(path: str) -> Path:
    p = (WORKSPACE_ROOT / path).resolve()
    if not p.is_relative_to(WORKSPACE_ROOT):
        raise PermissionError("path traversal blocked")
    return p


def write_file(args: WriteFileArgs) -> str:
    target = confine(args.path)
    target.write_text(args.content)
    return "ok"


def is_allowed_url(url: str) -> bool:
    return urlparse(url).hostname in ALLOWED_DOMAINS


def run_command(cmd: list[str]) -> str:
    client = docker.from_env()
    out = client.containers.run("python:3.12-slim", cmd, network_disabled=True, remove=True, timeout=120)
    return out.decode()


TOOLS = {
    "write_file": {"fn": write_file, "risk_level": ToolTier.WRITE, "args_schema": WriteFileArgs},
    "run_command": {"fn": run_command, "risk_level": ToolTier.IRREVERSIBLE},
}
allowed_tools = ["write_file", "run_command"]
