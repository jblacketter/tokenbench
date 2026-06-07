"""Provider parsers: raw JSONL logs -> normalized ``UsageEvent`` records.

Two critical, provider-specific rules (the heart of the MVP):

* **Claude Code** records usage PER MESSAGE under ``message.usage``. Each assistant
  message is its own event; we sum nothing across messages here — storage holds one
  row per message and analytics aggregates.

* **Codex** records ``total_token_usage`` as a CUMULATIVE running total per session
  (cached_input_tokens climbs into the millions). Naively summing those rows
  overcounts by orders of magnitude. We de-cumulate: emit per-turn DELTAS between
  consecutive usage rows in a session. If a session has only one usage row, that row
  IS the session total (the last-row fallback). Deltas are clamped at 0 to tolerate
  non-monotonic resets.

Both parsers are intentionally narrow: they read ONLY the numeric usage fields and a
few identifiers. They never copy prompt/response/code/tool content into the event.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator, Optional

from .schema import UsageEvent
from .sources import decode_claude_project_dir


def _read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield parsed JSON objects from a JSONL file, skipping blank/corrupt lines."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except (OSError, UnicodeError):
        return


def _stable_id(*parts: Any) -> str:
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# --------------------------------------------------------------------------- Claude


def parse_claude_file(path: Path) -> list[UsageEvent]:
    """Parse one Claude Code session JSONL into per-message usage events."""
    events: list[UsageEvent] = []
    encoded_project = path.parent.name
    project_path = decode_claude_project_dir(encoded_project) or None
    fallback_session = path.stem  # filename is the session uuid

    for idx, rec in enumerate(_read_jsonl(path)):
        message = rec.get("message")
        if not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue

        input_tokens = _as_int(usage.get("input_tokens"))
        output_tokens = _as_int(usage.get("output_tokens"))
        cache_write = _as_int(usage.get("cache_creation_input_tokens"))
        cache_read = _as_int(usage.get("cache_read_input_tokens"))

        # Skip records with no token signal at all (e.g. system/meta rows).
        if not any((input_tokens, output_tokens, cache_write, cache_read)):
            continue

        session_id = str(rec.get("sessionId") or fallback_session)
        timestamp = str(rec.get("timestamp") or "")
        model = message.get("model")

        events.append(
            UsageEvent(
                id=_stable_id("claude", path, session_id, idx),
                provider="claude",
                source=str(path),
                timestamp=timestamp,
                session_id=session_id,
                model=str(model) if model else None,
                project_path=project_path,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
                reasoning_output_tokens=0,
                metadata={"encoded_project": encoded_project},
            )
        )
    return events


# --------------------------------------------------------------------------- Codex


def _nested(rec: dict[str, Any], *keys: str) -> Any:
    cur: Any = rec
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _extract_codex_usage(rec: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Find ``total_token_usage`` in a Codex record.

    Real rollout shape nests it under ``payload.info.total_token_usage`` (a
    ``token_count`` event). We also tolerate top-level / other-container variants so
    older or differently-shaped logs still parse.
    """
    candidates = [
        _nested(rec, "payload", "info", "total_token_usage"),
        rec.get("total_token_usage"),
        _nested(rec, "info", "total_token_usage"),
        _nested(rec, "payload", "total_token_usage"),
        _nested(rec, "data", "total_token_usage"),
    ]
    for c in candidates:
        if isinstance(c, dict):
            return c
    return None


def _codex_session_context(records: list[dict[str, Any]]) -> dict[str, Optional[str]]:
    """Pull session id, cwd, and model from a rollout's metadata records.

    Codex records these once (in a ``session_meta`` header and turn-context rows),
    not on every token_count row, so we scan the whole file first.
    """
    ctx: dict[str, Optional[str]] = {"session_id": None, "cwd": None, "model": None}
    for rec in records:
        payload = rec.get("payload")
        if not isinstance(payload, dict):
            continue
        if rec.get("type") == "session_meta" or payload.get("id"):
            ctx["session_id"] = ctx["session_id"] or payload.get("id")
            cwd = payload.get("cwd")
            if isinstance(cwd, str) and cwd:
                ctx["cwd"] = ctx["cwd"] or cwd
        if ctx["model"] is None:
            for cand in (
                payload.get("model"),
                _nested(payload, "collaboration_mode", "settings", "model"),
                _nested(payload, "turn_context", "model"),
                _nested(payload, "info", "model"),
            ):
                if isinstance(cand, str) and cand:
                    ctx["model"] = cand
                    break
    return ctx


def parse_codex_file(path: Path) -> list[UsageEvent]:
    """Parse one Codex rollout JSONL into per-turn delta usage events.

    De-cumulation: ``total_token_usage`` is a running total, so each emitted event is
    the difference from the previous usage row in the same file. The first row is
    emitted as-is (it is the running total up to that point). A single-row session
    therefore yields exactly the session total (last-row fallback).
    """
    records = list(_read_jsonl(path))
    rows = [
        {"timestamp": rec.get("timestamp") or rec.get("ts") or "", "usage": usage}
        for rec in records
        if (usage := _extract_codex_usage(rec)) is not None
    ]
    if not rows:
        return []

    ctx = _codex_session_context(records)
    session_id_base = ctx["session_id"] or path.stem
    project_path = ctx["cwd"]
    model = ctx["model"]

    events: list[UsageEvent] = []
    prev = {
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "reasoning_output_tokens": 0,
        "total_tokens": 0,
    }

    for idx, row in enumerate(rows):
        usage = row["usage"]
        cur = {k: _as_int(usage.get(k)) for k in prev}

        # Per-turn delta vs previous cumulative snapshot, clamped at 0 to tolerate
        # session resets / non-monotonic rows.
        delta = {k: max(0, cur[k] - prev[k]) for k in prev}
        prev = cur

        # Skip no-op rows (cumulative didn't move).
        if not any(delta.values()):
            continue

        session_id = str(session_id_base)
        events.append(
            UsageEvent(
                id=_stable_id("codex", path, session_id, idx),
                provider="codex",
                source=str(path),
                timestamp=str(row["timestamp"] or ""),
                session_id=session_id,
                model=str(model) if model else None,
                project_path=project_path,
                input_tokens=delta["input_tokens"],
                output_tokens=delta["output_tokens"],
                cache_read_tokens=delta["cached_input_tokens"],
                cache_write_tokens=0,  # Codex has no cache-write counterpart.
                reasoning_output_tokens=delta["reasoning_output_tokens"],
                # total recomputed from components in UsageEvent.__post_init__.
                metadata={"normalization": "codex_cumulative_delta"},
            )
        )
    return events
