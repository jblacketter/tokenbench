"""Token-efficiency feedback cards.

Each card translates an observable usage pattern into a short, behavioral nudge —
following Nate Jones' framing that token counts are a behavioral trace tied to
outcomes, not a leaderboard or cost scoreboard. Cards are advisory and always
degrade to a friendly empty/low-data state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .analytics import Analytics


@dataclass
class FeedbackCard:
    key: str
    title: str
    severity: str  # "info" | "watch" | "alert"
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


def build_feedback(analytics: Analytics) -> list[FeedbackCard]:
    cards: list[FeedbackCard] = []
    summary = analytics.summary()

    if summary.event_count == 0:
        cards.append(
            FeedbackCard(
                key="empty",
                title="No usage yet",
                severity="info",
                detail="No usage events ingested. Run `tokenbench ingest` after using "
                "Claude Code or Codex, then revisit this dashboard.",
            )
        )
        return cards

    # 1. Session spikes — unusually large days.
    spikes = analytics.recent_spikes()
    if spikes:
        top = spikes[0]
        cards.append(
            FeedbackCard(
                key="spikes",
                title="Recent token spikes",
                severity="watch",
                detail=f"{top['day']} used {top['total_tokens']:,} tokens "
                f"({top['ratio']}x your median day). Spikes often mean a long single "
                f"thread — consider splitting big tasks into fresh sessions.",
            )
        )

    # 2. Cache utilization (where visible) — high cache reads are GOOD; low is a hint.
    cacheable = summary.cache_read_tokens + summary.input_tokens
    cache_pct = _pct(summary.cache_read_tokens, cacheable)
    if cacheable > 0:
        if cache_pct < 20:
            cards.append(
                FeedbackCard(
                    key="cache",
                    title="Low cache utilization",
                    severity="watch",
                    detail=f"Only {cache_pct}% of your input was served from cache. "
                    "Reusing a stable context (same files/system prompt) across turns "
                    "lets more input hit the cache and cost far fewer tokens.",
                )
            )
        else:
            cards.append(
                FeedbackCard(
                    key="cache",
                    title="Healthy cache reuse",
                    severity="info",
                    detail=f"{cache_pct}% of input was cache-read — you're reusing "
                    "context efficiently. Keep stable context across a thread.",
                )
            )

    # 3. Reasoning budget (Codex) — hidden reasoning vs visible output.
    if summary.reasoning_output_tokens > 0:
        reasoning_pct = _pct(
            summary.reasoning_output_tokens,
            summary.reasoning_output_tokens + summary.output_tokens,
        )
        cards.append(
            FeedbackCard(
                key="reasoning",
                title="Hidden reasoning budget",
                severity="info",
                detail=f"{reasoning_pct}% of generated tokens were hidden reasoning. "
                "If a task is straightforward, a lower-reasoning mode can deliver the "
                "same outcome for fewer tokens.",
            )
        )

    # 4. Project hotspots — concentration of usage.
    projects = analytics.project_breakdown()
    if projects and summary.total_tokens > 0:
        top = projects[0]
        share = _pct(top["total_tokens"], summary.total_tokens)
        if share >= 50 and top["project"] != "unknown":
            cards.append(
                FeedbackCard(
                    key="hotspot",
                    title="Project hotspot",
                    severity="info",
                    detail=f"`{top['project']}` accounts for {share}% of all tokens. "
                    "That's where efficiency wins compound — worth a focused look.",
                )
            )

    # 5. Heavy-continuation sessions.
    sessions = analytics.session_breakdown(limit=1)
    if sessions:
        biggest = sessions[0]
        if biggest["total_tokens"] >= 2 * (summary.total_tokens / max(summary.session_count, 1)):
            cards.append(
                FeedbackCard(
                    key="long_thread",
                    title="A heavy single thread",
                    severity="watch",
                    detail=f"One session ({biggest['provider']}, {biggest['events']} turns) "
                    f"used {biggest['total_tokens']:,} tokens — well above your average. "
                    "Long threads accumulate context cost; starting fresh for a new "
                    "sub-task can be cheaper.",
                )
            )

    if len(cards) == 0:
        cards.append(
            FeedbackCard(
                key="steady",
                title="Steady, efficient usage",
                severity="info",
                detail="No notable spikes or inefficiencies detected in the available "
                "data. Keep an eye here as more usage accrues.",
            )
        )
    return cards
