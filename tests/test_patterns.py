"""Pattern-library harness: determinism, correctness, and doc-in-sync guarantees."""

from __future__ import annotations

from tokenbench.patterns import (
    all_scenarios,
    estimate_tokens,
    get_scenario,
    render_markdown,
    render_table,
)
from tokenbench.patterns import docgen


def test_estimate_tokens_is_char_proxy():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1           # 4 chars / 4
    assert estimate_tokens("abcde") == 2          # ceil(5/4)
    assert estimate_tokens("x" * 400) == 100


def test_all_three_families_present():
    families = {s.family for s in all_scenarios()}
    assert families == {"Data Delivery", "Query", "Agent Loop"}


def test_every_scenario_saves_tokens():
    for s in all_scenarios():
        m = s.measure()
        assert m["baseline_tokens"] > m["efficient_tokens"]
        assert m["saved_tokens"] > 0
        assert m["ratio"] > 1
        assert 0 < m["reduction_pct"] <= 100


def test_measurements_are_deterministic():
    """Same inputs → identical numbers on every run (no Date/random/IO variance)."""
    first = [s.measure() for s in all_scenarios()]
    second = [s.measure() for s in all_scenarios()]
    assert first == second


def test_query_scenario_uses_real_captured_numbers():
    q = get_scenario("reference-fetch")
    m = q.measure()
    # Real captured browser-automation measurement (inline vs snapshot-to-file).
    assert m["baseline_tokens"] == 3075
    assert m["efficient_tokens"] == 800
    assert m["source"] == "measured"
    assert m["ratio"] == 3.84


def test_render_table_and_markdown_smoke():
    scenarios = all_scenarios()
    table = render_table(scenarios)
    assert "family" in table and "ratio" in table
    md = render_markdown(scenarios)
    for s in scenarios:
        assert s.pattern in md
    # Markdown reflects the real query numbers.
    assert "3,075" in md and "800" in md


def test_docs_are_in_sync_with_harness():
    """The single most important guarantee: pattern docs' measurement tables match
    the harness output exactly, so prose cannot drift from the numbers."""
    problems = docgen.check_all()
    assert problems == [], f"docs out of sync: {problems}"


def test_sync_is_idempotent():
    # After a sync, a second sync changes nothing.
    docgen.sync_all()
    assert docgen.sync_all() == []
