"""Project scoping: match semantics, scoped analytics, and dashboard wiring."""

from __future__ import annotations

import os

from tokenbench.analytics import Analytics
from tokenbench.dashboard import render_html, render_json
from tokenbench.ingest import ingest
from tokenbench.schema import UsageEvent
from tokenbench.scope import event_in_project, normalize_project_path
from tokenbench.storage import UsageStore

DEMO = "/Users/jack/projects/demo"  # both fixtures (Claude + Codex) live here


# -- normalize_project_path ---------------------------------------------


def test_normalize_none_and_empty_mean_machine_wide():
    assert normalize_project_path(None) is None
    assert normalize_project_path("") is None
    assert normalize_project_path("   ") is None


def test_normalize_strips_trailing_slash_and_is_absolute():
    assert normalize_project_path("/a/b/") == "/a/b"
    assert normalize_project_path("/a/b/../b") == "/a/b"


def test_normalize_expands_user():
    assert normalize_project_path("~/proj") == os.path.join(os.path.expanduser("~"), "proj")


def test_normalize_relative_resolves_against_cwd():
    assert normalize_project_path("sub/dir") == os.path.join(os.getcwd(), "sub", "dir")


# -- event_in_project ---------------------------------------------------


def test_no_target_matches_everything():
    assert event_in_project("/anything", None) is True
    assert event_in_project(None, None) is True
    assert event_in_project("", None) is True


def test_exact_and_nested_match():
    t = normalize_project_path("/a/foo")
    assert event_in_project("/a/foo", t) is True
    assert event_in_project("/a/foo/bar", t) is True
    assert event_in_project("/a/foo/bar/baz", t) is True


def test_sibling_prefix_is_not_a_match():
    t = normalize_project_path("/a/foo")
    assert event_in_project("/a/foo-bar", t) is False
    assert event_in_project("/a/foobar", t) is False
    assert event_in_project("/a/food", t) is False


def test_unrelated_and_empty_event_paths_excluded_when_scoped():
    t = normalize_project_path("/a/foo")
    assert event_in_project("/b/other", t) is False
    assert event_in_project(None, t) is False
    assert event_in_project("", t) is False
    assert event_in_project("   ", t) is False


# -- scoped analytics over the real fixtures ----------------------------


def test_scope_matching_path_keeps_all_fixture_events(fake_home, tmp_path):
    db = tmp_path / "scope.sqlite3"
    ingest(home=fake_home, db_path=db)
    with UsageStore(db) as store:
        machine = Analytics(store)
        scoped = Analytics(store, project=DEMO)
        # Every fixture event lives under DEMO, so scoping changes nothing here.
        assert scoped.summary().total_tokens == machine.summary().total_tokens
        info = scoped.scope_info()
        assert info["scoped"] is True
        assert info["project"] == DEMO
        assert info["scoped_tokens"] == info["machine_tokens"]
        assert info["token_share"] == 100.0


def test_scope_unrelated_path_yields_clean_empty_state(fake_home, tmp_path):
    db = tmp_path / "scope.sqlite3"
    ingest(home=fake_home, db_path=db)
    with UsageStore(db) as store:
        scoped = Analytics(store, project="/Users/jack/projects/nope")
        s = scoped.summary()
        assert s.event_count == 0 and s.total_tokens == 0
        info = scoped.scope_info()
        assert info["scoped"] is True
        assert info["scoped_tokens"] == 0
        assert info["machine_tokens"] > 0
        assert info["token_share"] == 0.0
        # Empty state, not an error.
        assert scoped.provider_windows() == []


def test_machine_wide_scope_info_reports_unscoped(fake_home, tmp_path):
    db = tmp_path / "scope.sqlite3"
    ingest(home=fake_home, db_path=db)
    with UsageStore(db) as store:
        info = Analytics(store).scope_info()
    assert info["scoped"] is False
    assert info["project"] is None
    assert info["scoped_tokens"] == info["machine_tokens"] > 0


# -- scoping discriminates between sibling projects ---------------------


def _two_project_store(tmp_path):
    store = UsageStore(tmp_path / "multi.sqlite3")
    store.upsert_events(
        [
            UsageEvent(
                id="a", provider="claude", source="x", timestamp="2026-06-01T00:00:00Z",
                session_id="s1", input_tokens=100, project_path="/Users/jack/projects/alpha",
            ),
            UsageEvent(
                id="a2", provider="codex", source="x", timestamp="2026-06-01T01:00:00Z",
                session_id="s3", input_tokens=50, project_path="/Users/jack/projects/alpha/sub",
            ),
            UsageEvent(
                id="b", provider="codex", source="y", timestamp="2026-06-01T00:00:00Z",
                session_id="s2", input_tokens=200, project_path="/Users/jack/projects/beta",
            ),
        ]
    )
    return store


def test_scope_excludes_siblings_includes_subdirs(tmp_path):
    with _two_project_store(tmp_path) as store:
        alpha = Analytics(store, project="/Users/jack/projects/alpha")
        # alpha + alpha/sub = 150; beta (200) excluded.
        assert alpha.summary().total_tokens == 150
        info = alpha.scope_info()
        assert info["scoped_tokens"] == 150
        assert info["machine_tokens"] == 350
        assert info["token_share"] == round(100.0 * 150 / 350, 1)


# -- dashboard wiring ----------------------------------------------------


def test_dashboard_header_shows_scope(fake_home, tmp_path):
    db = tmp_path / "scope.sqlite3"
    ingest(home=fake_home, db_path=db)
    with UsageStore(db) as store:
        machine_html = render_html(store)
        scoped_html = render_html(store, project=DEMO)
    assert "machine-wide" in machine_html
    assert "scoped to" in scoped_html and DEMO in scoped_html
    # Account-wide caveat appears only in the scoped view.
    assert "Rate limits are account-wide" in scoped_html
    assert "Rate limits are account-wide" not in machine_html


def test_json_exposes_scope(fake_home, tmp_path):
    db = tmp_path / "scope.sqlite3"
    ingest(home=fake_home, db_path=db)
    with UsageStore(db) as store:
        machine_json = render_json(store)
        scoped_json = render_json(store, project=DEMO)
    assert machine_json["scope"]["scoped"] is False
    assert scoped_json["scope"]["scoped"] is True
    assert scoped_json["scope"]["project"] == DEMO
    assert scoped_json["scope"]["machine_tokens"] >= scoped_json["scope"]["scoped_tokens"]
