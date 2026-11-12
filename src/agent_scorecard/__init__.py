"""Agent Safety Scorecard: a static scan of how safely an AI agent is built."""

__version__ = "0.1.0"

from .scanner import scan  # noqa: E402

__all__ = ["scan", "__version__"]
