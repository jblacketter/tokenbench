# Decision Log

This log tracks important decisions made during the project.

<!-- Add new decisions at the top in reverse chronological order -->

---

## 2026-06-08: Burn drivers classified from project paths, not prompts

**Decision:** Implement a "burn drivers" view that groups token usage into work
families using a documented, ordered ruleset over the **project path only**
(`tokenbench/drivers.py`), never prompt/response/code content.

**Context:** Nate Jones' dashboard has a compelling "what's driving the burn?" view,
but he classifies from session prompts. tokenbench's whole privacy posture is that
prompts never reach storage, so we cannot (and will not) classify from content. The
question was whether a useful version is possible without prompts.

**Alternatives Considered:**
- Prompt/content-based classification (like Nate's): rejected outright — it would
  require storing or re-reading prompts, breaking the core privacy guarantee.
- Learned/embedding classification: too heavy and non-deterministic for an offline,
  dependency-free MVP.
- No drivers view at all: leaves a real gap; the path-based version is good enough to
  be useful (e.g. "Web & app 42%, QA/test 40%") while staying honest.

**Rationale:** Project paths are already stored and are a strong proxy for *what* the
work was. An ordered keyword ruleset (first match wins) with an explicit
`Other / mixed` fallback is deterministic, documented, and transparent (the view
shows evidence projects per family). A privacy test asserts the driver outputs never
surface planted secret strings. This keeps the differentiator: the same actionable
"what's driving the burn?" read as the prior art, with prompts never leaving the
machine.

**Decided By:** Human + Codex + Claude review

**Phase:** usage-drivers

**Follow-ups:**
- Let users extend/override the family ruleset via config.
- Optional log-scale toggle on the trend (moving-average overlay shipped).

---

## 2026-06-08: Richer views over existing data; calendar heatmap on documented log bins

**Decision:** Add a calendar burn heatmap, a per-provider receipts table, and Fermi
"scale equivalents" as new reads over the aggregates we already store — no new data,
no prompts, no privacy impact. The heatmap colors days by a **documented, stable
log-scale level** (decade thresholds), and all windowed views accept a caller-supplied
`today` anchor for determinism.

**Context:** Reviewing Nate Jones' published dashboard ("one tidy table, five honest
reads") and prior art (tokscale's contribution graph) surfaced high-value views we
lacked. The goal was the visually-recognizable, shareable reads — without touching the
privacy boundary or adding providers.

**Alternatives Considered:**
- Quantile/relative heatmap bins: adapt better to small datasets but aren't stable
  over time or comparable across users; rejected in favor of fixed decade bins that
  are documented and reproducible.
- Wall-clock anchoring for windows: rejected for analytics/tests — windows take an
  explicit `today` so results are deterministic (the dashboard passes the latest day).
- A live cost/eco calculator: out of scope and dishonest at this precision; the Fermi
  equivalents carry an explicit "scale translations, not real accounting" caveat.

**Rationale:** Everything is derived from `tokens_by_day` / `daily_by_provider`, so it
stays offline, dependency-free, and privacy-neutral. Fixed log decades make the
heatmap legend meaningful and stable. Semantic "burn drivers" classification (Nate's
editorial view) is deferred to the `usage-drivers` phase, where it will be done from
**project paths** rather than prompts to preserve the privacy posture.

**Decided By:** Human + Codex + Claude review

**Phase:** richer-views

**Follow-ups:**
- `usage-drivers`: path-based work-family classification, spike-day driver labels, and
  a moving-average + log-scale trend refinement.

---

## 2026-06-08: Limit proximity from logs (Codex) + labeled estimate (Claude)

**Decision:** Add limit-proximity awareness by ingesting Codex `rate_limits` from
local logs into a dedicated `rate_limit_snapshots` table, and representing the Claude
side as a configurable-budget + burn-rate **estimate** (never a fabricated hard
limit). Read rate-limit data independently of usage-event emission.

**Context:** Users want to know how close they are to provider limits. Verified that
Codex rollouts carry `payload.rate_limits` (5-hour + weekly windows, `used_percent`,
`resets_at`, `plan_type`) while Claude Code logs carry **no** quota/limit fields at
all. Prior art (ccusage, tokscale, CodexBar, codex-usage-tracker) confirmed both the
value of window/reset displays and tokenbench's aggregate-only privacy posture.

**Alternatives Considered:**
- Derive Codex limits from emitted usage events: rejected — the Codex usage parser
  skips no-op cumulative rows, and `rate_limits` can ride on exactly those rows, so
  the latest limit state could be silently dropped. Read it directly from
  `token_count` rows instead.
- Show a fabricated Claude limit number: rejected — there is no source data; a
  made-up percentage would be misleading. Use an explicit, labeled estimate that is
  blank until the user configures a budget.
- Live account-API limit scraping: rejected — out of scope and breaks the local-only,
  offline, privacy-first posture.

**Rationale:** Reading `rate_limits` directly is both correct (no-op-row safe) and
cheap. Keeping Claude as a clearly-labeled estimate is honest. The new table stores
only numbers/enums, and the privacy regression test was extended to scan it. An
optional **API-equivalent value** figure uses a static, offline pricing table and is
explicitly framed as metered-API cost, not subscription cost.

**Decided By:** Human + Codex + Claude review

**Phase:** actionable-insights

**Follow-ups:**
- A project-scoped, pip-installable per-project dashboard (recorded as a roadmap
  goal; feasibility assessed in `docs/roadmap.md`).
- Let users persist a `ClaudeBudget` (and pricing overrides) via config rather than
  code.

---

## 2026-06-07: Benchmarks = a committed, regenerable results artifact with a sync guard

**Decision:** Implement Phase 4 as a multi-approach benchmark suite
(`tokenbench/bench/`) whose canonical results are committed to
`benchmarks/results.json`, with `tokenbench bench --check` (and a test) failing if a
fresh run diverges from the committed file.

**Context:** The roadmap calls for a *living* benchmark that "tracks how tool/model
updates change the numbers." For that to be meaningful, a change in the numbers must
be visible and intentional, not silent. The reviewer (codex) asked specifically to
keep JSON sorted/stable, include `schema_version` and `chars_per_token`, and route
all Phase 3-derived numbers through the pattern→benchmark bridge.

**Alternatives Considered:**
- Recompute-only (no committed artifact): nothing to diff against, so drift is
  invisible — defeats the "living benchmark" goal.
- A test that hard-codes expected numbers: brittle and scattered; a single canonical
  artifact is one obvious place to review changes.
- Re-measuring pattern numbers inside the bench module: would duplicate the Phase 3
  source of truth and let the two phases disagree.

**Rationale:** A committed, schema-versioned, deterministically-sorted artifact makes
every numbers change a reviewable `git diff` on one file. The pattern registry stays
the sole source for Phase 3 numbers via `cases._from_scenario`, so patterns and
benchmarks can't diverge. Everything is offline and dependency-free (char-proxy plus
real measured overrides), consistent with Phases 2–3. This closes the Phase 3
follow-up to share one measurement source between the pattern library and benchmarks.

**Decided By:** Human + Codex + Claude review

**Phase:** benchmarks

**Follow-ups:**
- Add a historical time-series of `results.json` snapshots to chart drift over time.
- Offer an exact-tokenizer mode alongside the character proxy.

---

## 2026-06-07: Pattern Library = measured docs generated from a code source-of-truth

**Decision:** Implement Phase 3 as a `patterns/` documentation tree whose
"Token impact" tables are **generated by a code harness** (`tokenbench/patterns/`),
not hand-written. Each pattern is anchored by one reproducible, offline scenario.

**Context:** The roadmap calls for patterns "backed by measurements from a real case
study." The risk with hand-written numbers is drift: prose and tables fall out of
sync as code/data change. The reviewer (codex) explicitly asked that the measurement
source of truth stay machine-readable or harness-generated.

**Alternatives Considered:**
- Hand-written measurement tables: simplest, but drifts and can't be re-verified.
- Live model/tokenizer calls per build: most accurate, but adds dependencies and
  non-determinism, and the library cares about *ratios*, not absolute counts.
- A separate data file (CSV/JSON) read by docs: better than hand-writing, but still a
  second source to keep in sync with the prose.

**Rationale:** Scenarios live in `scenarios.py`; `docgen.sync_all()` writes the
measurement block into each doc between `<!-- BEGIN/END GENERATED -->` markers, and
`docgen.check_all()` (asserted in `tests/test_patterns.py`) fails CI if any doc
drifts. Token counts use the established ~4-chars/token proxy (see 2026-02-10) for
fixture-based scenarios, with explicit real overrides for captured data (the
browser-automation Query measurement). Everything is offline, deterministic, and
dependency-free, matching the dashboard MVP's posture.

**Decided By:** Human + Codex + Claude review

**Phase:** pattern-library

**Follow-ups:**
- Add the remaining named patterns (Progressive Disclosure, Targeted Eval, Context
  Pruning, etc.) using the same measured template.
- Feed Phase 3 (Benchmarks) from the same scenario registry so benchmarks and the
  pattern library share one measurement source.

---

## 2026-06-07: Pivot Phase 2 to a Standalone Local Token Dashboard

**Decision:** Replace the broad Phase 2 "Token Measurement Toolkit" with a standalone local dashboard MVP for Claude Code and Codex CLI subscription usage.

**Context:** The project began as a browser-automation investigation into how tool-output delivery (inline snapshots vs reference-and-fetch) affects token cost. That research remains useful, but continued development should produce a practical tool: a visual dashboard that helps the user understand Claude and Codex token usage and improve AI work habits. Public references such as Nate Jones' token-burn dashboard reinforce that token counts are most useful as behavioral traces tied to outcomes, not as leaderboards or raw cost charts.

**Alternatives Considered:**
- Continue with a generic toolkit: Useful for future benchmarks, but too abstract for the user's current need.
- Build project-embedded API-token dashboards first: Important later, but it solves a different problem from subscription-account usage.
- Use a hosted dashboard: Easier for cross-device sync, but creates privacy and trust issues because local AI logs can contain prompts, responses, code, and secrets.

**Rationale:** A local-first dashboard gives immediate value while preserving the original token-efficiency mission. Claude Code and Codex CLI both expose local usage data, so the MVP can avoid API billing integrations and focus on parsers, privacy, normalization, and actionable feedback.

**Decided By:** Human + Codex + Claude review

**Phase:** standalone-dashboard-mvp

**Follow-ups:**
- Implement provider-specific parser rules for Claude per-message usage and Codex cumulative usage. *(Done — see `tokenbench/parsers.py`.)*
- Add privacy regression tests that verify prompt/response/code text is not stored. *(Done — see `tests/test_privacy.py`, which scans both queried rows and raw DB bytes for deliberately-planted secrets.)*
- The earlier browser-automation research and demo content has since been split out
  into a separate project; tokenbench retains only the derived measurement numbers
  used by the pattern library and benchmarks.

**Implementation note (2026-06-07):** The reviewer's discovery-spike sample for Codex was slightly idealized. On the real machine, `total_token_usage` is nested under `payload.info.total_token_usage` in `token_count` event rows, and `session_id`/`cwd`/`model` come from a `session_meta` header record rather than per row. The plan's deferred "where does Codex record cwd?" question resolved to `session_meta.payload.cwd` (with an `unknown` fallback retained). Parser and fixtures were updated to mirror the real on-disk shape; a full local ingest produced 67k+ events across both providers with no secrets reaching SQLite.

---

## 2026-02-10: Measure Characters as Token Proxy

**Decision:** Use ~4 characters per token as the standard approximation for mixed English/code text.

**Context:** Need a consistent way to estimate tokens from tool output without access to a tokenizer in every context.

**Alternatives Considered:**
- Exact tiktoken counts: More accurate but requires Python tooling and specific model tokenizer
- Word-based estimates (~1.3 tokens/word): Less accurate for code-heavy output
- Character-based (~4 chars/token): Good balance of accuracy and simplicity

**Rationale:** Industry-standard approximation. Close enough for comparison purposes (we care about ratios, not exact counts). Can upgrade to an exact tokenizer later. Still in use by the pattern library and benchmark harness.

**Decided By:** Claude (technical recommendation)

**Phase:** Phase 1

**Follow-ups:**
- Phase 2 toolkit should include exact tokenizer support
- Note approximation method in all published measurements
