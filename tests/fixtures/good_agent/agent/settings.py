import os

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
AGENT_ENABLED = os.environ.get("AGENT_ENABLED", "1") == "1"  # kill switch
DRY_RUN = os.environ.get("DRY_RUN") == "1"
ALLOWED_DOMAINS = {"api.github.com", "docs.python.org"}
MAX_BUDGET_USD = 2.0
