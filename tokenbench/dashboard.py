"""Localhost web dashboard.

Renders a single self-contained HTML page from the analytics aggregates and serves
it over ``http.server`` bound to localhost. No external assets, no network calls,
no JS frameworks — charts are inline SVG so the dashboard works fully offline and
leaks nothing.
"""

from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .analytics import Analytics
from .feedback import build_feedback
from .storage import UsageStore, DEFAULT_DB_PATH


def _fmt(n: int) -> str:
    return f"{n:,}"


def _bar_rows(items: list[dict[str, Any]], label_key: str, max_rows: int = 8) -> str:
    items = items[:max_rows]
    if not items:
        return '<p class="empty">No data yet.</p>'
    top = max((i["total_tokens"] for i in items), default=0) or 1
    rows = []
    for it in items:
        label = html.escape(str(it.get(label_key) or "unknown"))
        val = it["total_tokens"]
        pct = 100.0 * val / top
        rows.append(
            f'<div class="bar-row"><span class="bar-label" title="{label}">{label}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{pct:.1f}%"></span></span>'
            f'<span class="bar-val">{_fmt(val)}</span></div>'
        )
    return "\n".join(rows)


def _trend_svg(series: list[dict[str, Any]]) -> str:
    if not series:
        return '<p class="empty">Not enough data for a trend yet.</p>'
    w, h, pad = 720, 160, 24
    vals = [d["total_tokens"] for d in series]
    vmax = max(vals) or 1
    n = len(series)
    step = (w - 2 * pad) / max(n - 1, 1)
    pts = []
    for i, v in enumerate(vals):
        x = pad + i * step
        y = h - pad - (h - 2 * pad) * (v / vmax)
        pts.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(pts)
    first, last = series[0]["day"], series[-1]["day"]
    return (
        f'<svg viewBox="0 0 {w} {h}" class="trend" preserveAspectRatio="none">'
        f'<polyline points="{polyline}" fill="none" stroke="#4f7cff" stroke-width="2"/>'
        f"</svg>"
        f'<div class="trend-axis"><span>{first}</span><span>peak {_fmt(vmax)}</span><span>{last}</span></div>'
    )


def _spike_rows(spikes: list[dict[str, Any]]) -> str:
    if not spikes:
        return '<p class="empty">No unusual spikes in the available data.</p>'
    rows = [
        f'<li><strong>{html.escape(s["day"])}</strong> — {_fmt(s["total_tokens"])} tokens '
        f'<span class="ratio">{s["ratio"]}× median</span></li>'
        for s in spikes
    ]
    return f'<ul class="spikes">{"".join(rows)}</ul>'


def _session_rows(sessions: list[dict[str, Any]]) -> str:
    if not sessions:
        return '<p class="empty">No sessions yet.</p>'
    rows = []
    for s in sessions[:10]:
        sid = html.escape(str(s["session_id"])[:12])
        project = html.escape(str(s["project"]))
        rows.append(
            f"<tr><td>{html.escape(s['provider'])}</td><td title=\"{project}\">{project}</td>"
            f"<td>{sid}…</td><td class='num'>{s['events']}</td>"
            f"<td class='num'>{_fmt(s['total_tokens'])}</td></tr>"
        )
    return (
        "<table><thead><tr><th>Provider</th><th>Project</th><th>Session</th>"
        "<th class='num'>Turns</th><th class='num'>Tokens</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _feedback_cards(cards) -> str:
    out = []
    for c in cards:
        out.append(
            f'<div class="card sev-{html.escape(c.severity)}">'
            f'<h3>{html.escape(c.title)}</h3><p>{html.escape(c.detail)}</p></div>'
        )
    return "\n".join(out)


_STYLE = """
* { box-sizing: border-box; }
body { font-family: -apple-system, system-ui, sans-serif; margin: 0; background: #0f1115; color: #e6e8ee; }
header { padding: 24px 32px; border-bottom: 1px solid #20242e; }
header h1 { margin: 0; font-size: 20px; }
header p { margin: 4px 0 0; color: #8b90a0; font-size: 13px; }
main { padding: 24px 32px; display: grid; gap: 20px; grid-template-columns: repeat(2, 1fr); max-width: 1200px; }
section { background: #161922; border: 1px solid #20242e; border-radius: 10px; padding: 18px; }
section.wide { grid-column: 1 / -1; }
section h2 { margin: 0 0 14px; font-size: 14px; text-transform: uppercase; letter-spacing: .05em; color: #9aa0b4; }
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.stat { background: #0f1115; border-radius: 8px; padding: 12px; }
.stat .v { font-size: 22px; font-weight: 600; }
.stat .l { font-size: 12px; color: #8b90a0; margin-top: 2px; }
.bar-row { display: grid; grid-template-columns: 140px 1fr 90px; gap: 10px; align-items: center; margin: 6px 0; font-size: 13px; }
.bar-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #c4c8d4; }
.bar-track { background: #0f1115; border-radius: 4px; height: 14px; overflow: hidden; }
.bar-fill { display: block; height: 100%; background: linear-gradient(90deg,#4f7cff,#7a5cff); }
.bar-val { text-align: right; color: #9aa0b4; font-variant-numeric: tabular-nums; }
.trend { width: 100%; height: 160px; }
.trend-axis { display: flex; justify-content: space-between; color: #8b90a0; font-size: 12px; margin-top: 4px; }
ul.spikes { list-style: none; padding: 0; margin: 0; }
ul.spikes li { padding: 6px 0; border-bottom: 1px solid #20242e; font-size: 13px; }
.ratio { color: #ff9f4f; margin-left: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #20242e; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.card { border-radius: 8px; padding: 14px; border-left: 3px solid #4f7cff; background: #0f1115; }
.card h3 { margin: 0 0 6px; font-size: 14px; }
.card p { margin: 0; font-size: 13px; color: #c4c8d4; line-height: 1.45; }
.sev-watch { border-left-color: #ff9f4f; }
.sev-alert { border-left-color: #ff5f6e; }
.sev-info { border-left-color: #4f7cff; }
.empty { color: #6b7080; font-size: 13px; font-style: italic; }
footer { padding: 16px 32px; color: #6b7080; font-size: 12px; }
"""


def render_html(store: UsageStore) -> str:
    analytics = Analytics(store)
    s = analytics.summary()
    cards = build_feedback(analytics)

    range_str = (
        f"{s.first_day} → {s.last_day}" if s.first_day else "no data yet"
    )

    stats = "".join(
        f'<div class="stat"><div class="v">{v}</div><div class="l">{l}</div></div>'
        for v, l in [
            (_fmt(s.total_tokens), "total tokens"),
            (_fmt(s.event_count), "events"),
            (_fmt(s.session_count), "sessions"),
            (_fmt(s.reasoning_output_tokens), "reasoning tokens"),
        ]
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TokenBench</title><style>{_STYLE}</style></head>
<body>
<header>
  <h1>TokenBench — local token usage</h1>
  <p>Claude Code + Codex CLI · {range_str} · privacy-first (no prompts/code stored)</p>
</header>
<main>
  <section class="wide"><h2>Overview</h2><div class="stat-grid">{stats}</div></section>

  <section class="wide"><h2>30-day trend</h2>{_trend_svg(analytics.trend())}</section>

  <section><h2>Provider split</h2>{_bar_rows(analytics.provider_split(), "provider")}</section>
  <section><h2>Model split</h2>{_bar_rows(analytics.model_split(), "model")}</section>

  <section><h2>Project breakdown</h2>{_bar_rows(analytics.project_breakdown(), "project")}</section>
  <section><h2>Recent spikes</h2>{_spike_rows(analytics.recent_spikes())}</section>

  <section class="wide"><h2>Top sessions</h2>{_session_rows(analytics.session_breakdown())}</section>

  <section class="wide"><h2>Feedback</h2><div class="cards">{_feedback_cards(cards)}</div></section>
</main>
<footer>TokenBench v0.1 · data read locally from ~/.claude and ~/.codex · nothing leaves this machine.</footer>
</body></html>"""


def render_json(store: UsageStore) -> dict[str, Any]:
    analytics = Analytics(store)
    return {
        "summary": analytics.summary().as_dict(),
        "tokens_by_day": analytics.tokens_by_day(),
        "provider_split": analytics.provider_split(),
        "model_split": analytics.model_split(),
        "project_breakdown": analytics.project_breakdown(),
        "session_breakdown": analytics.session_breakdown(),
        "recent_spikes": analytics.recent_spikes(),
        "trend": analytics.trend(),
        "feedback": [c.as_dict() for c in build_feedback(analytics)],
    }


def _make_handler(db_path: Path | str):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            if self.path.rstrip("/") in ("", "/index.html"):
                with UsageStore(db_path) as store:
                    body = render_html(store).encode("utf-8")
                self._send(body, "text/html; charset=utf-8")
            elif self.path.rstrip("/") == "/api/summary":
                with UsageStore(db_path) as store:
                    body = json.dumps(render_json(store), default=str).encode("utf-8")
                self._send(body, "application/json")
            else:
                self.send_error(404, "Not found")

        def log_message(self, *args) -> None:  # silence default stderr logging
            return

    return Handler


def serve(
    db_path: Path | str = DEFAULT_DB_PATH,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> ThreadingHTTPServer:
    """Build and return a server bound to localhost. Caller runs serve_forever()."""
    handler = _make_handler(db_path)
    return ThreadingHTTPServer((host, port), handler)
