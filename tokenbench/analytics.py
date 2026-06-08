"""Aggregations over stored usage events for the dashboard.

All functions read from a ``UsageStore`` and return plain dicts/lists so the
dashboard (and tests) stay rendering-agnostic. Everything degrades gracefully on an
empty or low-data store: callers get empty lists / zeroed summaries, never errors.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


def _to_epoch(timestamp: str) -> Optional[float]:
    """Parse an ISO-8601 timestamp to epoch seconds, tolerantly."""
    if not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def _now_epoch() -> float:
    return datetime.now(timezone.utc).timestamp()


def _day(timestamp: str) -> Optional[str]:
    """Extract a YYYY-MM-DD day key from an ISO timestamp, tolerantly."""
    if not timestamp:
        return None
    ts = timestamp.strip()
    # Fast path: ISO strings start with the date.
    if len(ts) >= 10 and ts[4] == "-" and ts[7] == "-":
        return ts[:10]
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


@dataclass
class Summary:
    event_count: int = 0
    session_count: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    reasoning_output_tokens: int = 0
    first_day: Optional[str] = None
    last_day: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class Analytics:
    """Computes dashboard aggregates from rows in a UsageStore."""

    def __init__(self, store):
        self.rows = [dict(r) for r in store.all_events()]

    # -- core summaries -----------------------------------------------------

    def summary(self) -> Summary:
        s = Summary()
        s.event_count = len(self.rows)
        sessions = set()
        days = []
        for r in self.rows:
            sessions.add(r["session_id"])
            s.total_tokens += r["total_tokens"]
            s.input_tokens += r["input_tokens"]
            s.output_tokens += r["output_tokens"]
            s.cache_read_tokens += r["cache_read_tokens"]
            s.cache_write_tokens += r["cache_write_tokens"]
            s.reasoning_output_tokens += r["reasoning_output_tokens"]
            d = _day(r["timestamp"])
            if d:
                days.append(d)
        s.session_count = len(sessions)
        if days:
            days.sort()
            s.first_day, s.last_day = days[0], days[-1]
        return s

    def tokens_by_day(self) -> list[dict[str, Any]]:
        agg: dict[str, int] = defaultdict(int)
        for r in self.rows:
            d = _day(r["timestamp"])
            if d:
                agg[d] += r["total_tokens"]
        return [{"day": d, "total_tokens": agg[d]} for d in sorted(agg)]

    def provider_split(self) -> list[dict[str, Any]]:
        return self._split_by("provider")

    def model_split(self) -> list[dict[str, Any]]:
        return self._split_by("model", unknown_label="unknown")

    def _split_by(self, key: str, unknown_label: str = "unknown") -> list[dict[str, Any]]:
        agg: dict[str, int] = defaultdict(int)
        for r in self.rows:
            label = r.get(key) or unknown_label
            agg[label] += r["total_tokens"]
        return [
            {key: k, "total_tokens": v}
            for k, v in sorted(agg.items(), key=lambda kv: kv[1], reverse=True)
        ]

    def project_breakdown(self) -> list[dict[str, Any]]:
        agg: dict[str, dict[str, Any]] = {}
        for r in self.rows:
            label = r.get("project_path") or "unknown"
            bucket = agg.setdefault(
                label, {"project": label, "total_tokens": 0, "sessions": set()}
            )
            bucket["total_tokens"] += r["total_tokens"]
            bucket["sessions"].add(r["session_id"])
        out = [
            {"project": b["project"], "total_tokens": b["total_tokens"], "session_count": len(b["sessions"])}
            for b in agg.values()
        ]
        out.sort(key=lambda b: b["total_tokens"], reverse=True)
        return out

    def session_breakdown(self, limit: int = 20) -> list[dict[str, Any]]:
        agg: dict[str, dict[str, Any]] = {}
        for r in self.rows:
            sid = r["session_id"]
            bucket = agg.setdefault(
                sid,
                {
                    "session_id": sid,
                    "provider": r["provider"],
                    "project": r.get("project_path") or "unknown",
                    "total_tokens": 0,
                    "events": 0,
                    "last": "",
                },
            )
            bucket["total_tokens"] += r["total_tokens"]
            bucket["events"] += 1
            if r["timestamp"] > bucket["last"]:
                bucket["last"] = r["timestamp"]
        out = sorted(agg.values(), key=lambda b: b["total_tokens"], reverse=True)
        return out[:limit]

    # -- derived views ------------------------------------------------------

    def recent_spikes(self, limit: int = 5, factor: float = 2.0) -> list[dict[str, Any]]:
        """Days whose total exceeds ``factor`` x the median day total."""
        by_day = self.tokens_by_day()
        if len(by_day) < 2:
            return []
        totals = sorted(d["total_tokens"] for d in by_day)
        mid = len(totals) // 2
        median = totals[mid] if len(totals) % 2 else (totals[mid - 1] + totals[mid]) / 2
        if median <= 0:
            return []
        spikes = [
            {"day": d["day"], "total_tokens": d["total_tokens"], "ratio": round(d["total_tokens"] / median, 1)}
            for d in by_day
            if d["total_tokens"] >= factor * median
        ]
        spikes.sort(key=lambda d: d["day"], reverse=True)
        return spikes[:limit]

    def burn_rate(self, hours: float = 5.0, now_epoch: Optional[float] = None) -> dict[str, Any]:
        """Tokens consumed in the last ``hours`` and the implied tokens/hour.

        ``now`` defaults to the latest event time so a stale store still reports a
        meaningful recent-window rate.
        """
        pairs = [(_to_epoch(r["timestamp"]), r["total_tokens"]) for r in self.rows]
        pairs = [(e, t) for e, t in pairs if e is not None]
        if not pairs:
            return {"hours": hours, "tokens": 0, "tokens_per_hour": 0}
        now = now_epoch if now_epoch is not None else max(e for e, _ in pairs)
        cutoff = now - hours * 3600
        recent = sum(t for e, t in pairs if cutoff <= e <= now)
        return {
            "hours": hours,
            "tokens": recent,
            "tokens_per_hour": round(recent / hours) if hours else 0,
        }

    def provider_window_tokens(
        self, provider: str, window_minutes: int, now_epoch: Optional[float] = None
    ) -> int:
        """Total tokens for ``provider`` within the last ``window_minutes``."""
        pairs = [
            (_to_epoch(r["timestamp"]), r["total_tokens"])
            for r in self.rows
            if r["provider"] == provider
        ]
        pairs = [(e, t) for e, t in pairs if e is not None]
        if not pairs:
            return 0
        now = now_epoch if now_epoch is not None else max(e for e, _ in pairs)
        cutoff = now - window_minutes * 60
        return sum(t for e, t in pairs if cutoff <= e <= now)

    def trend(self, days: int = 30, today: Optional[str] = None) -> list[dict[str, Any]]:
        """Dense per-day series for the last ``days`` days (zero-filled).

        ``today`` (YYYY-MM-DD) anchors the window; if omitted it is derived from the
        latest event so a fresh install with old data still renders a useful trend.
        """
        by_day = {d["day"]: d["total_tokens"] for d in self.tokens_by_day()}
        if not by_day:
            return []
        anchor_str = today or max(by_day)
        try:
            anchor = datetime.fromisoformat(anchor_str).date()
        except ValueError:
            anchor = datetime.now(timezone.utc).date()
        series = []
        for i in range(days - 1, -1, -1):
            d = (anchor - timedelta(days=i)).isoformat()
            series.append({"day": d, "total_tokens": by_day.get(d, 0)})
        return series


# Map window keys to their nominal length in minutes for Claude budget estimates.
_WINDOW_MINUTES = {"primary_5h": 300, "secondary_weekly": 10080}
_WINDOW_LABEL = {"primary_5h": "5-hour", "secondary_weekly": "weekly"}


class LimitAnalytics:
    """Reads rate-limit snapshots and reports current limit proximity (Codex)."""

    def __init__(self, store):
        self.rows = [dict(r) for r in store.all_rate_limits()]

    def current_status(self, now_epoch: Optional[float] = None) -> list[dict[str, Any]]:
        """Latest snapshot per window with a reset countdown.

        ``now`` defaults to wall-clock UTC; tests pass a fixed value.
        """
        now = now_epoch if now_epoch is not None else _now_epoch()
        latest: dict[str, dict[str, Any]] = {}
        for r in self.rows:
            w = r["window"]
            cur = latest.get(w)
            if cur is None or r["timestamp"] > cur["timestamp"]:
                latest[w] = r
        out = []
        for w, r in latest.items():
            entry = dict(r)
            entry["window_label"] = _WINDOW_LABEL.get(w, w)
            ra = r.get("resets_at")
            entry["reset_in_seconds"] = max(0, int(ra - now)) if ra else None
            out.append(entry)
        out.sort(key=lambda x: x["window"])
        return out


def claude_budget_status(
    analytics: Analytics, budget, now_epoch: Optional[float] = None
) -> list[dict[str, Any]]:
    """Estimated Claude window usage vs an optional configured budget.

    Always an estimate (Claude logs carry no native limit data). When a window's
    budget is unset, ``used_percent`` and ``budget_tokens`` are ``None`` and callers
    should render a "configure to enable" state.
    """
    out = []
    for window, cap in (
        ("primary_5h", getattr(budget, "five_hour_tokens", None)),
        ("secondary_weekly", getattr(budget, "weekly_tokens", None)),
    ):
        minutes = _WINDOW_MINUTES[window]
        used = analytics.provider_window_tokens("claude", minutes, now_epoch)
        out.append(
            {
                "window": window,
                "window_label": _WINDOW_LABEL[window],
                "window_minutes": minutes,
                "used_tokens": used,
                "budget_tokens": cap,
                "used_percent": round(100.0 * used / cap, 1) if cap else None,
                "estimate": True,
            }
        )
    return out
