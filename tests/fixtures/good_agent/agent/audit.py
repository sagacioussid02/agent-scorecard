import hashlib
import json
import re

_SECRET = re.compile(r"(sk-[A-Za-z0-9_-]+|ghp_[A-Za-z0-9]+)")


def redact(text: str) -> str:
    return _SECRET.sub("[REDACTED]", text)


class AuditLog:
    """Append-only, hash-chained audit trail of tool calls."""

    def __init__(self, path: str):
        self.path = path
        self.prev_hash = "0" * 64

    def log_tool_call(self, tool: str, args: dict, result: str) -> None:
        entry = {"tool": tool, "args": redact(json.dumps(args)), "result": redact(result), "prev_hash": self.prev_hash}
        line = json.dumps(entry)
        self.prev_hash = hashlib.sha256(line.encode()).hexdigest()
        with open(self.path, "a") as fh:
            fh.write(line + "\n")
