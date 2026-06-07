"""Analytics, feedback, dry-run, and low-data graceful-degradation tests."""

from __future__ import annotations

from tokenbench.analytics import Analytics
from tokenbench.dashboard import render_html, render_json
from tokenbench.feedback import build_feedback
from tokenbench.ingest import dry_run, ingest
from tokenbench.storage import UsageStore


def _ingested_store(fake_home, tmp_path):
    db = tmp_path / "a.sqlite3"
    ingest(home=fake_home, db_path=db)
    return UsageStore(db)


def test_summary_aggregates(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        s = Analytics(store).summary()
    # Claude total 5650 + Codex total 1,805,100.
    assert s.total_tokens == 5650 + 1_805_100
    assert s.session_count == 2  # claude-sess-1 + codex-sess-1
    assert s.first_day == "2026-06-01"
    assert s.last_day == "2026-06-02"


def test_provider_and_model_split(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        a = Analytics(store)
        providers = {p["provider"]: p["total_tokens"] for p in a.provider_split()}
        models = {m["model"]: m["total_tokens"] for m in a.model_split()}
    assert providers == {"claude": 5650, "codex": 1_805_100}
    assert models["claude-opus-4"] == 5650
    assert models["gpt-5-codex"] == 1_805_100


def test_project_breakdown(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        projects = {p["project"]: p for p in Analytics(store).project_breakdown()}
    assert "/Users/jack/projects/demo" in projects  # claude decoded + codex cwd


def test_trend_is_zero_filled_and_dense(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        trend = Analytics(store).trend(days=30)
    assert len(trend) == 30
    assert trend[-1]["day"] == "2026-06-02"  # anchored to latest event
    assert sum(d["total_tokens"] for d in trend) == 5650 + 1_805_100


def test_dry_run_writes_nothing(fake_home):
    result = dry_run(home=fake_home)
    assert result.dry_run and result.written == 0
    reports = {r.provider: r for r in result.reports}
    assert reports["claude"].available and reports["claude"].session_count == 1
    assert reports["codex"].available and reports["codex"].session_count == 1


def test_absent_sources_reported_gracefully(empty_home):
    result = dry_run(home=empty_home)
    for r in result.reports:
        assert not r.available
        assert "No" in r.note


def test_feedback_and_dashboard_on_empty_store(tmp_path):
    """Low/empty-data must not error — dashboard renders, feedback has an empty card."""
    with UsageStore(tmp_path / "empty.sqlite3") as store:
        a = Analytics(store)
        cards = build_feedback(a)
        assert any(c.key == "empty" for c in cards)
        html = render_html(store)
        assert "TokenBench" in html
        payload = render_json(store)
        assert payload["summary"]["event_count"] == 0


def test_feedback_on_real_data(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        cards = build_feedback(Analytics(store))
    assert cards and all(c.title and c.detail for c in cards)
    # Codex fixture has reasoning tokens, so a reasoning card should appear.
    assert any(c.key == "reasoning" for c in cards)


def test_dashboard_html_contains_sections(fake_home, tmp_path):
    with _ingested_store(fake_home, tmp_path) as store:
        html = render_html(store)
    for heading in ["Overview", "30-day trend", "Provider split", "Model split",
                    "Project breakdown", "Recent spikes", "Top sessions", "Feedback"]:
        assert heading in html
