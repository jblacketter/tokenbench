"""Common usage-event schema shared across providers.

``UsageEvent`` is the single normalized record that every provider parser emits and
the only shape that reaches SQLite. The field list is deliberately a *whitelist*:
parsers may see prompts, responses, source code, and secrets in the raw logs, but
none of that can be represented here, so none of it can be persisted.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict
from typing import Any, Optional


# The exact set of columns persisted to SQLite. ``metadata`` holds only small,
# whitelisted provider hints (e.g. session file name), never raw content.
PERSISTED_FIELDS = (
    "id",
    "provider",
    "source",
    "model",
    "timestamp",
    "project_path",
    "session_id",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_output_tokens",
    "total_tokens",
    "metadata",
)


@dataclass
class UsageEvent:
    """One normalized usage record.

    Token counts are per-event (already de-cumulated for Codex). ``total_tokens`` is
    computed from the components when a provider does not supply it directly.
    Provider-asymmetric fields (cache writes, reasoning tokens, model, project path)
    may be ``None``.
    """

    id: str
    provider: str  # "claude" | "codex"
    source: str  # absolute path to the log file the event came from
    timestamp: str  # ISO-8601 UTC
    session_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0
    model: Optional[str] = None
    project_path: Optional[str] = None
    # Small whitelisted hints only — never raw prompt/response/code/secret text.
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize Nones on numeric fields to 0 so storage/analytics can rely on ints.
        for numeric in (
            "input_tokens",
            "output_tokens",
            "cache_read_tokens",
            "cache_write_tokens",
            "reasoning_output_tokens",
        ):
            if getattr(self, numeric) is None:
                setattr(self, numeric, 0)
        if not self.total_tokens:
            self.total_tokens = (
                self.input_tokens
                + self.output_tokens
                + self.cache_read_tokens
                + self.cache_write_tokens
                + self.reasoning_output_tokens
            )

    def as_persisted_dict(self) -> dict[str, Any]:
        """Return only the whitelisted persisted columns for this event."""
        full = asdict(self)
        return {k: full[k] for k in PERSISTED_FIELDS}


# Sanity check: every persisted field must be a real dataclass field. Guards against
# the whitelist drifting away from the dataclass definition.
_FIELD_NAMES = {f.name for f in fields(UsageEvent)}
assert set(PERSISTED_FIELDS) <= _FIELD_NAMES, (
    f"PERSISTED_FIELDS references unknown fields: {set(PERSISTED_FIELDS) - _FIELD_NAMES}"
)
