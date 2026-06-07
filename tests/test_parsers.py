"""Parser correctness, including the critical Codex de-cumulation rule."""

from __future__ import annotations

from pathlib import Path

from tokenbench.parsers import parse_claude_file, parse_codex_file
from tokenbench.sources import decode_claude_project_dir, discover_all

FIXTURES = Path(__file__).parent / "fixtures"


def test_claude_per_message_parsing():
    events = parse_claude_file(FIXTURES / "claude_session.jsonl")
    # Two assistant messages carry usage; meta + user rows are skipped.
    assert len(events) == 2
    assert all(e.provider == "claude" for e in events)
    assert sum(e.input_tokens for e in events) == 2500
    assert sum(e.output_tokens for e in events) == 750
    assert sum(e.cache_read_tokens for e in events) == 2200
    assert sum(e.cache_write_tokens for e in events) == 200
    # total recomputed from components per event.
    assert events[0].total_tokens == 2000
    assert events[1].total_tokens == 3650
    assert events[0].model == "claude-opus-4"


def test_claude_project_path_decoded():
    # The fixture lives under an encoded project dir name when discovered via home,
    # but parse_claude_file uses the parent dir name; here parent is "fixtures".
    events = parse_claude_file(FIXTURES / "claude_session.jsonl")
    assert events[0].metadata["encoded_project"] == "fixtures"


def test_decode_claude_project_dir():
    assert decode_claude_project_dir("-Users-jack-projects-foo") == "/Users/jack/projects/foo"
    assert decode_claude_project_dir("") == ""


def test_codex_decumulation_sums_to_final_total():
    """The single most important rule: per-turn deltas must sum to the final
    cumulative total, NOT to the (vastly inflated) sum of cumulative rows."""
    events = parse_codex_file(FIXTURES / "codex_rollout.jsonl")
    assert len(events) == 3
    assert all(e.provider == "codex" for e in events)

    # Final cumulative total in the fixture is 1,805,100.
    summed = sum(e.total_tokens for e in events)
    assert summed == 1_805_100

    # Sanity: naive summing of cumulative rows would be ~2.7M — far larger.
    naive = 1250 + 903620 + 1805100
    assert summed < naive

    # cached_input maps to cache_read; cache_write stays 0 for Codex.
    assert sum(e.cache_read_tokens for e in events) == 1_800_000
    assert all(e.cache_write_tokens == 0 for e in events)
    assert sum(e.reasoning_output_tokens for e in events) == 200


def test_codex_project_path_from_cwd():
    events = parse_codex_file(FIXTURES / "codex_rollout.jsonl")
    assert events[0].project_path == "/Users/jack/projects/demo"


def test_discovery_finds_both_and_ignores_history(fake_home):
    discoveries = {d.provider: d for d in discover_all(fake_home)}
    assert discoveries["claude"].available and discoveries["claude"].file_count == 1
    assert discoveries["codex"].available and discoveries["codex"].file_count == 1
    # history.jsonl is not under sessions/ glob, so it's excluded.
    assert all("history.jsonl" not in str(p) for p in discoveries["codex"].files)


def test_discovery_absent(empty_home):
    discoveries = {d.provider: d for d in discover_all(empty_home)}
    assert not discoveries["claude"].available
    assert not discoveries["codex"].available
