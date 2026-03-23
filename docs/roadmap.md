# TokenBench — Project Roadmap

## Overview

Exploring how to effectively build AI-powered applications with token efficiency in mind. Collects real-world measurements, patterns, and anti-patterns — starting with a browser automation case study and expanding to general principles.

**Tech Stack:** Python, Playwright, Claude Code, MCP

**Workflow:** Lead / Reviewer with Human Arbiter (see ai-handoff.yaml for agent configuration)

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

### Phase 2: Token Measurement Toolkit
- **Status:** Not Started
- **Description:** Build simple tools to measure and compare token usage across different approaches. Makes future case studies easier to produce with real numbers.
- **Key Deliverables:**
  - Token counter utility (wraps tool calls, logs input/output estimates)
  - Side-by-side comparison harness (same task, two approaches, diff token counts)
  - Visualization dashboard for token breakdown per step
  - Character → token conversion utilities (~4 chars/token English, ~3.5 for code)

### Phase 3: Pattern Library
- **Status:** Not Started
- **Description:** Document generalizable token-efficiency patterns beyond browser automation. Each pattern backed by measurements from a real case study.
- **Key Deliverables:**
  - Data Delivery Patterns (Inline All, Reference + Fetch, Progressive Disclosure, Filtered Response)
  - Query Patterns (Targeted Eval, Full Scan, Incremental Scan)
  - Agent Loop Patterns (Snapshot Budget, Two-Phase Execution, Context Pruning, Parallel Fan-Out)
  - Case studies: RAG chunking, API response shaping, multi-agent delegation, code search, DB queries

### Phase 4: Benchmarks
- **Status:** Not Started
- **Description:** Standardized benchmarks for token efficiency across common AI application patterns. Living benchmark that tracks how tool/model updates change the numbers.
- **Key Deliverables:**
  - Standard task set (browser automation, code search, API interaction, document analysis)
  - Multi-approach measurements per task
  - Published benchmark results

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
