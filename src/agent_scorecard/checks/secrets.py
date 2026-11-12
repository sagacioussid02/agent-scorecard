"""Layer 4: secrets and egress. What can leak, and where can it go?"""

from __future__ import annotations

import re

from ..model import Evidence, Layer, Severity, Status
from ..repo import FileKind
from .base import CODE, Outcome, ScanContext, check, find, tiered

L = Layer.SECRETS

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Anthropic key", re.compile(r"sk-ant-(?:api|admin)\d{2}-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{32,}")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("Stripe live key", re.compile(r"\b[rs]k_live_[0-9a-zA-Z]{20,}")),
    ("Private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----(?:\\n|\s)+[A-Za-z0-9+/=]{64,}")),
    ("Hardcoded credential", re.compile(
        r"(?i)\b(?:api[_-]?key|secret[_-]?key|auth[_-]?token|access[_-]?token|client[_-]?secret|password)\b"
        r"\s*[:=]\s*['\"]([A-Za-z0-9_\-+/=]{24,})['\"]")),
)
_PLACEHOLDER = re.compile(r"(?i)(x{4,}|your|example|placeholder|changeme|dummy|fake|sample|test|redacted|<|\$\{|\*{3,}|0{8,}|1234)")
_EXAMPLE_FILE = re.compile(r"(?i)(\.example|\.sample|\.template|example\.|sample\.|\.dist)($|\.)")


def entropy(value: str) -> float:
    """Shannon entropy in bits per character. Real keys sit well above 3.5."""
    import math
    from collections import Counter
    if not value:
        return 0.0
    n = len(value)
    return -sum(c / n * math.log2(c / n) for c in Counter(value).values())


def _redact(text: str, start: int, end: int) -> str:
    secret = text[start:end]
    return text[:start] + secret[:6] + "…[redacted]" + text[end:]


def find_secrets(ctx: ScanContext) -> list[Evidence]:
    out: list[Evidence] = []
    for f in ctx.index.select((FileKind.CODE, FileKind.CONFIG, FileKind.CI), production_only=False):
        if _EXAMPLE_FILE.search(f.name) or f.lang == "lock":
            continue
        for label, rx in SECRET_PATTERNS:
            for m in rx.finditer(f.text):
                value = m.group(1) if m.groups() else m.group(0)
                generic = label == "Hardcoded credential"
                if _PLACEHOLDER.search(value) or len(set(value)) < 8:
                    continue
                if label != "Private key":
                    if entropy(value) < (3.5 if generic else 3.0):
                        continue
                    if not (re.search(r"\d", value) and re.search(r"[A-Za-z]", value)):
                        continue  # real keys mix letters and digits; "xoxb-real-token" doesn't
                if generic and not f.is_production:
                    continue  # generic test fixtures are noise; provider formats still count
                line_start = f.text.rfind("\n", 0, m.start()) + 1
                line_end = f.text.find("\n", m.end())
                line = f.text[line_start: line_end if line_end != -1 else len(f.text)]
                s, e = m.start() - line_start, m.end() - line_start
                if m.groups():
                    s, e = m.start(1) - line_start, m.end(1) - line_start
                snippet = f"{label}: " + _redact(line, s, e).strip()[:120]
                out.append(Evidence(f.path, f.text.count("\n", 0, m.start()) + 1, snippet,
                                    negative=True))
    return out


@check(
    "SE-01", L, "No secrets are committed", Severity.CRITICAL,
    why="A key in the repo is a key in every clone, fork and CI log. Agents make it worse: "
        "they read the repo and can paste the key anywhere.",
    look_for="Provider key formats (Anthropic, OpenAI, AWS, GitHub, Slack, Google, Stripe), "
             "private keys, and long literal values assigned to api_key / token / password, "
             "plus committed .env files. Matches are redacted in the report.",
    full="Nothing that looks like a live secret is committed.",
    partial="Secret-shaped values appear only in tests or examples; confirm they are fake.",
    fix="Rotate anything found, move it to the environment or a secret manager, and purge "
        "it from history.",
)
def no_committed_secrets(ctx: ScanContext) -> Outcome:
    hits = find_secrets(ctx)
    env_files = [Evidence(f.path, 1, "committed .env file", negative=True) for f in ctx.index.files
                 if re.search(r"(^|/)\.env(\.[\w-]+)?$", f.path) and not _EXAMPLE_FILE.search(f.name)
                 and re.search(r"(?im)^\s*\w*(KEY|TOKEN|SECRET|PASSWORD)\w*\s*=\s*\S{8,}", f.text)]
    prod = [h for h in hits if (ctx.index.get(h.path) and ctx.index.get(h.path).is_production)] + env_files
    if prod:
        return Outcome(Status.MISSING, f"{len(prod)} likely secret(s) committed in non-test files.", tuple(prod))
    if hits:
        return Outcome(Status.PARTIAL, f"{len(hits)} secret-shaped value(s) in tests or examples; confirm they are fake.", tuple(hits))
    return Outcome(Status.PASS, "No committed secrets detected.")


@check(
    "SE-02", L, "Secrets come from the environment or a vault", Severity.HIGH,
    why="Keys loaded at runtime can be rotated, scoped per environment and kept out of the "
        "model's context. Keys in code can't.",
    look_for="os.environ / getenv / process.env / pydantic BaseSettings / a secret manager "
             "(AWS Secrets Manager, SSM, Vault, GCP Secret Manager, keyring), plus .env in "
             ".gitignore.",
    full="Secrets are read at runtime and .env files are git-ignored.",
    partial="Secrets are read from the environment, but .env is not git-ignored.",
    fix="Load secrets through one settings module, git-ignore .env, and ship a .env.example.",
)
def env_secrets(ctx: ScanContext) -> Outcome:
    loads = find(ctx, [
        r"\bos\.(environ|getenv)\b|\bprocess\.env\b|\bos\.Getenv\(|\bos\.LookupEnv\(|\bimport\.meta\.env\b",
        r"\b(BaseSettings|pydantic_settings|SecretsManager|secretsmanager|get_secret_value|ssm\.get_parameter|hvac|keyring|SecretManagerServiceClient|KeyVault)\b",
    ], CODE)
    ignores = [f for f in ctx.index.files if f.name == ".gitignore" and re.search(r"(?m)^\s*/?\*?\.env\b|^\s*\.env\*", f.text)]
    if loads and ignores:
        return Outcome(Status.PASS, "Secrets are read at runtime and .env is git-ignored.", tuple(loads[:3] + [Evidence(ignores[0].path, 1, ".env ignored")]))
    if loads:
        return Outcome(Status.PARTIAL, "Secrets come from the environment, but .env is not git-ignored.", tuple(loads))
    return Outcome(Status.MISSING, "No runtime secret loading found.")


@check(
    "SE-03", L, "Secret scanning runs before merge", Severity.MEDIUM,
    why="People and agents both paste keys. A scanner in CI or pre-commit catches it before "
        "it reaches the default branch.",
    look_for="gitleaks, trufflehog, detect-secrets, ggshield, secretlint or git-secrets in CI "
             "or pre-commit; weaker: other static security scanners (CodeQL, Semgrep, Bandit).",
    full="A secret scanner runs in CI or pre-commit.",
    partial="Static security scanning runs, but no dedicated secret scanner.",
    fix="Add gitleaks or trufflehog to CI and pre-commit, and fail the build on findings.",
)
def secret_scanning(ctx: ScanContext) -> Outcome:
    return tiered(
        ctx,
        full=[r"\b(gitleaks|trufflehog|detect-secrets|ggshield|secretlint|git-secrets|talisman|secret[-_ ]scan(ning|ner)?)\b"],
        partial=[r"\b(codeql|semgrep|bandit|snyk|trivy|osv-scanner|pip-audit|npm audit)\b"],
        kinds=(FileKind.CI, FileKind.CONFIG),
        flags=re.I,
        full_msg="A secret scanner runs in CI or pre-commit.",
        partial_msg="Security scanning runs, but no secret scanner.",
        missing_msg="No secret or security scanning in CI or pre-commit.",
    )


@check(
    "SE-04", L, "Outbound network access is restricted", Severity.HIGH,
    why="Exfiltration needs somewhere to send data. An agent that can fetch any URL can be "
        "told to send your data to any URL.",
    look_for="Domain or host allowlists for fetch/browse tools, private-IP and SSRF blocking, "
             "egress policies (NetworkPolicy, firewall rules); weaker: denylists.",
    full="Fetch and browse tools are limited to an allowlist, or private ranges are blocked.",
    partial="Some destinations are denied, but the default is open.",
    fix="Route agent HTTP through one client with a domain allowlist, block private and "
        "metadata IPs, and deny network by default in sandboxes.",
)
def egress(ctx: ScanContext) -> Outcome:
    return tiered(
        ctx,
        full=[
            r"\b(allowed_(domains|hosts|urls)|ALLOWED_(DOMAINS|HOSTS|URLS)|domain_allowlist|host_allowlist|url_allowlist|allowedDomains|allowedHosts)\b",
            r"\b(is_allowed_(url|domain|host)|check_url|validate_url|egress\w*|ssrf\w*|block_private\w*|is_private_ip|is_private|private_ip\w*|169\.254\.169\.254)\b",
            r"\bkind:\s*NetworkPolicy\b",
        ],
        partial=[r"\b(blocked|denied|prohibited|forbidden)_?(domains|hosts|urls)\b"],
        kinds=(FileKind.CODE, FileKind.CONFIG),
        flags=re.I,
        full_msg="Outbound destinations are restricted.",
        partial_msg="A denylist exists, but outbound access is open by default.",
        missing_msg="No outbound network restrictions found.",
    )

