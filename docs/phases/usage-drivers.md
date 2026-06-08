# Usage Drivers

## Summary

A **privacy-safe** take on Nate Jones' "burn drivers" view, plus a trend refinement.
Nate classifies token burn into work families from session *prompts*; tokenbench
never stores prompts, so we classify from **project paths** only. This phase groups
usage into work families by path, labels recent spike days with their dominant
project, and adds a moving-average (and optional log-scale) refinement to the daily
trend.

## Scope

In scope:
1. **Work-family classification (path-based)** — a documented, deterministic ruleset
   maps each `project_path` to a work family (e.g. test/QA automation, writing/docs,
   web/app, infra). A "Burn drivers" view shows families by tokens, share %, and
   evidence (top contributing projects). Falls back to "Other / mixed" (or the
   project basename) when no rule matches.
2. **Spike-day driver labels** — each recent spike day is labeled with its dominant
   project / work family (computed from per-day project totals).
3. **Trend refinement** — add a moving-average overlay to the daily trend and an
   optional log-scale y-axis option.
4. Surface all of the above in the dashboard and JSON API.

Out of scope:
- Any prompt/response/content-based classification (would break the privacy boundary).
- Learned/ML classification — heuristic path rules only.
- Persisted user-editable rule config (rules live in code with documented defaults;
  persistence can come later).

## Technical Approach

1. **`tokenbench/drivers.py`** (new): `WORK_FAMILY_RULES` — an ordered list of
   `(substring/predicate, family)` tested against the lowercased project path;
   `classify_project(path) -> family` with a documented default. Pure and
   deterministic.
2. **Analytics additions** (`analytics.py`):
   - `work_families()` → tokens per family with share % and top-N evidence projects.
   - `labeled_spikes(...)` → `recent_spikes` enriched with each day's dominant project
     and family (from per-day, per-project aggregation).
   - `moving_average(window)` helper + a trend variant that returns raw + smoothed
     series (and exposes values suitable for a log-scale axis).
3. **Dashboard**: a "Burn drivers" section (family bars with share + evidence), spike
   labels in the Recent spikes list, and a moving-average overlay on the trend SVG.
4. **JSON API**: add `work_families` and labeled spikes.
5. Path-only classification keeps the privacy posture intact; offline and
   dependency-free as everywhere else.

## Files

Likely new or changed:
- `tokenbench/drivers.py` — path-based work-family rules + classifier (new)
- `tokenbench/analytics.py` — `work_families`, `labeled_spikes`, moving average
- `tokenbench/dashboard.py` — burn-drivers section, spike labels, trend overlay
- `tests/test_drivers.py`
- `docs/phases/usage-drivers.md`, `docs/roadmap.md`, `docs/decision_log.md`, `README.md`

## Success Criteria

- Token burn is classified into work families using **project paths only** (never
  prompts/content), via documented, deterministic rules; the dashboard shows a
  Burn-drivers view with family, share %, and evidence (top projects).
- Recent spike days are labeled with their dominant project / work family.
- The daily trend gains a moving-average overlay (and/or a log-scale option).
- The JSON API exposes `work_families` and the labeled spikes.
- The privacy posture is unchanged (path-only); everything is offline and
  dependency-free; the full test suite and the bench/pattern sync guards pass.
