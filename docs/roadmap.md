# TokenBench — Project Roadmap

## Overview

Exploring how to effectively build AI-powered applications with token efficiency in mind. The project started as an article/video case study about MCP vs CLI token overhead, and is now expanding into a local-first usage dashboard for Claude Code and Codex CLI subscription accounts.

**Tech Stack:** Python, Playwright, Claude Code, MCP

**Workflow:** Lead / Reviewer with Human Arbiter (see tagteam.yaml for agent configuration)

## Phases

### Phase 1: MCP Server vs Playwright CLI Case Study
- **Status:** In Progress
- **Description:** Publish an article/video demonstrating token cost differences with real measurements from a production QA workflow. Same browser automation task, two approaches, 2.5x–3.8x token cost difference.
- **Key Deliverables:**
  - Article/blog post (~2,000 words) with comparison tables and architecture diagrams
  - Video walkthrough showing both approaches side-by-side
  - Reproducible example scripts
  - Raw comparison data (already captured in `examples/mcp-vs-cli/`)
- **Source Data:** Northstar QA environment — Angular + Auth0, 31 form fields, 51-option dropdown
- **Key Finding:** MCP ~3,075 tokens vs playwright-cli ~800–1,225 tokens for identical task

### Phase 2: Standalone Local Token Dashboard MVP
- **Status:** Implemented (MVP) — see `tokenbench/` package and `docs/phases/standalone-dashboard-mvp.md`
- **Description:** Build a local-first dashboard that reads Claude Code and Codex CLI subscription usage logs, normalizes token metadata, and gives feedback that helps the user become more token-efficient.
- **Key Deliverables:**
  - Local log discovery for Claude Code and Codex CLI
  - Provider parsers with correct per-message vs cumulative-token handling
  - SQLite-backed normalized usage schema
  - Local standalone dashboard with daily burn, provider/model split, project/session breakdowns, spikes, trends, and feedback cards
  - Privacy tests that prove prompts, responses, source code, and secrets are not persisted
- **Supersedes:** The previous "Token Measurement Toolkit" direction. Measurement utilities remain useful internally, but the product target is now a concrete dashboard rather than a general benchmark toolkit.

### Phase 3: Pattern Library
- **Status:** Implemented (MVP) — see `patterns/` docs and `tokenbench/patterns/` harness
- **Description:** Document generalizable token-efficiency patterns beyond browser automation. Each pattern backed by a reproducible measurement, not untested advice. The MVP ships one measured anchor scenario per family with a dependency-free, offline harness whose output generates the docs' measurement tables (so prose can't drift from the numbers). Run with `python -m tokenbench patterns`.
- **Delivered (MVP):**
  - Data Delivery: **Filtered Response** (measured)
  - Query: **Reference + Fetch** — the real MCP-vs-CLI snapshot-to-file case study (measured, 3.84×)
  - Agent Loop: **Snapshot Budget** (measured)
  - Harness + registry + `tokenbench patterns [--markdown] [--family]` CLI, with deterministic tests and a docs-in-sync guarantee
- **Future patterns (same measured template):**
  - Data Delivery: Inline All, Progressive Disclosure
  - Query: Targeted Eval, Full Scan, Incremental Scan
  - Agent Loop: Two-Phase Execution, Context Pruning, Parallel Fan-Out
  - Case studies: RAG chunking, API response shaping, multi-agent delegation, code search, DB queries

### Phase 4: Benchmarks
- **Status:** Implemented (MVP) — see `benchmarks/` and `tokenbench/bench/`
- **Description:** Standardized benchmarks for token efficiency across common AI application patterns. A living benchmark that tracks how tool/model updates change the numbers: the current results are committed to `benchmarks/results.json` and `tokenbench bench --check` fails if a fresh run diverges, so every change to the numbers is an intentional, reviewable diff. Run with `python -m tokenbench bench`.
- **Delivered (MVP):**
  - Standard task set across 5 categories (browser automation, API interaction, agent loop, code search, document analysis), each with ≥2 measured approaches
  - Generalized multi-approach benchmark cases built on the Phase 3 harness; the pattern registry is the single source for Phase 3-derived numbers (no duplication)
  - Committed, regenerable `benchmarks/results.json` (schema-versioned, deterministic) + `tokenbench bench [--json] [--check] [--category]` CLI
  - Determinism, coverage, bridge, and artifact-in-sync tests
- **Future:**
  - Historical time-series of results to chart drift across tool/model updates
  - Exact-tokenizer mode alongside the char-proxy
  - Published/exported benchmark results

## Core Principles

1. **Measure, don't guess** — Always real token counts, not estimates
2. **Show the tradeoff** — Token efficiency vs ergonomics vs latency
3. **Per-call matters at scale** — 500 tokens × 100 steps = 50K tokens
4. **Output tokens cost more** — 3-5x input token cost in most pricing models
5. **Context window is finite** — Bloated context degrades quality even if cost is acceptable
6. **Design for the worst case** — Complex pages, large responses, deep agent loops

## Decision Log
See `docs/decision_log.md`

## Getting Started
1. Use `/phase` to check current phase
2. Use `/plan create [phase]` to start planning
3. Use `/status` for project overview
