# Project-Scoped, Pip-Installable Dashboard

## Summary

Let tokenbench render a dashboard **scoped to a single project** — the token usage
for *this* repo — instead of only the machine-wide view across every Claude Code and
Codex session. The package is already pip-installable (it ships a `tokenbench`
console script via `pyproject.toml`), so a developer can `pip install` it into any
project today; the missing piece is a **project filter** that flows through analytics
and the dashboard so every view reflects just that project's burn.

The enabling fact: every stored event already carries a `project_path` (Claude
decodes it from the encoded `~/.claude/projects/<encoded-cwd>` dir; Codex takes it
from the session `cwd` in `session_meta`). Scoping is therefore a single, uniform
filter on `project_path` — no schema change, no re-ingest, no new parsing.

## Scope

In scope:
1. **Project-match primitive** — a documented helper that normalizes a target path
   and decides whether an event's `project_path` belongs to it (exact match, or the
   event path is nested under the target). Pure and deterministic.
2. **Scoped analytics** — `Analytics` (and `LimitAnalytics` where meaningful) accept
   an optional `project` filter; when set, **all** aggregates (summary, daily burn,
   splits, breakdowns, spikes, trend, heatmap, receipts, drivers, equivalents,
   feedback) reflect only the matching events. Default stays machine-wide — zero
   behavior change when the filter is absent.
3. **CLI surface** — a `--project [PATH]` flag on `serve`, `status`, and `limits`:
   - `--project` with no value → scope to the current working directory (the common
     "show me *this* project" case for a pip-installed dependency).
   - `--project /some/path` → scope to that path.
   - flag absent → machine-wide, exactly as today.
4. **Dashboard scope banner** — the page header states whether it is machine-wide or
   scoped to a project path, and (when scoped) how many of the machine's events/tokens
   that project represents, so the number is never silently mistaken for the whole.
5. **Honest scoping of account-wide data** — Codex `rate_limits` are an *account*
   signal, not per-project; in project scope the Limits section stays account-wide
   and is labeled as such (it is not filtered, because filtering it would misrepresent
   it). Same for any other account-level figure.
6. Surface the scope in the JSON API (`render_json`) so the scoped view is scriptable.

Out of scope:
- Per-project persisted config / a `tokenbench init` scaffold in the host repo
  (could come later; this phase is the filter + CLI, not project bootstrapping).
- Auto-detecting the project from git root vs cwd (cwd is the contract here; git-root
  detection can be a later refinement).
- Re-keying storage by project or a separate per-project DB — the machine-wide store
  is the source of truth and we filter reads; no write-path change.

## Technical Approach

1. **`tokenbench/scope.py`** (new): `normalize_project_path(path) -> str` and
   `event_in_project(event_path, target) -> bool` (exact match or `event_path`
   startswith `target + os.sep`). Documented best-effort semantics, mirroring the
   existing `decode_claude_project_dir` caveat about dash-ambiguous names.
2. **`analytics.py`**: `Analytics(store, project=None)` filters `self.rows` once in
   `__init__` (`[r for r in rows if event_in_project(r["project_path"], project)]`)
   so every downstream aggregate is scoped for free. A `project_scope` attribute
   records the active filter (or `None`). `LimitAnalytics`/`claude_budget_status`
   keep reading account-wide rows but the Claude burn-rate *estimate* can optionally
   reflect the scoped analytics where that is the honest reading.
3. **`dashboard.py`**: `render_html`/`render_json` accept and thread a `project`
   argument; add a scope banner near the top (machine-wide vs `Scoped to <path>` with
   the project's share of machine totals); `serve(...)` accepts `project`.
4. **`cli.py`**: add `--project` (nargs="?", const=<cwd sentinel>) to `serve`,
   `status`, `limits`; resolve the sentinel to `os.getcwd()`; pass the normalized
   path through. `ingest` stays machine-wide (we ingest everything once; scope is a
   read concern), with a one-line note in `--dry-run`/report output if helpful.
5. Everything stays offline, stdlib-only, and privacy-preserving — we are filtering
   the same whitelisted columns we already store; no new data is read or persisted.

## Files

Likely new or changed:
- `tokenbench/scope.py` — project-path normalize + match (new)
- `tokenbench/analytics.py` — optional `project` filter on `Analytics`; `project_scope`
- `tokenbench/dashboard.py` — scope banner + `project` arg through `render_html`/`render_json`/`serve`
- `tokenbench/cli.py` — `--project [PATH]` on `serve`/`status`/`limits`
- `tests/test_scope.py` — match semantics + scoped-vs-machine aggregates + empty/no-match safety
- `README.md` — "Per-project dashboard" usage (`cd your-project && tokenbench serve --project`)
- `docs/roadmap.md` — Phase 7 status → Implemented (MVP)
- `docs/decision_log.md` — record the read-filter (not re-key) decision and the
  account-wide-limits caveat

## Success Criteria

- Running `tokenbench serve --project` inside a project shows a dashboard scoped to
  that project's `project_path`, while the flag's absence is byte-for-byte the current
  machine-wide behavior.
- `--project /path` scopes to an explicit path; nested session paths under it are
  included; unrelated projects are excluded.
- Every aggregate view (summary, daily burn, splits, breakdowns, spikes, trend,
  heatmap, receipts, drivers, equivalents, feedback) reflects only the scoped events.
- The dashboard header clearly states the scope and, when scoped, the project's share
  of machine totals; account-wide Codex rate limits remain labeled account-wide rather
  than being silently filtered.
- The JSON API exposes the active scope.
- A no-match project yields a clean empty state (not an error); machine-wide remains
  the default. Privacy posture unchanged; offline and dependency-free; the full test
  suite plus the bench/pattern sync guards pass.
