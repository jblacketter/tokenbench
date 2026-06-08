# Standalone Dashboard MVP

## Summary

Build the first real TokenBench product surface: a local-first dashboard that reads Claude Code and Codex CLI subscription usage from local machine logs, normalizes token events, and gives practical feedback for becoming more token-efficient.

This phase pivots active development toward a standalone dashboard. Future phases can add project-embedded API-token dashboards.

## Scope

In scope:
- Define the local usage data model for Claude Code and Codex CLI.
- Implement source discovery for local subscription-account logs.
- Build provider parsers for Claude Code and Codex local usage artifacts.
- Store normalized usage events locally.
- Build a standalone dashboard with daily usage, provider/model mix, project/session breakdowns, and trend views.
- Add feedback cards that translate usage patterns into token-efficiency advice.
- Keep prompts, responses, source code, and secrets out of persisted analytics.

Out of scope:
- API billing integrations.
- Cloud sync, accounts, leaderboards, or hosted dashboards.
- Project-embedded dashboard mode.
- Team analytics.
- Exact live rate-limit monitoring unless the local logs already expose enough data without account scraping.

## Technical Approach

1. Focus the repo on the standalone dashboard product (earlier browser-automation research content has since moved to a separate project).
2. Treat this MVP as the successor to the old Phase 2 "Token Measurement Toolkit." The original toolkit idea is subsumed by a concrete product: local usage ingestion plus a dashboard and feedback loop.
3. Add a real application structure around ingestion, storage, analysis, and dashboard rendering.
4. Use Python, SQLite, and a lightweight local web dashboard for the MVP. The launch path should be a local command that scans usage logs, stores normalized metadata, and serves a localhost dashboard. This fits the current repo better than introducing a separate frontend stack before the parser and privacy model are proven.
5. Ingest the confirmed local subscription-account sources:
   - Claude Code: `~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl`
   - Codex: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`
   - Do not parse `~/.codex/history.jsonl` for token data; it has session metadata/text but no usage totals.
6. Normalize provider-specific logs into a common `usage_event` schema:
   - `id`
   - `provider`
   - `source`
   - `model`
   - `timestamp`
   - `project_path` or anonymized project label
   - `session_id`
   - `input_tokens`
   - `output_tokens`
   - `cache_read_tokens`
   - `cache_write_tokens`
   - `reasoning_output_tokens`
   - `total_tokens`
   - `metadata`
7. Use provider-specific normalization rules:
   - Claude Code records usage per message under `message.usage`. Sum per-message `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, and `output_tokens`.
   - Codex records `total_token_usage` as cumulative running totals per session. Do not sum raw Codex rows. For the MVP, compute per-turn deltas when possible and use the last row per session as the session-total fallback.
   - Map Codex `cached_input_tokens` to `cache_read_tokens`; leave `cache_write_tokens` null or zero when unavailable.
   - Preserve Codex `reasoning_output_tokens` separately so analysis can distinguish visible output from hidden reasoning budget.
8. Handle provider-asymmetric fields explicitly. Cache writes, reasoning tokens, model names, and project paths may be null depending on provider and log format.
9. Project attribution:
   - Claude Code project paths are recoverable from encoded project directories such as `-Users-jack-projects-foo` to `/Users/jack/projects/foo`.
   - Codex project/cwd availability must be verified from rollout records during implementation. If unavailable, use an anonymized label or `unknown`.
10. Store locally in SQLite. Persist only whitelisted metadata fields, not prompts, responses, source code, tool output, or secrets.
11. Include a dry-run ingestion mode that reports discovered providers, scanned paths, session count, date range, and absent-source messages without writing to SQLite.
12. Build feedback from observable patterns:
   - unusually large session spikes
   - repeated high-token continuations in one thread
   - low cache utilization where visible
   - model mix shifts
   - project hotspots
   - quiet stretches after prior heavy productive usage
13. Use Nate Jones' public framing as product inspiration: token counts should be a behavioral trace tied to outcomes, not a leaderboard or cost scoreboard.

### Redacted Source Shapes

Claude Code records usage per message:

```json
{
  "type": "assistant",
  "sessionId": "00000000-0000-0000-0000-000000000000",
  "timestamp": "2026-06-07T00:00:00.000Z",
  "message": {
    "model": "claude-opus-4",
    "usage": {
      "input_tokens": 1234,
      "cache_creation_input_tokens": 100,
      "cache_read_input_tokens": 2000,
      "output_tokens": 567
    },
    "content": "[redacted prompt/response content must not be stored]"
  }
}
```

Codex rollout records expose cumulative session usage:

```json
{
  "timestamp": "2026-06-07T00:00:00.000Z",
  "session_id": "00000000-0000-0000-0000-000000000000",
  "model": "gpt-5-codex",
  "total_token_usage": {
    "input_tokens": 1234,
    "cached_input_tokens": 500000,
    "output_tokens": 567,
    "reasoning_output_tokens": 89,
    "total_tokens": 501890
  },
  "items": "[redacted conversation/tool content must not be stored]"
}
```

## Files

Likely new or changed files:
- `README.md`
- `docs/roadmap.md`
- `docs/decision_log.md`
- `docs/phases/standalone-dashboard-mvp.md`
- Python package files for ingestion, storage, analytics, and local web dashboard serving
- tests for parser fixtures and analytics rules

> Historical note: the browser-automation research and demo content referenced in the
> original plan was later split out into a separate project. tokenbench retains only
> the derived measurement numbers used by the pattern library and benchmarks.

## Success Criteria

- The repo presents a clear standalone dashboard product direction.
- `docs/roadmap.md` states that the standalone dashboard MVP replaces/subsumes the previous Phase 2 toolkit direction.
- `docs/decision_log.md` records the pivot into a standalone local dashboard.
- A local ingestion command can discover and parse available Claude Code and Codex usage logs, or report clearly when they are absent.
- A dry-run mode reports discovered paths, provider availability, session counts, and date ranges without writing to SQLite.
- Parsed usage is normalized into one local schema.
- A standalone dashboard can be launched locally and shows at least:
  - total tokens by day
  - provider split
  - model split
  - project/session breakdown
  - recent spikes with available data
  - 30-day trend with available data
  - token-efficiency feedback cards
- The MVP has parser tests using fixtures that do not contain private prompts, responses, source code, or secrets.
- The MVP has a privacy regression test using fixtures that deliberately include prompt, response, code, and secret-looking strings, then asserts none of those strings reach SQLite.
- Documentation explains privacy boundaries and current limitations.
