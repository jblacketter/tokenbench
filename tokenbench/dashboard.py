"""Localhost web dashboard.

Renders a single self-contained HTML page from the analytics aggregates and serves
it over ``http.server`` bound to localhost. No external assets, no network calls,
no JS frameworks — charts are inline SVG so the dashboard works fully offline and
leaks nothing.
"""

from __future__ import annotations

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .analytics import Analytics, LimitAnalytics, claude_budget_status, _now_epoch
from .equivalents import CAVEAT, as_dicts as equivalents_as_dicts
from .feedback import build_feedback
from .limits import DEFAULT_CLAUDE_BUDGET, api_equivalent_usd
from .storage import UsageStore, DEFAULT_DB_PATH


def _fmt(n: int) -> str:
    return f"{n:,}"


def _shorten_project(path: str) -> str:
    """Show a readable project name (basename) instead of a long absolute path."""
    if not path or path == "unknown":
        return path or "unknown"
    base = os.path.basename(path.rstrip("/"))
    return base or path


def _bar_rows(
    items: list[dict[str, Any]],
    label_key: str,
    max_rows: int = 8,
    shorten: bool = False,
) -> str:
    items = items[:max_rows]
    if not items:
        return '<p class="empty">No data yet.</p>'
    top = max((i["total_tokens"] for i in items), default=0) or 1
    rows = []
    for it in items:
        full = str(it.get(label_key) or "unknown")
        display = _shorten_project(full) if shorten else full
        label = html.escape(display)
        title = html.escape(full)
        val = it["total_tokens"]
        pct = 100.0 * val / top
        rows.append(
            f'<div class="bar-row"><span class="bar-label" title="{title}">{label}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{pct:.1f}%"></span></span>'
            f'<span class="bar-val">{_fmt(val)}</span></div>'
        )
    return "\n".join(rows)


def _trend_svg(series: list[dict[str, Any]]) -> str:
    """Daily trend with a trailing moving-average overlay when present.

    Each item is ``{day, total_tokens[, moving_avg]}``. The raw line is drawn faint
    and the moving average bold so the smoothed direction reads at a glance.
    """
    if not series:
        return '<p class="empty">Not enough data for a trend yet.</p>'
    w, h, pad = 720, 160, 24
    vals = [d["total_tokens"] for d in series]
    has_ma = "moving_avg" in series[0]
    ma_vals = [d.get("moving_avg", 0) for d in series] if has_ma else []
    vmax = max(vals + ma_vals) or 1
    n = len(series)
    step = (w - 2 * pad) / max(n - 1, 1)

    def line(values):
        return " ".join(
            f"{pad + i * step:.1f},{h - pad - (h - 2 * pad) * (v / vmax):.1f}"
            for i, v in enumerate(values)
        )

    raw_stroke = "#4f7cff" if not has_ma else "#34406a"
    parts = [f'<polyline points="{line(vals)}" fill="none" stroke="{raw_stroke}" stroke-width="1.5"/>']
    if has_ma:
        parts.append(
            f'<polyline points="{line(ma_vals)}" fill="none" stroke="#5a7ff0" stroke-width="2.5"/>'
        )
    first, last = series[0]["day"], series[-1]["day"]
    ma_note = " · bold = 7-day avg" if has_ma else ""
    return (
        f'<svg viewBox="0 0 {w} {h}" class="trend" preserveAspectRatio="none">{"".join(parts)}</svg>'
        f'<div class="trend-axis"><span>{first}</span>'
        f'<span>peak {_fmt(vmax)}{ma_note}</span><span>{last}</span></div>'
    )


def _spike_rows(spikes: list[dict[str, Any]]) -> str:
    if not spikes:
        return '<p class="empty">No unusual spikes in the available data.</p>'
    rows = []
    for s in spikes:
        label = ""
        fam = s.get("family")
        if fam:
            dom = _shorten_project(str(s.get("dominant_project") or ""))
            label = (
                f' <span class="muted">— {html.escape(fam)}'
                f'{f" ({html.escape(dom)})" if dom else ""}</span>'
            )
        rows.append(
            f'<li><strong>{html.escape(s["day"])}</strong> — {_fmt(s["total_tokens"])} tokens '
            f'<span class="ratio">{s["ratio"]}× median</span>{label}</li>'
        )
    return f'<ul class="spikes">{"".join(rows)}</ul>'


def _drivers_section(families: list[dict[str, Any]]) -> str:
    if not families:
        return '<p class="empty">No data yet.</p>'
    top = max((f["total_tokens"] for f in families), default=0) or 1
    rows = []
    for f in families:
        pct = 100.0 * f["total_tokens"] / top
        evidence = ", ".join(
            _shorten_project(str(e["project"])) for e in f.get("evidence", [])
        )
        rows.append(
            f'<div class="bar-row"><span class="bar-label" title="{html.escape(evidence)}">'
            f'{html.escape(f["family"])}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{pct:.1f}%"></span></span>'
            f'<span class="bar-val">{f["share"]}%</span></div>'
            f'<div class="muted small driver-evidence">{html.escape(evidence)}</div>'
        )
    return "\n".join(rows)


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


def _fmt_countdown(seconds) -> str:
    if not seconds:
        return ""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h >= 24:
        return f"resets in ~{h // 24}d {h % 24}h"
    if h >= 1:
        return f"resets in ~{h}h {m}m"
    return f"resets in ~{max(1, m)}m"


def _limit_meter(label: str, pct, sub: str) -> str:
    if pct is None:
        return (
            f'<div class="meter"><div class="meter-head"><span>{html.escape(label)}</span>'
            f'<span class="muted">{html.escape(sub)}</span></div>'
            f'<div class="meter-track"><span class="meter-fill na" style="width:0%"></span></div></div>'
        )
    pct = max(0.0, min(100.0, float(pct)))
    sev = "ok"
    if pct >= 90:
        sev = "alert"
    elif pct >= 75:
        sev = "warn"
    return (
        f'<div class="meter"><div class="meter-head"><span>{html.escape(label)}</span>'
        f'<span><strong>{pct:.0f}%</strong> <span class="muted">{html.escape(sub)}</span></span></div>'
        f'<div class="meter-track"><span class="meter-fill {sev}" style="width:{pct:.0f}%"></span></div></div>'
    )


def _limits_section(codex_status: list[dict], claude_status: list[dict]) -> str:
    blocks = []

    # Codex — from local logs.
    plan = next((s.get("plan_type") for s in codex_status if s.get("plan_type")), None)
    codex_title = "Codex" + (f" ({html.escape(str(plan))})" if plan else "")
    if codex_status:
        meters = "".join(
            _limit_meter(
                s.get("window_label", s.get("window", "window")),
                s.get("used_percent"),
                _fmt_countdown(s.get("reset_in_seconds")),
            )
            for s in codex_status
        )
        codex_html = f'<div class="limit-col"><h3>{codex_title}</h3>{meters}</div>'
    else:
        codex_html = (
            '<div class="limit-col"><h3>Codex</h3>'
            '<p class="empty">No Codex rate-limit data ingested yet.</p></div>'
        )

    # Claude — estimate against a configurable budget (logs carry no native limits).
    claude_meters = []
    for s in claude_status:
        if s.get("budget_tokens"):
            claude_meters.append(
                _limit_meter(
                    s["window_label"],
                    s.get("used_percent"),
                    f"{_fmt(s['used_tokens'])} / {_fmt(s['budget_tokens'])} (est.)",
                )
            )
        else:
            claude_meters.append(
                _limit_meter(
                    s["window_label"], None, f"{_fmt(s['used_tokens'])} used — set a budget"
                )
            )
    claude_html = (
        '<div class="limit-col"><h3>Claude <span class="muted">(estimate)</span></h3>'
        + "".join(claude_meters)
        + '<p class="muted small">Claude logs carry no native limit data; configure '
        "per-window budgets to turn these into percentages.</p></div>"
    )

    blocks.append(f'<div class="limit-grid">{codex_html}{claude_html}</div>')
    return "".join(blocks)


_HEAT_COLORS = ["#161922", "#23314f", "#2f4a86", "#3f63c0", "#5a7ff0", "#86a6ff"]  # level 0..5


def _sparkline_svg(values: list[int]) -> str:
    if not values or max(values) == 0:
        return '<span class="muted small">—</span>'
    w, h = 120, 24
    vmax = max(values) or 1
    n = len(values)
    step = w / max(n - 1, 1)
    pts = " ".join(
        f"{i * step:.1f},{h - (h - 2) * (v / vmax):.1f}" for i, v in enumerate(values)
    )
    return (
        f'<svg viewBox="0 0 {w} {h}" class="spark" preserveAspectRatio="none">'
        f'<polyline points="{pts}" fill="none" stroke="#4f7cff" stroke-width="1.5"/></svg>'
    )


def _heatmap_svg(hm: dict) -> str:
    days = hm.get("days") or []
    if not days:
        return '<p class="empty">Not enough data for a heatmap yet.</p>'
    weeks = hm["weeks"]
    cell, gap, pad = 12, 3, 2
    width = pad * 2 + weeks * (cell + gap)
    height = pad * 2 + 7 * (cell + gap)
    rects = []
    for c in days:
        x = pad + c["week"] * (cell + gap)
        y = pad + c["weekday"] * (cell + gap)
        color = _HEAT_COLORS[min(c["level"], len(_HEAT_COLORS) - 1)]
        title = f'{c["day"]}: {c["tokens"]:,} tokens'
        rects.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{color}">'
            f"<title>{html.escape(title)}</title></rect>"
        )
    legend = "".join(
        f'<rect x="{i * 16}" y="0" width="12" height="12" rx="2" fill="{c}"/>'
        for i, c in enumerate(_HEAT_COLORS)
    )
    lw = len(_HEAT_COLORS) * 16
    return (
        f'<div class="heat-scroll"><svg viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" class="heatmap">{"".join(rects)}</svg></div>'
        f'<div class="heat-legend"><span class="muted small">{html.escape(hm["first"])}</span>'
        f'<span class="muted small">less</span>'
        f'<svg viewBox="0 0 {lw} 12" width="{lw}" height="12">{legend}</svg>'
        f'<span class="muted small">more · log scale</span>'
        f'<span class="muted small">{html.escape(hm["last"])}</span></div>'
    )


def _receipts_table(windows: list[dict]) -> str:
    if not windows:
        return '<p class="empty">No data yet.</p>'
    rows = []
    for w in windows:
        name = "Total" if w["provider"] == "total" else str(w["provider"]).capitalize()
        peak = w["peak_day"]
        rows.append(
            f"<tr><td>{html.escape(name)}</td>"
            f"<td class='num'>{_fmt(w['today'])}</td>"
            f"<td class='num'>{_fmt(w['last_7d'])}</td>"
            f"<td class='num'>{_fmt(w['last_30d'])}</td>"
            f"<td>{html.escape(peak['day'])} <span class='muted'>({_fmt(peak['tokens'])})</span></td>"
            f"<td class='num'>{w['active_days']}</td>"
            f"<td>{_sparkline_svg(w['sparkline'])}</td></tr>"
        )
    return (
        "<table><thead><tr><th>Tool</th><th class='num'>Today</th><th class='num'>7d</th>"
        "<th class='num'>30d</th><th>Peak day</th><th class='num'>Active days</th>"
        "<th>30d</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _equivalents_section(total_tokens: int) -> str:
    items = equivalents_as_dicts(total_tokens)
    if not items:
        return '<p class="empty">No data yet.</p>'
    cards = "".join(
        f'<div class="equiv"><div class="equiv-measure muted small">{html.escape(e["measure"])}</div>'
        f'<div class="equiv-est">{html.escape(e["estimate"])}</div>'
        f'<div class="equiv-eq muted">{html.escape(e["equivalent"])}</div>'
        f'<div class="equiv-basis muted small" title="{html.escape(e["basis"])}">{html.escape(e["basis"])}</div></div>'
        for e in items
    )
    return f'<div class="equiv-grid">{cards}</div><p class="muted small">{html.escape(CAVEAT)}</p>'


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
.muted { color: #8b90a0; }
.small { font-size: 12px; }
.limit-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.limit-col h3 { margin: 0 0 12px; font-size: 14px; }
.meter { margin: 10px 0; }
.meter-head { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px; }
.meter-track { background: #0f1115; border-radius: 5px; height: 12px; overflow: hidden; }
.meter-fill { display: block; height: 100%; background: #4f7cff; }
.meter-fill.warn { background: #ff9f4f; }
.meter-fill.alert { background: #ff5f6e; }
.meter-fill.na { background: #2a2f3a; }
.heat-scroll { overflow-x: auto; padding-bottom: 4px; }
.heatmap { display: block; }
.heat-legend { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.spark { width: 120px; height: 24px; }
.equiv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; }
.equiv { background: #0f1115; border-radius: 8px; padding: 14px; }
.equiv-est { font-size: 20px; font-weight: 600; margin: 2px 0; }
.equiv-basis { margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.driver-evidence { margin: -2px 0 8px 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
footer { padding: 16px 32px; color: #6b7080; font-size: 12px; }
"""


def _scope_line(scope: dict[str, Any]) -> str:
    """Human-readable scope descriptor for the dashboard header."""
    if not scope["scoped"]:
        return "machine-wide · all projects"
    proj = html.escape(str(scope["project"]))
    return (
        f"scoped to <strong>{proj}</strong> · {scope['token_share']}% of machine "
        f"tokens ({_fmt(scope['scoped_tokens'])} / {_fmt(scope['machine_tokens'])})"
    )


def render_html(store: UsageStore, project: str | None = None) -> str:
    analytics = Analytics(store, project=project)
    s = analytics.summary()
    scope = analytics.scope_info()
    now = _now_epoch()
    codex_limits = LimitAnalytics(store).current_status(now_epoch=now)
    claude_limits = claude_budget_status(analytics, DEFAULT_CLAUDE_BUDGET, now_epoch=now)
    cards = build_feedback(analytics, limit_status=codex_limits)
    # API-equivalent value follows the active scope (uses the already-filtered rows).
    cost_usd = api_equivalent_usd(analytics.rows)

    range_str = (
        f"{s.first_day} → {s.last_day}" if s.first_day else "no data yet"
    )
    # Codex rate limits are an account signal, not per-project; say so when scoped.
    limits_note = (
        '<p class="muted small">Rate limits are account-wide, not project-scoped.</p>'
        if scope["scoped"]
        else ""
    )

    stats = "".join(
        f'<div class="stat"><div class="v">{v}</div><div class="l">{l}</div></div>'
        for v, l in [
            (_fmt(s.total_tokens), "total tokens"),
            (_fmt(s.event_count), "events"),
            (_fmt(s.session_count), "sessions"),
            (f"${cost_usd:,.0f}", "API-equiv. value*"),
        ]
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TokenBench</title><style>{_STYLE}</style></head>
<body>
<header>
  <h1>TokenBench — local token usage</h1>
  <p>Claude Code + Codex CLI · {range_str} · {_scope_line(scope)} · privacy-first (no prompts/code stored)</p>
</header>
<main>
  <section class="wide"><h2>Overview</h2><div class="stat-grid">{stats}</div></section>

  <section class="wide"><h2>Limits</h2>{limits_note}{_limits_section(codex_limits, claude_limits)}</section>

  <section class="wide"><h2>Receipts</h2>{_receipts_table(analytics.provider_windows())}</section>

  <section class="wide"><h2>Daily burn heatmap</h2>{_heatmap_svg(analytics.heatmap())}</section>

  <section class="wide"><h2>30-day trend</h2>{_trend_svg(analytics.trend_smoothed())}</section>

  <section class="wide"><h2>Burn drivers</h2>{_drivers_section(analytics.work_families())}</section>

  <section class="wide"><h2>Scale equivalents</h2>{_equivalents_section(s.total_tokens)}</section>

  <section><h2>Provider split</h2>{_bar_rows(analytics.provider_split(), "provider")}</section>
  <section><h2>Model split</h2>{_bar_rows(analytics.model_split(), "model")}</section>

  <section><h2>Project breakdown</h2>{_bar_rows(analytics.project_breakdown(), "project", shorten=True)}</section>
  <section><h2>Recent spikes</h2>{_spike_rows(analytics.labeled_spikes())}</section>

  <section class="wide"><h2>Top sessions</h2>{_session_rows(analytics.session_breakdown())}</section>

  <section class="wide"><h2>Feedback</h2><div class="cards">{_feedback_cards(cards)}</div></section>
</main>
<footer>TokenBench · data read locally from ~/.claude and ~/.codex · nothing leaves this machine. *API-equivalent value is an offline estimate of metered-API cost, not your subscription cost.</footer>
</body></html>"""


def render_json(store: UsageStore, project: str | None = None) -> dict[str, Any]:
    analytics = Analytics(store, project=project)
    now = _now_epoch()
    codex_limits = LimitAnalytics(store).current_status(now_epoch=now)
    claude_limits = claude_budget_status(analytics, DEFAULT_CLAUDE_BUDGET, now_epoch=now)
    return {
        "scope": analytics.scope_info(),
        "summary": analytics.summary().as_dict(),
        "tokens_by_day": analytics.tokens_by_day(),
        "provider_split": analytics.provider_split(),
        "model_split": analytics.model_split(),
        "project_breakdown": analytics.project_breakdown(),
        "session_breakdown": analytics.session_breakdown(),
        "recent_spikes": analytics.labeled_spikes(),
        "trend": analytics.trend_smoothed(),
        "work_families": analytics.work_families(),
        "provider_windows": analytics.provider_windows(),
        "heatmap": analytics.heatmap(),
        "scale_equivalents": equivalents_as_dicts(analytics.summary().total_tokens),
        "burn_rate": analytics.burn_rate(now_epoch=now),
        "limits": {"codex": codex_limits, "claude": claude_limits},
        "api_equivalent_usd": api_equivalent_usd(analytics.rows),
        "feedback": [c.as_dict() for c in build_feedback(analytics, limit_status=codex_limits)],
    }


def _make_handler(db_path: Path | str, project: str | None = None):
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
                    body = render_html(store, project=project).encode("utf-8")
                self._send(body, "text/html; charset=utf-8")
            elif self.path.rstrip("/") == "/api/summary":
                with UsageStore(db_path) as store:
                    body = json.dumps(render_json(store, project=project), default=str).encode("utf-8")
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
    project: str | None = None,
) -> ThreadingHTTPServer:
    """Build and return a server bound to localhost. Caller runs serve_forever().

    ``project`` scopes every served page/JSON to one project path (``None`` =
    machine-wide).
    """
    handler = _make_handler(db_path, project)
    return ThreadingHTTPServer((host, port), handler)
