"""Aggregations over stored usage events for the dashboard.

All functions read from a ``UsageStore`` and return plain dicts/lists so the
dashboard (and tests) stay rendering-agnostic. Everything degrades gracefully on an
empty or low-data store: callers get empty lists / zeroed summaries, never errors.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
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
    """Computes dashboard aggregates from rows in a UsageStore.

    ``project`` (optional) scopes every aggregate to one project: only events whose
    ``project_path`` is that path or a subdirectory of it are considered. When it is
    ``None`` (the default) the view is machine-wide — byte-for-byte the prior
    behavior. Scoping is a pure read-side filter; storage and ingestion are untouched.
    """

    def __init__(self, store, project: Optional[str] = None):
        from .scope import normalize_project_path, event_in_project

        all_rows = [dict(r) for r in store.all_events()]
        self.project_scope = normalize_project_path(project)
        if self.project_scope:
            self.rows = [
                r
                for r in all_rows
                if event_in_project(r.get("project_path"), self.project_scope)
            ]
        else:
            self.rows = all_rows
        # Machine-wide totals are retained so a scoped view can report its share.
        self._machine_total_tokens = sum(r["total_tokens"] for r in all_rows)
        self._machine_event_count = len(all_rows)

    def scope_info(self) -> dict[str, Any]:
        """Describe the active scope and, when scoped, its share of machine totals."""
        scoped_tokens = sum(r["total_tokens"] for r in self.rows)
        machine = self._machine_total_tokens
        return {
            "project": self.project_scope,
            "scoped": self.project_scope is not None,
            "scoped_tokens": scoped_tokens,
            "scoped_events": len(self.rows),
            "machine_tokens": machine,
            "machine_events": self._machine_event_count,
            "token_share": round(100.0 * scoped_tokens / machine, 1) if machine else 0.0,
        }

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

    # -- usage drivers ------------------------------------------------------

    def work_families(self, top_n: int = 3) -> list[dict[str, Any]]:
        """Token burn grouped into work families by project path (path-only).

        Each entry carries the family total, share %, and up to ``top_n`` evidence
        projects (the biggest contributors), so the classification is transparent.
        """
        from .drivers import classify_project

        agg: dict[str, dict[str, Any]] = {}
        for r in self.rows:
            family = classify_project(r.get("project_path"))
            bucket = agg.setdefault(family, {"tokens": 0, "projects": {}})
            bucket["tokens"] += r["total_tokens"]
            path = r.get("project_path") or "unknown"
            bucket["projects"][path] = bucket["projects"].get(path, 0) + r["total_tokens"]
        total = sum(b["tokens"] for b in agg.values()) or 1
        out = []
        for family, bucket in agg.items():
            evidence = sorted(bucket["projects"].items(), key=lambda kv: kv[1], reverse=True)
            out.append(
                {
                    "family": family,
                    "total_tokens": bucket["tokens"],
                    "share": round(100.0 * bucket["tokens"] / total, 1),
                    "evidence": [
                        {"project": p, "total_tokens": t} for p, t in evidence[:top_n]
                    ],
                }
            )
        out.sort(key=lambda x: x["total_tokens"], reverse=True)
        return out

    def labeled_spikes(self, limit: int = 5, factor: float = 2.0) -> list[dict[str, Any]]:
        """Recent spikes enriched with each day's dominant project and work family."""
        from .drivers import classify_project

        spikes = self.recent_spikes(limit=limit, factor=factor)
        if not spikes:
            return []
        day_proj: dict[str, dict[str, int]] = {}
        for r in self.rows:
            d = _day(r["timestamp"])
            if not d:
                continue
            p = r.get("project_path") or "unknown"
            day_proj.setdefault(d, {})
            day_proj[d][p] = day_proj[d].get(p, 0) + r["total_tokens"]
        for s in spikes:
            projs = day_proj.get(s["day"], {})
            if projs:
                top_project = max(projs.items(), key=lambda kv: kv[1])[0]
                s["dominant_project"] = top_project
                s["family"] = classify_project(top_project)
            else:
                s["dominant_project"] = None
                s["family"] = None
        return spikes

    def trend_smoothed(
        self, days: int = 30, window: int = 7, today: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Dense daily trend with a trailing moving average.

        The moving average uses only the days already in the ``days`` window, so the
        result is deterministic for a given ``today`` anchor (no wall-clock use).
        """
        base = self.trend(days=days, today=today)
        vals = [d["total_tokens"] for d in base]
        out = []
        for i, d in enumerate(base):
            lo = max(0, i - window + 1)
            wnd = vals[lo : i + 1]
            out.append(
                {
                    "day": d["day"],
                    "total_tokens": d["total_tokens"],
                    "moving_avg": round(sum(wnd) / len(wnd)) if wnd else 0,
                }
            )
        return out

    # -- richer views -------------------------------------------------------

    def daily_by_provider(self) -> dict[str, dict[str, int]]:
        """Per-day tokens, keyed by provider plus a synthetic ``"total"`` series."""
        out: dict[str, dict[str, int]] = {}
        for r in self.rows:
            d = _day(r["timestamp"])
            if not d:
                continue
            tok = r["total_tokens"]
            for key in (r["provider"], "total"):
                bucket = out.setdefault(key, {})
                bucket[d] = bucket.get(d, 0) + tok
        return out

    def provider_windows(self, today: Optional[str] = None) -> list[dict[str, Any]]:
        """Per-provider (and total) receipts: today / 7d / 30d / peak / active / spark.

        ``today`` anchors all windows; it defaults to the latest day in the data so
        results are deterministic without wall-clock dependence (tests pass it).
        """
        dbp = self.daily_by_provider()
        if not dbp:
            return []
        all_days = sorted({d for series in dbp.values() for d in series})
        anchor_str = today or all_days[-1]
        try:
            anchor = date.fromisoformat(anchor_str)
        except ValueError:
            anchor = date.fromisoformat(all_days[-1])

        def window_sum(series: dict[str, int], n: int) -> int:
            start = anchor - timedelta(days=n - 1)
            total = 0
            for ds, t in series.items():
                try:
                    dd = date.fromisoformat(ds)
                except ValueError:
                    continue
                if start <= dd <= anchor:
                    total += t
            return total

        results = []
        for provider, series in dbp.items():
            peak_day, peak_tokens = max(series.items(), key=lambda kv: kv[1])
            spark = [
                series.get((anchor - timedelta(days=i)).isoformat(), 0)
                for i in range(29, -1, -1)
            ]
            results.append(
                {
                    "provider": provider,
                    "today": series.get(anchor.isoformat(), 0),
                    "last_7d": window_sum(series, 7),
                    "last_30d": window_sum(series, 30),
                    "peak_day": {"day": peak_day, "tokens": peak_tokens},
                    "active_days": sum(1 for t in series.values() if t > 0),
                    "sparkline": spark,
                }
            )
        # Total row first, then providers by 30-day volume.
        results.sort(key=lambda r: (r["provider"] != "total", -r["last_30d"]))
        return results

    def heatmap(self, today: Optional[str] = None) -> dict[str, Any]:
        """Calendar grid of per-day totals with a documented log-scale level per day.

        Cells run from the Monday on/before the first day through ``today`` (default:
        latest day). Each cell carries ``weekday`` (0=Mon) and ``week`` (column index).
        """
        by_day = {d["day"]: d["total_tokens"] for d in self.tokens_by_day()}
        if not by_day:
            return {
                "days": [],
                "first": None,
                "last": None,
                "weeks": 0,
                "max_level": HEATMAP_MAX_LEVEL,
            }
        days_sorted = sorted(by_day)
        anchor_str = today or days_sorted[-1]
        try:
            anchor = date.fromisoformat(anchor_str)
        except ValueError:
            anchor = date.fromisoformat(days_sorted[-1])
        first = date.fromisoformat(days_sorted[0])
        start = first - timedelta(days=first.weekday())  # back up to Monday
        cells = []
        cur = start
        while cur <= anchor:
            iso = cur.isoformat()
            tok = by_day.get(iso, 0)
            cells.append(
                {
                    "day": iso,
                    "tokens": tok,
                    "level": heatmap_level(tok),
                    "weekday": cur.weekday(),
                    "week": (cur - start).days // 7,
                }
            )
            cur += timedelta(days=1)
        return {
            "days": cells,
            "first": days_sorted[0],
            "last": anchor.isoformat(),
            "weeks": (anchor - start).days // 7 + 1,
            "max_level": HEATMAP_MAX_LEVEL,
        }


# Documented, stable log-scale bins for the calendar heatmap. A day's level is the
# number of upper edges it meets: 0 tokens → 0; <1M → 1; <10M → 2; <100M → 3;
# <1B → 4; ≥1B → 5. Decade thresholds keep the scale stable across users/time.
HEATMAP_BIN_EDGES = (1_000_000, 10_000_000, 100_000_000, 1_000_000_000)
HEATMAP_MAX_LEVEL = len(HEATMAP_BIN_EDGES) + 1  # 5


def heatmap_level(tokens: int) -> int:
    if tokens <= 0:
        return 0
    level = 1
    for edge in HEATMAP_BIN_EDGES:
        if tokens >= edge:
            level += 1
    return level


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
