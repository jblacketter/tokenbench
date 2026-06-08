"""Rate-limit ingestion, limit/burn analytics, budgets, and dashboard limit views."""

from __future__ import annotations

from pathlib import Path

from tokenbench.analytics import (
    Analytics,
    LimitAnalytics,
    claude_budget_status,
    _to_epoch,
)
from tokenbench.dashboard import _shorten_project, render_html
from tokenbench.ingest import ingest
from tokenbench.limits import ClaudeBudget, DEFAULT_CLAUDE_BUDGET, api_equivalent_usd
from tokenbench.parsers import parse_codex_file, parse_codex_rate_limits
from tokenbench.schema import WINDOW_PRIMARY, WINDOW_SECONDARY
from tokenbench.storage import UsageStore

from conftest import FORBIDDEN_STRINGS

FIXTURES = Path(__file__).parent / "fixtures"


def _ingested_store(fake_home, tmp_path):
    db = tmp_path / "rl.sqlite3"
    ingest(home=fake_home, db_path=db)
    return UsageStore(db)


# -- parsing -------------------------------------------------------------


def test_codex_rate_limits_parsed():
    snaps = {s.window: s for s in parse_codex_rate_limits(FIXTURES / "codex_rollout.jsonl")}
    assert set(snaps) == {WINDOW_PRIMARY, WINDOW_SECONDARY}
    assert snaps[WINDOW_SECONDARY].window_minutes == 10080
    assert snaps[WINDOW_PRIMARY].window_minutes == 300
    assert snaps[WINDOW_SECONDARY].plan_type == "plus"
    assert snaps[WINDOW_SECONDARY].resets_at == 1780600000  # epoch seconds


def test_latest_rate_limit_comes_from_noop_cumulative_row():
    """The fixture's last token_count row repeats the cumulative total (so the usage
    parser emits NO event for it) but carries the newest rate_limits. The rate-limit
    parser must still capture it — that's the whole point of reading it independently."""
    usage = parse_codex_file(FIXTURES / "codex_rollout.jsonl")
    assert len(usage) == 3  # no-op 4th row produced no usage event

    snaps = {s.window: s for s in parse_codex_rate_limits(FIXTURES / "codex_rollout.jsonl")}
    # 78%/35% only appear on the no-op row — proves it wasn't dropped.
    assert snaps[WINDOW_SECONDARY].used_percent == 78.0
    assert snaps[WINDOW_PRIMARY].used_percent == 35.0


# -- storage + analytics -------------------------------------------------


def test_ingest_persists_rate_limits(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        rows = store.all_rate_limits()
    windows = {r["window"] for r in rows}
    assert windows == {WINDOW_PRIMARY, WINDOW_SECONDARY}


def test_current_status_reset_countdown(fake_home, tmp_path):
    now = 1780000000.0  # before both resets_at in the fixture
    with _ingested_store(fake_home, tmp_path) as store:
        status = {s["window"]: s for s in LimitAnalytics(store).current_status(now_epoch=now)}
    assert status[WINDOW_PRIMARY]["reset_in_seconds"] == 300
    assert status[WINDOW_SECONDARY]["reset_in_seconds"] == 600000
    assert status[WINDOW_SECONDARY]["used_percent"] == 78.0
    assert status[WINDOW_SECONDARY]["window_label"] == "weekly"


def test_burn_rate_and_window_tokens(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        a = Analytics(store)
        now = _to_epoch("2026-06-01T10:05:00.000Z")
        # Both Claude events (5650 total) fall within a 5h window of that 'now'.
        assert a.provider_window_tokens("claude", 300, now_epoch=now) == 5650
        burn = a.burn_rate(hours=5.0, now_epoch=now)
        assert burn["tokens"] == 5650 and burn["tokens_per_hour"] == round(5650 / 5)


def test_claude_budget_status_unconfigured_and_configured(fake_home, tmp_path):
    now = _to_epoch("2026-06-01T10:05:00.000Z")
    with _ingested_store(fake_home, tmp_path) as store:
        a = Analytics(store)
        unconf = {s["window"]: s for s in claude_budget_status(a, DEFAULT_CLAUDE_BUDGET, now)}
        conf = {
            s["window"]: s
            for s in claude_budget_status(a, ClaudeBudget(weekly_tokens=11300), now)
        }
    assert unconf[WINDOW_SECONDARY]["used_percent"] is None
    assert unconf[WINDOW_SECONDARY]["used_tokens"] == 5650
    assert unconf[WINDOW_SECONDARY]["estimate"] is True
    assert conf[WINDOW_SECONDARY]["used_percent"] == 50.0  # 5650 / 11300


# -- dashboard + cost ----------------------------------------------------


def test_shorten_project():
    assert _shorten_project("/Users/jack/projects/sonic/sonicgrid") == "sonicgrid"
    assert _shorten_project("unknown") == "unknown"
    assert _shorten_project("") == "unknown"


def test_dashboard_limits_section(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        h = render_html(store)
    assert "<h2>Limits</h2>" in h
    assert "weekly" in h and "plus" in h
    # Project breakdown shows the basename, full path stays in the title attr.
    assert ">demo<" in h
    assert 'title="/Users/jack/projects/demo"' in h


def test_api_equivalent_usd_offline_deterministic(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        rows = [dict(r) for r in store.all_events()]
    a = api_equivalent_usd(rows)
    b = api_equivalent_usd(rows)
    assert a == b and a > 0


# -- privacy: the new table must not leak either ------------------------


def test_rate_limit_table_has_no_secrets(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        assert len(store.all_rate_limits()) > 0  # actually testing a non-empty table
        dump = store.dump_text()
    for forbidden in FORBIDDEN_STRINGS:
        assert forbidden not in dump
