"""TokenBench — a local-first dashboard for Claude Code and Codex CLI token usage.

This package reads subscription-account usage from local machine logs, normalizes
token events into a single schema, stores only whitelisted metadata in SQLite, and
serves a localhost dashboard with token-efficiency feedback.

Privacy boundary: prompts, responses, source code, tool output, and secrets are
never persisted. Only the numeric usage fields and a small set of identifiers in
``UsageEvent`` reach the SQLite store. See ``tokenbench.storage`` and the privacy
regression test for the enforced guarantee.
"""

__version__ = "0.1.0"

from .schema import UsageEvent, PERSISTED_FIELDS

__all__ = ["UsageEvent", "PERSISTED_FIELDS", "__version__"]
