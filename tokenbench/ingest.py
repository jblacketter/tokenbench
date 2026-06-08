"""Ingestion orchestration: discover -> parse -> (optionally) store.

``ingest`` writes normalized events to SQLite. ``dry_run`` reports what would be
ingested (providers, paths, session counts, date ranges, absent sources) without
touching the database — satisfying the "report clearly when logs are absent" and
dry-run success criteria.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .parsers import parse_claude_file, parse_codex_file, parse_codex_rate_limits
from .schema import UsageEvent, RateLimitSnapshot
from .sources import SourceDiscovery, discover_all
from .storage import UsageStore, DEFAULT_DB_PATH

_PARSERS: dict[str, Callable[[Path], list[UsageEvent]]] = {
    "claude": parse_claude_file,
    "codex": parse_codex_file,
}


@dataclass
class ProviderReport:
    provider: str
    available: bool
    root: str
    file_count: int = 0
    event_count: int = 0
    session_count: int = 0
    earliest: Optional[str] = None
    latest: Optional[str] = None
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "provider": self.provider,
            "available": self.available,
            "root": self.root,
            "file_count": self.file_count,
            "event_count": self.event_count,
            "session_count": self.session_count,
            "earliest": self.earliest,
            "latest": self.latest,
            "note": self.note,
        }


@dataclass
class IngestResult:
    reports: list[ProviderReport] = field(default_factory=list)
    written: int = 0
    rate_limits_written: int = 0
    dry_run: bool = False

    @property
    def total_events(self) -> int:
        return sum(r.event_count for r in self.reports)


def _summarize(provider: str, disc: SourceDiscovery, events: list[UsageEvent]) -> ProviderReport:
    report = ProviderReport(
        provider=provider,
        available=disc.available,
        root=str(disc.root),
        file_count=disc.file_count,
    )
    if not disc.available:
        report.note = f"No {provider} logs found at {disc.root} (provider not in use, or different home)."
        return report
    if disc.file_count == 0:
        report.note = f"{provider} log directory exists but contains no parseable session files."
        return report

    report.event_count = len(events)
    report.session_count = len({e.session_id for e in events})
    timestamps = sorted(t for t in (e.timestamp for e in events) if t)
    if timestamps:
        report.earliest = timestamps[0]
        report.latest = timestamps[-1]
    if not events:
        report.note = "Files found but no token-bearing usage rows were present."
    return report


def collect(
    home: Path | None = None,
) -> tuple[list[ProviderReport], list[UsageEvent], list[RateLimitSnapshot]]:
    """Discover + parse all providers. Returns (reports, events, rate_limits). No writes."""
    reports: list[ProviderReport] = []
    all_events: list[UsageEvent] = []
    all_rate_limits: list[RateLimitSnapshot] = []
    for disc in discover_all(home):
        parser = _PARSERS[disc.provider]
        provider_events: list[UsageEvent] = []
        for path in disc.files:
            provider_events.extend(parser(path))
            if disc.provider == "codex":
                all_rate_limits.extend(parse_codex_rate_limits(path))
        reports.append(_summarize(disc.provider, disc, provider_events))
        all_events.extend(provider_events)
    return reports, all_events, all_rate_limits


def dry_run(home: Path | None = None) -> IngestResult:
    reports, events, rate_limits = collect(home)
    return IngestResult(
        reports=reports, written=0, rate_limits_written=0, dry_run=True
    )


def ingest(
    home: Path | None = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> IngestResult:
    reports, events, rate_limits = collect(home)
    with UsageStore(db_path) as store:
        written = store.upsert_events(events)
        rl_written = store.upsert_rate_limits(rate_limits)
    return IngestResult(
        reports=reports, written=written, rate_limits_written=rl_written, dry_run=False
    )


def format_report(result: IngestResult) -> str:
    """Human-readable summary for the CLI."""
    lines: list[str] = []
    if result.dry_run:
        header = "DRY RUN — no data written"
    else:
        header = (
            f"Ingested {result.written} events, "
            f"{result.rate_limits_written} rate-limit snapshots"
        )
    lines.append(header)
    lines.append("=" * len(header))
    for r in result.reports:
        status = "available" if r.available else "ABSENT"
        lines.append(f"\n[{r.provider}] {status}")
        lines.append(f"  root:     {r.root}")
        lines.append(f"  files:    {r.file_count}")
        lines.append(f"  events:   {r.event_count}")
        lines.append(f"  sessions: {r.session_count}")
        if r.earliest or r.latest:
            lines.append(f"  range:    {r.earliest or '?'} -> {r.latest or '?'}")
        if r.note:
            lines.append(f"  note:     {r.note}")
    return "\n".join(lines)
