# Benchmarks

## Summary

Build a standardized, versioned, **offline** token-efficiency benchmark suite. It
generalizes the Phase 3 pattern harness from two-way (baseline vs efficient)
comparisons to **multi-approach benchmark cases** across a standard task set
(browser automation, code search, API interaction, document analysis).

The suite emits a machine-readable results artifact plus a human table, and a
regression check pins the numbers — so this is a *living benchmark* where every
change to the published numbers is intentional and reviewable, not accidental
drift. It shares one measurement source of truth with the pattern library (per the
2026-06-07 decision-log follow-up).

## Scope

In scope:
- A `tokenbench/bench/` module: a `BenchmarkCase` (a task with ≥2 named approaches,
  each measured in tokens), a registry, a runner, and renderers (table + JSON).
- A bridge that turns each Phase 3 pattern `Scenario` into a 2-approach benchmark
  case, so patterns and benchmarks never duplicate numbers.
- New standard-task-set cases beyond the pattern anchors (e.g. code search,
  document analysis), using offline fixtures or real measured overrides.
- A committed, regenerable `benchmarks/results.json` snapshot of current numbers,
  with a `--check` mode that fails if a fresh run diverges from it.
- CLI: `python -m tokenbench bench [--json] [--check] [--category ...]`.
- `benchmarks/README.md` documenting methodology, the task set, and how to update.
- Tests: determinism, category coverage, and results-artifact-in-sync.

Out of scope:
- Live model / API / tokenizer calls. Measurements stay offline: the ~4-chars/token
  proxy for fixtures plus explicit real overrides for captured data (consistent with
  Phases 2–3).
- Cloud publishing, hosted dashboards, or historical time-series storage. The MVP
  ships a single current snapshot; trend history can come later.
- Any new scraping of provider logs.

## Technical Approach

1. **Generalize the primitive.** `BenchmarkCase = {task, category, baseline_label,
   approaches: [Approach(label, tokens|payload, source)]}`. Reuse
   `tokenbench.patterns.harness.estimate_tokens` and the `Variant` token logic so the
   estimator is shared, not reimplemented.
2. **Bridge from patterns.** A helper converts each pattern `Scenario` (baseline +
   efficient) into a `BenchmarkCase` with two approaches. This keeps the Query
   MCP-vs-CLI numbers and the others single-sourced.
3. **Add the standard task set.** At least four categories, each with ≥2 approaches:
   - Browser automation — reuse the MCP-vs-CLI case (measured).
   - API interaction — reuse Filtered Response (measured from fixtures).
   - Code search — grep-whole-files vs targeted ripgrep with line ranges (fixtures).
   - Document analysis — inline-whole-doc vs chunk-and-retrieve relevant sections
     (fixtures).
4. **Results artifact.** `benchmarks/results.json` is deterministic and sorted, with
   schema version, the `chars_per_token` constant, and per-case
   category/task/approach/tokens plus the best-vs-baseline ratio. `bench --check`
   recomputes and diffs against the committed file; a test asserts they match.
5. **CLI + docs.** Wire a `bench` subcommand; document methodology and the update
   workflow (`bench --json > benchmarks/results.json`).
6. **Offline & dependency-free**, matching the established package posture.

## Files

Likely new or changed:
- `docs/phases/benchmarks.md`
- `tokenbench/bench/__init__.py`
- `tokenbench/bench/cases.py` (registry: pattern bridge + new cases)
- `tokenbench/bench/runner.py` (measure, render table/JSON, check artifact)
- `tokenbench/bench/fixtures/` (offline payloads for code-search / doc-analysis)
- `benchmarks/README.md`
- `benchmarks/results.json` (generated, committed)
- `tokenbench/cli.py` (add `bench` subcommand)
- `tests/test_bench.py`
- `docs/roadmap.md` (Phase 4 status)
- `docs/decision_log.md` (benchmarks approach entry)

Reused:
- `tokenbench/patterns/` scenario registry (shared measurement source)
- `examples/mcp-vs-cli/comparison-data.md` (real browser-automation numbers)

## Success Criteria

- The suite covers **≥4 standard task categories**, each with **≥2 measured
  approaches**.
- It **reuses the Phase 3 scenario registry** as a shared source — no duplicated
  token numbers between patterns and benchmarks.
- `python -m tokenbench bench` prints a results table; `--json` emits machine-readable
  results; `--check` verifies the committed `benchmarks/results.json` is in sync
  (the living-benchmark guard).
- A committed `benchmarks/results.json` captures the current numbers and is
  regenerable deterministically (same run → identical file).
- `benchmarks/README.md` documents methodology, the task set, and the update flow.
- Tests assert determinism, category coverage, and artifact-in-sync.
- `docs/roadmap.md` and `docs/decision_log.md` are updated, and the full existing
  test suite still passes.
