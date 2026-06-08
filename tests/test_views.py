"""Richer views: per-provider receipts, calendar heatmap, and scale equivalents."""

from __future__ import annotations

from tokenbench.analytics import Analytics, heatmap_level, HEATMAP_MAX_LEVEL
from tokenbench.dashboard import render_html, render_json
from tokenbench.equivalents import scale_equivalents, as_dicts, CAVEAT
from tokenbench.ingest import ingest
from tokenbench.storage import UsageStore


def _ingested(fake_home, tmp_path):
    db = tmp_path / "views.sqlite3"
    ingest(home=fake_home, db_path=db)
    return UsageStore(db)


# -- heatmap binning (documented + stable) ------------------------------


def test_heatmap_levels_are_documented_decades():
    assert heatmap_level(0) == 0
    assert heatmap_level(1) == 1
    assert heatmap_level(999_999) == 1
    assert heatmap_level(1_000_000) == 2
    assert heatmap_level(10_000_000) == 3
    assert heatmap_level(100_000_000) == 4
    assert heatmap_level(1_000_000_000) == 5
    assert heatmap_level(5_000_000_000) == HEATMAP_MAX_LEVEL


def test_heatmap_grid_is_anchored_and_dense(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        hm = Analytics(store).heatmap(today="2026-06-02")
    assert hm["last"] == "2026-06-02"
    assert hm["first"] == "2026-06-01"  # earliest event day (Claude fixture)
    # First grid cell starts on the Monday on/before the first day; weekday 0=Mon.
    assert hm["days"][0]["weekday"] == 0
    # Every cell carries a level within range.
    assert all(0 <= c["level"] <= HEATMAP_MAX_LEVEL for c in hm["days"])


# -- per-provider receipts ----------------------------------------------


def test_provider_windows_total_and_per_provider(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        wins = {w["provider"]: w for w in Analytics(store).provider_windows(today="2026-06-02")}
    assert "total" in wins and "claude" in wins and "codex" in wins
    # Claude all on 2026-06-01, Codex all on 2026-06-02.
    assert wins["claude"]["peak_day"]["day"] == "2026-06-01"
    assert wins["codex"]["peak_day"]["day"] == "2026-06-02"
    assert wins["total"]["last_30d"] == 5650 + 1_805_100
    # 'today' (2026-06-02) sees only Codex.
    assert wins["claude"]["today"] == 0
    assert wins["codex"]["today"] == 1_805_100
    # Sparkline is a dense 30-day series.
    assert len(wins["total"]["sparkline"]) == 30


def test_provider_windows_active_days(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        wins = {w["provider"]: w for w in Analytics(store).provider_windows(today="2026-06-02")}
    assert wins["claude"]["active_days"] == 1
    assert wins["codex"]["active_days"] == 1
    assert wins["total"]["active_days"] == 2


def test_provider_windows_total_first_then_by_volume(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        order = [w["provider"] for w in Analytics(store).provider_windows(today="2026-06-02")]
    assert order[0] == "total"
    assert order.index("codex") < order.index("claude")  # codex has more tokens


# -- scale equivalents (deterministic, caveated) ------------------------


def test_scale_equivalents_deterministic_and_nonempty():
    a = scale_equivalents(1_000_000_000)
    b = scale_equivalents(1_000_000_000)
    assert a == b
    assert len(a) >= 3
    measures = {e.measure for e in a}
    assert {"Water", "Electricity", "Code volume"} <= measures


def test_scale_equivalents_empty_on_zero():
    assert scale_equivalents(0) == []
    assert as_dicts(0) == []


# -- dashboard wiring ----------------------------------------------------


def test_dashboard_has_new_sections(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        h = render_html(store)
    for heading in ["Receipts", "Daily burn heatmap", "Scale equivalents"]:
        assert f"<h2>{heading}</h2>" in h
    assert CAVEAT in h


def test_json_exposes_new_aggregates(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        j = render_json(store)
    assert "provider_windows" in j and "heatmap" in j and "scale_equivalents" in j
    assert j["heatmap"]["max_level"] == HEATMAP_MAX_LEVEL


def test_views_empty_store_safe(tmp_path):
    with UsageStore(tmp_path / "empty.sqlite3") as store:
        a = Analytics(store)
        assert a.provider_windows() == []
        assert a.heatmap()["days"] == []
        h = render_html(store)
        assert "Daily burn heatmap" in h  # renders an empty state, not an error
