"""Benchmark suite: coverage, determinism, the pattern bridge, and artifact-in-sync."""

from __future__ import annotations

import json

from tokenbench.bench import (
    all_cases,
    canonical_json,
    check_results,
    measure_all,
    render_table,
    results_payload,
)
from tokenbench.bench.runner import RESULTS_PATH
from tokenbench.patterns.scenarios import get_scenario


def test_covers_at_least_four_categories():
    categories = {c.category for c in all_cases()}
    assert len(categories) >= 4
    # The standard task set is represented.
    assert {"Browser Automation", "API Interaction", "Code Search", "Document Analysis"} <= categories


def test_every_case_has_two_plus_approaches_and_saves():
    for r in measure_all():
        assert len(r["approaches"]) >= 2
        assert r["best_tokens"] < r["baseline_tokens"]
        assert r["ratio_vs_baseline"] > 1
        assert 0 < r["reduction_pct"] <= 100


def test_results_are_deterministic():
    assert measure_all() == measure_all()
    assert canonical_json() == canonical_json()


def test_canonical_json_is_sorted_and_has_metadata():
    payload = results_payload()
    assert payload["schema_version"] == 1
    assert payload["chars_per_token"] == 4
    text = canonical_json(payload)
    # sort_keys=True → re-dumping the parsed object reproduces the text exactly.
    assert json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n" == text


def test_pattern_bridge_is_sole_source_for_phase3_numbers():
    """The Browser Automation case must carry the exact pattern Query numbers."""
    rows = {r["task"]: r for r in measure_all()}
    q = get_scenario("reference-fetch").measure()
    bridged = rows["Reference + Fetch"]
    assert bridged["baseline_tokens"] == q["baseline_tokens"] == 3075
    assert bridged["best_tokens"] == q["efficient_tokens"] == 800
    # And it is flagged measured, not estimated.
    assert any(a["source"] == "measured" for a in bridged["approaches"])


def test_committed_artifact_in_sync():
    """The living-benchmark guard: committed results.json matches a fresh run."""
    assert check_results() == [], "benchmarks/results.json is out of sync"


def test_committed_artifact_is_canonical_on_disk():
    """The committed file is byte-for-byte the canonical render (regenerable)."""
    on_disk = RESULTS_PATH.read_text(encoding="utf-8")
    assert on_disk == canonical_json()


def test_render_table_smoke():
    table = render_table()
    assert "category" in table and "ratio" in table
    assert "Browser Automation" in table
