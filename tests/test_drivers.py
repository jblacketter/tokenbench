"""Usage drivers: path-only classification, evidence, spike labels, moving average."""

from __future__ import annotations

from tokenbench.analytics import Analytics
from tokenbench.dashboard import render_html, render_json
from tokenbench.drivers import classify_project, family_names, OTHER_FAMILY, WORK_FAMILY_RULES
from tokenbench.ingest import ingest
from tokenbench.storage import UsageStore

from conftest import FORBIDDEN_STRINGS


def _ingested(fake_home, tmp_path):
    db = tmp_path / "drv.sqlite3"
    ingest(home=fake_home, db_path=db)
    return UsageStore(db)


# -- classifier: deterministic, ordered, explicit fallback --------------


def test_classify_uses_path_only_and_is_deterministic():
    assert classify_project("/Users/jack/projects/northstar/test/automation") == "QA & test automation"
    assert classify_project("/Users/jack/projects/linkedin-articles") == "Writing & content"
    assert classify_project("/Users/jack/projects/sonic/sonicgrid") == "Web & app"
    # Stable across calls.
    assert classify_project("/x/qa") == classify_project("/x/qa")


def test_unmatched_and_unknown_paths_are_other_mixed():
    assert classify_project("/Users/jack/projects/zzxq") == OTHER_FAMILY
    assert classify_project("") == OTHER_FAMILY
    assert classify_project(None) == OTHER_FAMILY
    assert classify_project("unknown") == OTHER_FAMILY


def test_rule_order_first_match_wins():
    # A path hitting an earlier family's keyword classifies there even if a later
    # family keyword is also present ("test" → QA, before "app" → Web).
    assert classify_project("/repo/test-app") == "QA & test automation"
    assert family_names()[-1] == OTHER_FAMILY  # fallback is last/explicit
    assert len(family_names()) == len(WORK_FAMILY_RULES) + 1


# -- work families + evidence -------------------------------------------


def test_work_families_have_share_and_evidence(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        fams = Analytics(store).work_families()
    assert fams
    assert abs(sum(f["share"] for f in fams) - 100.0) < 0.5  # shares ~sum to 100
    for f in fams:
        assert f["family"] in family_names()
        assert all("project" in e and "total_tokens" in e for e in f["evidence"])
    # Sorted by tokens desc.
    assert fams == sorted(fams, key=lambda x: x["total_tokens"], reverse=True)


# -- spike labels + moving average --------------------------------------


def test_labeled_spikes_carry_family(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        a = Analytics(store)
        spikes = a.labeled_spikes()
    # Fixture may or may not trigger spikes; if it does, labels must be present.
    for s in spikes:
        assert "family" in s and "dominant_project" in s


def test_trend_smoothed_is_deterministic_and_windowed(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        a = Analytics(store)
        t1 = a.trend_smoothed(days=30, window=7, today="2026-06-02")
        t2 = a.trend_smoothed(days=30, window=7, today="2026-06-02")
    assert t1 == t2
    assert len(t1) == 30
    assert all("moving_avg" in d and "total_tokens" in d for d in t1)
    # The last day's moving average is the mean of the trailing 7 raw values.
    last7 = [d["total_tokens"] for d in t1[-7:]]
    assert t1[-1]["moving_avg"] == round(sum(last7) / len(last7))


# -- privacy: classification never reads content ------------------------


def test_driver_outputs_contain_no_secrets(fake_home, tmp_path):
    """Classification is path-only; family/evidence output must never surface any of
    the secret strings planted in the fixtures' prompt/response/code content."""
    with _ingested(fake_home, tmp_path) as store:
        a = Analytics(store)
        blob = repr(a.work_families()) + repr(a.labeled_spikes())
    for forbidden in FORBIDDEN_STRINGS:
        assert forbidden not in blob


def test_dashboard_has_burn_drivers_section(fake_home, tmp_path):
    with _ingested(fake_home, tmp_path) as store:
        h = render_html(store)
        j = render_json(store)
    assert "<h2>Burn drivers</h2>" in h
    assert "work_families" in j
    assert "bold = 7-day avg" in h  # moving-average overlay rendered


def test_drivers_empty_store_safe(tmp_path):
    with UsageStore(tmp_path / "empty.sqlite3") as store:
        a = Analytics(store)
        assert a.work_families() == []
        assert a.labeled_spikes() == []
        assert "Burn drivers" in render_html(store)
