# TokenBench

Exploring how to effectively build AI-powered applications with token efficiency in mind.

This project collects real-world measurements, patterns, and anti-patterns for managing token consumption in LLM-driven workflows — with a focus on practical engineering decisions that compound at scale.

## Why This Matters

Token usage directly maps to cost, latency, and context window pressure. A 3x difference in token overhead per tool call becomes a 30x difference across a 10-step workflow. As AI agents get more autonomous (more tool calls, longer chains), token efficiency becomes a first-class engineering concern.

## The Dashboard (Phase 1)

TokenBench now ships a **local-first usage dashboard** for Claude Code and Codex CLI
subscription accounts. It reads usage from your machine's own logs, normalizes it
into one schema, stores only numeric metadata in a local SQLite file, and serves a
localhost dashboard with token-efficiency feedback.

It is **standard-library only** (no third-party dependencies) and **never sends
anything off your machine**.

```bash
# See what would be ingested (no writes) — works even if a provider isn't installed:
python -m tokenbench ingest --dry-run

# Ingest local usage into data/tokenbench.sqlite3:
python -m tokenbench ingest

# Ingest (unless --no-ingest) and serve the dashboard at http://127.0.0.1:8765/
python -m tokenbench serve --open

# One-line summary of the current store:
python -m tokenbench status

# Limit proximity (Codex windows from logs) + recent burn rate:
python -m tokenbench limits
```

The dashboard shows total tokens by day, provider/model split, project & session
breakdowns, recent spikes, a 30-day trend, a **Limits** panel, a **per-provider
receipts table** (Today / 7d / 30d / peak / active days / sparkline), a **calendar
burn heatmap** (log scale), **scale equivalents** (Fermi estimates), and feedback cards
that turn usage patterns into behavioral nudges (spike detection, cache-utilization
hints, hidden reasoning budget, project hotspots, heavy single-thread warnings,
limit-proximity warnings, burn rate, and model-mix concentration).

### Limits

Codex rollouts record `rate_limits` locally, so the dashboard shows your **5-hour and
weekly Codex windows** (used %, reset countdown, plan tier) straight from your logs.
Claude Code logs carry **no** native limit data, so the Claude side is a
*configurable-budget + burn-rate estimate*, clearly labeled — set a per-window budget
to turn it into a percentage. An optional **API-equivalent value** figure estimates
what your usage would cost on metered API pricing (offline, illustrative — not your
subscription cost).

### Sources read

| Provider | Path | Token shape |
|----------|------|-------------|
| Claude Code | `~/.claude/projects/<encoded-cwd>/<session>.jsonl` | per-message `message.usage` (summed) |
| Codex CLI | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` | cumulative `payload.info.total_token_usage` (de-cumulated to per-turn deltas) |

`~/.codex/history.jsonl` is deliberately **not** parsed — it has session text but no token totals.

### Privacy boundary

The raw logs contain full prompts, responses, source code, tool output, and
secrets. TokenBench's storage layer only ever writes a **whitelist** of numeric
usage fields and identifiers (`tokenbench/schema.py`). This is enforced, not just
documented: `tests/test_privacy.py` ingests fixtures that deliberately contain
prompt/response/code/secret strings and asserts none of them reach SQLite — checking
both queried rows and the raw database bytes.

### Current limitations

- Token counts are read from local logs, so the dashboard reflects whatever those
  logs contain (not live account billing). Codex rate-limit windows come from the
  logs; Claude limit proximity is an estimate (no native log data).
- Codex per-turn deltas are derived from the cumulative running total; sessions that
  reset mid-stream are clamped at zero per turn but still sum to the session total.
- Project attribution falls back to `unknown` when a log doesn't record a working
  directory.

## Project Structure

```
tokenbench/
  tokenbench/               # The product package
    schema.py               # Common usage_event schema + persisted-field whitelist
    sources.py              # Local log discovery (Claude + Codex)
    parsers.py              # Provider parsers (per-message vs cumulative-delta)
    storage.py              # Whitelisted SQLite store
    ingest.py               # Discover -> parse -> store, plus dry-run reporting
    analytics.py            # Daily/provider/model/project/session/spike/trend aggregates
    feedback.py             # Token-efficiency feedback cards
    limits.py               # Configurable Claude budgets + offline pricing table
    equivalents.py          # Fermi "scale equivalents" from total token burn
    dashboard.py            # Self-contained localhost web dashboard
    cli.py                  # CLI (ingest / serve / status / limits / patterns / bench)
    patterns/               # Phase 2 — measurement harness + scenario registry
    bench/                  # Phase 3 — benchmark cases + runner
  patterns/                 # Phase 2 — pattern docs (measurement tables generated)
  benchmarks/               # Phase 3 — README + committed results.json
  tests/                    # Parser, privacy, analytics, patterns, and bench tests
  docs/
    roadmap.md              # Project roadmap
    decision_log.md         # Architecture and approach decisions
    phases/                 # Per-phase plans
  data/                     # Local SQLite store (gitignored)
  templates/                # handoff-workflow templates
```

## Quick Start

```bash
python -m tokenbench serve --open   # ingest local usage + open the dashboard
python -m tokenbench patterns        # measured token-efficiency patterns
python -m tokenbench bench            # standardized benchmark suite
```

Run the tests with `pytest`. See `docs/roadmap.md` for the full plan and
`docs/phases/standalone-dashboard-mvp.md` for the dashboard design.

## Key Themes

1. **Inline vs On-Demand Data** — When tools return everything vs letting you choose what to read
2. **Snapshot Overhead** — Full DOM trees, API responses, log output in every tool call
3. **Targeted Queries vs Kitchen Sink** — `eval("count")` vs full accessibility tree
4. **Token Budgets for Agents** — How to cap and manage cost in multi-step workflows
5. **Architecture Decisions That Compound** — Small per-call differences that multiply across workflows

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Standalone local token dashboard MVP | Implemented (MVP) |
| 2 | Pattern library (data delivery, query, agent loop patterns) | Implemented (MVP) |
| 3 | Standardized benchmarks | Implemented (MVP) |
| 4 | Actionable insights (limits, richer feedback) | Implemented (MVP) |
| 5 | Richer views (heatmap, receipts, scale equivalents) | Implemented (MVP) |
| 6 | Usage drivers (path-based work families, trend refinement) | In Progress |
| 7 | Project-scoped, pip-installable dashboard | Goal |

See `docs/roadmap.md` for details.
