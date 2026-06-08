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


# Persisted columns for rate-limit snapshots — numbers/enums only, no raw content.
RL_PERSISTED_FIELDS = (
    "id",
    "provider",
    "source",
    "session_id",
    "timestamp",
    "window",
    "used_percent",
    "window_minutes",
    "resets_at",
    "plan_type",
)

# Recognized window keys.
WINDOW_PRIMARY = "primary_5h"
WINDOW_SECONDARY = "secondary_weekly"


@dataclass
class RateLimitSnapshot:
    """One provider rate-limit reading for a single window at a point in time.

    Sourced from Codex rollout ``payload.rate_limits``. ``resets_at`` is epoch
    **seconds** (matching the Codex log). Only numeric/enum fields are persisted —
    no prompt, response, code, or secret content can be represented here.
    """

    id: str
    provider: str  # "codex" (Claude logs carry no native limit data)
    source: str
    session_id: str
    timestamp: str  # ISO-8601 of the reading
    window: str  # WINDOW_PRIMARY | WINDOW_SECONDARY
    used_percent: float = 0.0
    window_minutes: Optional[int] = None
    resets_at: Optional[int] = None  # epoch SECONDS
    plan_type: Optional[str] = None

    def as_persisted_dict(self) -> dict[str, Any]:
        full = asdict(self)
        return {k: full[k] for k in RL_PERSISTED_FIELDS}


_RL_FIELD_NAMES = {f.name for f in fields(RateLimitSnapshot)}
assert set(RL_PERSISTED_FIELDS) <= _RL_FIELD_NAMES, (
    f"RL_PERSISTED_FIELDS references unknown fields: {set(RL_PERSISTED_FIELDS) - _RL_FIELD_NAMES}"
)
