# TokenBench

Exploring how to effectively build AI-powered applications with token efficiency in mind.

This project collects real-world measurements, patterns, and anti-patterns for managing token consumption in LLM-driven workflows — with a focus on practical engineering decisions that compound at scale.

## Why This Matters

Token usage directly maps to cost, latency, and context window pressure. A 3x difference in token overhead per tool call becomes a 30x difference across a 10-step workflow. As AI agents get more autonomous (more tool calls, longer chains), token efficiency becomes a first-class engineering concern.

## First Deliverable

**Article/Video: "Your AI Agent Is Burning 3x More Tokens Than It Needs To"**

Real measurements from a production QA workflow showing how the same browser automation task consumes 2.5x–3.8x more tokens via MCP Server vs a CLI approach. Generalizes to broader patterns for any AI application making tool calls.

## Project Structure

```
tokenbench/
  docs/
    roadmap.md              # Project roadmap (4 phases)
    article-outline.md      # Full outline for the MCP vs CLI article/video
    decision_log.md         # Architecture and approach decisions
  examples/
    mcp-vs-cli/
      comparison-data.md    # Raw measurements from the Northstar QA experiment
  data/                     # Raw measurements, token counts (Phase 2+)
  scripts/                  # Token measurement utilities (Phase 2+)
  templates/                # ai-handoff templates
```

## Quick Start

**Phase 1** is in progress — all source data is captured, article outline is drafted.

See `docs/roadmap.md` for the full plan, or start with:
- `examples/mcp-vs-cli/comparison-data.md` — the raw numbers
- `docs/article-outline.md` — article/video structure

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
| 2 | Token measurement toolkit | Not Started |
| 3 | Pattern library (data delivery, query, agent loop patterns) | Not Started |
| 4 | Standardized benchmarks | Not Started |

See `docs/roadmap.md` for details.
