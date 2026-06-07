# TokenBench Benchmarks

A standardized, **offline**, deterministic token-efficiency benchmark suite. Each
benchmark *case* is a task with two or more *approaches*, measured in tokens; the
best approach is compared to a declared baseline.

This is a **living benchmark**: the current numbers are committed to
[`results.json`](results.json), and `tokenbench bench --check` fails if a fresh run
diverges from that artifact — so any change to the published numbers shows up as an
intentional, reviewable diff (e.g. when a tool/model update changes the shape of a
payload, or when the estimator is upgraded).

## Run it

```bash
python -m tokenbench bench                  # results table
python -m tokenbench bench --category "Code Search"
python -m tokenbench bench --json           # canonical results artifact (stdout)
python -m tokenbench bench --check          # verify results.json is in sync
```

## Methodology

- **Offline & deterministic.** No model/API/tokenizer calls. Token counts use the
  project's ~4-chars/token proxy (`chars_per_token` in the artifact) applied to real
  fixture payloads, with explicit **measured** overrides for captured production data
  (e.g. the MCP-vs-CLI browser-automation case). Each approach is tagged `estimated`
  or `measured`.
- **Ratios, not absolutes.** The suite reports best-vs-baseline ratios, which are
  stable under the proxy even though absolute counts are approximate.
- **Single source of truth.** Phase 3 pattern numbers enter the suite only through
  the pattern→benchmark bridge (`tokenbench/bench/cases.py`), so patterns and
  benchmarks can never disagree.

## Standard task set

| Category | Task | Source |
|----------|------|--------|
| Browser Automation | Reference + Fetch (MCP vs CLI) | measured (real) |
| API Interaction | Filtered Response | estimated (fixtures) |
| Agent Loop | Snapshot Budget | estimated (fixtures) |
| Code Search | Targeted ripgrep vs whole-file read | estimated (fixtures) |
| Document Analysis | Chunk-and-retrieve vs whole-document inline | estimated (fixtures) |

## Updating the numbers

When a case's inputs legitimately change, regenerate and commit the artifact:

```bash
python -m tokenbench bench --json > benchmarks/results.json
```

The diff on `results.json` is the record of what changed and why.

## Artifact schema

`results.json` contains `schema_version`, `chars_per_token`, and a sorted list of
`cases`, each with its approaches, baseline, best approach, and `ratio_vs_baseline`.
