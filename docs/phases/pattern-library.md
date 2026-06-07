# Pattern Library

## Summary

Build a library of generalizable token-efficiency patterns. Each pattern is
documented with a consistent template (problem, forces, solution, tradeoffs) **and
backed by a reproducible measurement**, so the library follows the project's first
principle — *measure, don't guess* — rather than offering untested advice.

Patterns are grouped into three families from the roadmap: **Data Delivery**,
**Query**, and **Agent Loop**. The existing MCP-vs-CLI case study
(`examples/mcp-vs-cli/`) becomes the first fully-measured entry, so this phase
builds directly on work already captured.

## Scope

In scope:
- A `patterns/` documentation tree: one markdown file per pattern using a shared
  template, plus an index and a short "how to read a pattern" guide.
- A lightweight, dependency-free measurement harness under `tokenbench/patterns/`
  that runs small before/after scenarios and reports token counts + ratios
  deterministically and **offline**.
- At least one fully-measured case study per family:
  - Data Delivery: inline-all vs filtered/shaped API response
  - Query: targeted eval vs full DOM/accessibility-tree scan (reusing the real
    MCP-vs-CLI numbers)
  - Agent Loop: snapshot-budget / context-pruning across a multi-step loop
- A `python -m tokenbench patterns` command that runs all registered scenarios,
  prints a table, and can emit markdown for the docs.
- Tests covering the harness and measurement reproducibility.

Out of scope:
- Live model/API calls. Measurements use captured fixtures and the established
  character-proxy estimator so they are deterministic and run offline.
- The full standardized benchmark suite / published results (that is Phase 4).
- Rewriting the Phase 1 article or changing the dashboard MVP.

## Technical Approach

1. **Reuse the established estimator.** Per the decision log (2026-02-10), use the
   ~4-chars-per-token proxy as the default, but structure the harness so an exact
   tokenizer can be plugged in later. The proxy keeps measurements deterministic and
   dependency-free, and the library cares about *ratios* between approaches, not
   absolute counts.
2. **Pattern template.** Every pattern doc has: Name · Family · Problem · Forces ·
   Solution · When to use / When not · Token impact (measured) · Tradeoffs
   (latency / ergonomics / quality) · Related patterns.
3. **Harness design** (`tokenbench/patterns/harness.py`):
   - `estimate_tokens(text)` — char-proxy estimator (pluggable).
   - `Scenario` — a named comparison with a baseline variant and an efficient
     variant, each producing a payload string; reports tokens for each, the absolute
     savings, and the ratio.
   - `run_all()` / registry — collect scenarios and render a results table or
     markdown snippet.
4. **Scenarios** (`tokenbench/patterns/scenarios.py`): at least three real,
   offline scenarios — one per family — using small fixtures (e.g. a sample API
   response, a captured DOM snippet, a multi-step tool loop transcript). The
   Query-family scenario folds in the real MCP-vs-CLI measurement so the library is
   anchored in production data, not synthetic numbers.
5. **CLI wiring.** Add a `patterns` subcommand to `tokenbench/cli.py`:
   `python -m tokenbench patterns` (table) and `--markdown` (doc-ready output).
6. **Docs generation discipline.** The measured "Token impact" tables in pattern
   docs are produced by the harness so the prose can never silently drift from the
   numbers. Reproducibility is asserted in tests.
7. **Keep it dependency-free** and consistent with the existing package style
   (stdlib only, same module conventions as the dashboard MVP).

## Files

Likely new or changed:
- `docs/phases/pattern-library.md`
- `patterns/README.md` (index + how to read a pattern)
- `patterns/data-delivery/*.md`
- `patterns/query/*.md`
- `patterns/agent-loop/*.md`
- `tokenbench/patterns/__init__.py`
- `tokenbench/patterns/harness.py`
- `tokenbench/patterns/scenarios.py`
- `tokenbench/patterns/fixtures/` (small offline payload fixtures)
- `tokenbench/cli.py` (add `patterns` subcommand)
- `tests/test_patterns.py`
- `docs/roadmap.md` (Phase 3 status)
- `docs/decision_log.md` (pattern-library approach entry)

Existing assets reused:
- `examples/mcp-vs-cli/comparison-data.md` (real Query-family measurement)

## Success Criteria

- All three pattern families (Data Delivery, Query, Agent Loop) are represented,
  each with at least one measured case study.
- Every pattern doc follows the shared template and cites a real or reproducible
  measurement (no unmeasured claims).
- `python -m tokenbench patterns` runs all scenarios **offline** and prints token
  counts + ratios; `--markdown` emits doc-ready tables.
- Measurements are deterministic and reproducible — a test asserts stable numbers
  for each scenario.
- The existing MCP-vs-CLI data is incorporated as the anchor Query-family case
  study.
- `patterns/README.md` indexes all patterns and explains how to read an entry.
- `docs/roadmap.md` and `docs/decision_log.md` are updated.
- The harness and scenarios have passing tests, and the existing suite still passes.
