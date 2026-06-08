# Actionable Insights

## Summary

Move the dashboard from *what happened* to *what to do about it*. This phase adds
limit-proximity awareness, richer data-driven efficiency feedback, and fixes the
Project Breakdown name truncation. It is informed by prior art (ccusage, tokscale,
CodexBar, codex-usage-tracker) and keeps tokenbench's offline, dependency-free,
privacy-first posture.

It also records — but does not build — a future goal: a project-scoped,
pip-installable dashboard.

## What the local logs actually expose (verified)

- **Codex** rollouts already carry limit data per `token_count` row, under
  `payload.rate_limits`: `primary` (5-hour window, `window_minutes: 300`) and
  `secondary` (weekly, `window_minutes: 10080`), each with `used_percent`,
  `resets_at` (epoch), plus `plan_type` (e.g. `plus`). → Codex limit proximity is
  directly readable.
- **Claude Code** logs contain **no** quota/limit/rate fields (verified by scanning
  records). → The Claude side must use a *configurable budget + rolling-window
  burn-rate estimate*, explicitly labeled as an estimate, not a hard limit.

## Prior art (learnings folded in)

- **ccusage** — daily/weekly/monthly/session reports, 5-hour billing-window tracking,
  burn rate + projection, offline pricing data, group-by-project. Learnings: burn
  rate/projection and an offline cost-equivalent are valuable and feasible.
- **tokscale** — multi-provider real-time subscription quota with reset times.
- **CodexBar** — per-provider session/weekly/monthly windows with reset countdowns.
- **codex-usage-tracker** — local-first, aggregate-only SQLite that deliberately
  stores no prompts/secrets. Direct validation of tokenbench's privacy model.

tokenbench's differentiation: dependency-free + privacy-first **and** integrated with
a measured pattern library and benchmark suite in one package.

## Scope

In scope:
1. **Fix Project Breakdown labels** — show the project *name* (basename) with the full
   path on hover; no mid-path truncation like `/Users/.../pr…`.
2. **Limit proximity panel**:
   - Codex: ingest `rate_limits` snapshots; show the latest 5-hour and weekly windows
     with `used_percent`, a reset countdown, and plan tier.
   - Claude: a configurable per-window token budget + rolling-window burn-rate
     estimate; if unconfigured, a clear "no native limit data — configure to enable"
     state.
3. **Richer efficiency feedback** — new data-driven cards: burn rate & projection to
   next reset, cache read/write efficiency, model-mix weighting, reasoning-heavy
   sessions. Each degrades gracefully on low data.
4. **(Optional/stretch) Cost-equivalent estimate** — an offline, configurable pricing
   table giving the API-equivalent dollar value of subscription usage, clearly framed
   as "what this would cost on metered API pricing," never a network call.
5. **Record the future goal** — add a roadmap entry for a project-scoped,
   pip-installable dashboard, with a feasibility note (below). Not built this phase.

Out of scope:
- Building the per-project / pip-embedded mode (recorded as a roadmap goal only).
- Any network calls (pricing and limits are local logs + static config only).
- Scraping Anthropic/OpenAI account APIs for live limits.

## Technical Approach

1. **Rate-limit ingestion (Codex).** Extend the Codex parse/ingest path to read
   `payload.rate_limits` from `token_count` rows into a new
   `rate_limit_snapshots` table: `provider, session_id, source, timestamp, window`
   (`primary_5h` | `secondary_weekly`), `used_percent, window_minutes, resets_at,
   plan_type`. Numbers/enums only — no raw content. The privacy regression test is
   extended to cover this table.
2. **Limit analytics.** "Current limit status" = the most recent snapshot per window
   (max timestamp) across all sessions, with the reset countdown derived from
   `resets_at` relative to a `now` passed in by the caller (normal code, so wall-clock
   is fine — only workflow scripts forbid `Date.now`).
3. **Claude budget estimate.** A small config (`tokenbench/limits.py` or JSON) for
   optional user-set per-window token budgets; compute used-vs-budget over the rolling
   window from `usage_events`. Always labeled an estimate.
4. **Efficiency cards.** Extend `feedback.py`: burn rate (tokens/hour over a recent
   window) + projection, cache efficiency, model-mix weighting, reasoning-token share.
   Advisory, low-data-safe.
5. **Cost-equivalent (optional).** Static, offline, configurable per-model pricing
   table; compute API-equivalent value. Offline only; clearly labeled.
6. **Dashboard.** New "Limits" section (Codex window progress bars + reset countdown +
   plan tier; Claude estimate or "configure to enable"); fix Project Breakdown to use
   the basename with a `title=` full path; optional cost-equivalent stat.
7. **Future-goal feasibility note (point 4).** A project-scoped, pip-installable
   dashboard is feasible: the package already ships a console script via
   `pyproject.toml`; scoping needs a `--project <path>` / cwd filter on discovery
   (Claude: match the encoded project dir to the path; Codex: filter by session cwd)
   plus an analytics filter. Deferred to its own phase.

## Files

Likely new or changed:
- `tokenbench/parsers.py` — extract `rate_limits`
- `tokenbench/schema.py` — `RateLimitSnapshot` + persisted-field whitelist
- `tokenbench/storage.py` — `rate_limit_snapshots` table
- `tokenbench/ingest.py` — persist snapshots
- `tokenbench/analytics.py` — limit status, burn rate
- `tokenbench/limits.py` — Claude budget config + (optional) pricing/model-weight tables
- `tokenbench/feedback.py` — new cards
- `tokenbench/dashboard.py` — Limits panel, project-name fix, optional cost stat
- `tokenbench/cli.py` — surface limits (flag or `limits` subcommand)
- `tests/test_limits.py`, additions to `tests/test_privacy.py` and fixtures (a Codex
  rollout fixture carrying `rate_limits`)
- `docs/roadmap.md` (future goal), `docs/decision_log.md`, `README.md`

## Success Criteria

- Codex `rate_limits` snapshots are ingested into a privacy-preserving table
  (numbers/enums only); the privacy regression test is extended to assert no raw
  content reaches it.
- The dashboard shows a **Limits** panel: Codex 5-hour + weekly windows with
  `used_percent`, a reset countdown, and plan tier; Claude shows a configurable-budget
  estimate or an explicit "no native limit data" state.
- **Project Breakdown shows the actual project name** (basename), full path on hover,
  with no mid-path truncation.
- At least three new data-driven efficiency cards (burn rate/projection, cache
  efficiency, model-mix), each with graceful low-data states.
- Any cost-equivalent figure is offline and clearly labeled as API-equivalent value,
  or is explicitly deferred.
- Prior-art learnings and tokenbench's differentiation are documented; the
  project-scoped, pip-installable dashboard is recorded as a roadmap goal with a
  feasibility note.
- Everything stays offline and dependency-free; the full test suite passes.
