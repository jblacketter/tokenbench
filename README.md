# TokenBench

Exploring how to effectively build AI-powered applications with token efficiency in mind.

This project collects real-world measurements, patterns, and anti-patterns for managing token consumption in LLM-driven workflows — with a focus on practical engineering decisions that compound at scale.

## Why This Matters

Token usage directly maps to cost, latency, and context window pressure. A 3x difference in token overhead per tool call becomes a 30x difference across a 10-step workflow. As AI agents get more autonomous (more tool calls, longer chains), token efficiency becomes a first-class engineering concern.

## The Dashboard (Phase 2 MVP)

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
```

The dashboard shows total tokens by day, provider/model split, project & session
breakdowns, recent spikes, a 30-day trend, and feedback cards that turn usage
patterns into behavioral nudges (spike detection, cache-utilization hints, hidden
reasoning budget, project hotspots, heavy single-thread warnings).

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
  logs contain (not live account billing or rate-limit state).
- Codex per-turn deltas are derived from the cumulative running total; sessions that
  reset mid-stream are clamped at zero per turn but still sum to the session total.
- Project attribution falls back to `unknown` when a log doesn't record a working
  directory.

## Research content (Phase 1)

**Article/Video: "Your AI Agent Is Burning 3x More Tokens Than It Needs To"**

Real measurements from a production QA workflow showing how the same browser automation task consumes 2.5x–3.8x more tokens via MCP Server vs a CLI approach. Generalizes to broader patterns for any AI application making tool calls. This research is preserved under `content/`, `examples/`, and `scripts/`.

## Project Structure

```
tokenbench/
  tokenbench/               # The dashboard package (Phase 2 MVP)
    schema.py               # Common usage_event schema + persisted-field whitelist
    sources.py              # Local log discovery (Claude + Codex)
    parsers.py              # Provider parsers (per-message vs cumulative-delta)
    storage.py              # Whitelisted SQLite store
    ingest.py               # Discover -> parse -> store, plus dry-run reporting
    analytics.py            # Daily/provider/model/project/session/spike/trend aggregates
    feedback.py             # Token-efficiency feedback cards
    dashboard.py            # Self-contained localhost web dashboard
    cli.py                  # `tokenbench` CLI (ingest / serve / status)
  tests/                    # Parser, privacy regression, and analytics tests
  docs/
    roadmap.md              # Project roadmap
    decision_log.md         # Architecture and approach decisions
    phases/                 # Per-phase plans
  examples/mcp-vs-cli/      # Raw measurements from the Northstar QA experiment (research)
  scripts/                  # MCP vs CLI demo scripts (research)
  data/                     # Local SQLite store (gitignored)
  templates/                # ai-handoff templates
```

## Quick Start

```bash
python -m tokenbench serve --open   # ingest local usage + open the dashboard
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
| 1 | MCP vs CLI case study (article + video) | In Progress |
| 2 | Standalone local token dashboard MVP | Implemented (MVP) |
| 3 | Pattern library (data delivery, query, agent loop patterns) | Not Started |
| 4 | Standardized benchmarks | Not Started |

See `docs/roadmap.md` for details.
