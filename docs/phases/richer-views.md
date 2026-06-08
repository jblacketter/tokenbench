# Richer Views

## Summary

Add three new "honest reads" over the normalized daily data we already store —
a **calendar burn heatmap** (log-scale), **scale equivalents** (Fermi estimates), and
a **per-provider receipts table** (Today / 7d / 30d / Peak day / Active days / 30-day
sparkline). Inspired by Nate Jones' "one tidy table, five honest reads" framing and
tokscale's contribution graph. Every view is derived from existing aggregates, so
this phase does not touch the privacy boundary or add data sources.

## Scope

In scope:
1. **Calendar burn heatmap** — per-day total tokens across the available history,
   color-binned on a **log scale** (GitHub-contributions style), as inline SVG with a
   legend. Graceful empty/low-data state.
2. **Scale equivalents** — Fermi estimates translating total token burn into
   human-relatable quantities (e.g. water, electricity, lines-of-code/engineer-years)
   with documented basis constants, and Nate's honesty caveat ("scale translations,
   not measured utility, billing, or environmental accounting").
3. **Per-provider receipts table** — for each provider **and** the combined total:
   Today, Last 7 days, Last 30 days, Peak day (date + value), Active days, and a
   30-day sparkline.
4. Surface all three in the dashboard and the JSON API.

Out of scope (deferred to the `usage-drivers` phase):
- Work-family / semantic "burn drivers" classification.
- Moving-average + log-scale trend refinement of the existing line chart.
- Any new providers or data sources (no ChatGPT, no exports).

## Technical Approach

1. **Analytics additions** (`analytics.py`):
   - `daily_by_provider()` → per-day, per-provider totals (feeds sparklines + heatmap).
   - `provider_windows(now_epoch=None)` → per provider + total: `today`, `last_7d`,
     `last_30d`, `peak_day` (`{day, tokens}`), `active_days`, and a dense 30-day
     series for the sparkline. Reuses `provider_window_tokens` and `tokens_by_day`.
   - `heatmap(weeks=None)` → a dense day grid with a log-scale bin index per day for
     coloring.
2. **Scale equivalents** (`tokenbench/equivalents.py`, new): documented Fermi
   constants → a list of `{measure, estimate, equivalent, basis}`. Deterministic and
   offline; carries the explicit "not real accounting" caveat.
3. **Dashboard** (`dashboard.py`): a calendar-heatmap SVG (weeks × weekdays, log-binned
   color, legend), a receipts table, and a scale-equivalents section.
4. **JSON API**: add the new aggregates to `render_json`.
5. Offline, dependency-free, consistent with existing module style; low-data states
   everywhere.

## Files

Likely new or changed:
- `tokenbench/analytics.py` — `daily_by_provider`, `provider_windows`, `heatmap`
- `tokenbench/equivalents.py` — Fermi scale equivalents (new)
- `tokenbench/dashboard.py` — heatmap SVG, receipts table, equivalents section
- `tests/test_views.py`
- `docs/phases/richer-views.md`, `docs/roadmap.md`, `docs/decision_log.md`, `README.md`

## Success Criteria

- The dashboard renders a **calendar heatmap** of per-day totals on a log scale with a
  legend; empty/low-data input renders a clear empty state, not an error.
- A **scale-equivalents** section shows at least three Fermi translations, each with a
  documented basis and the explicit "scale translations, not real accounting" caveat;
  the figures are deterministic (asserted in tests).
- A **per-provider receipts table** shows Today / 7d / 30d / Peak day / Active days /
  30-day sparkline for each provider and the combined total.
- The JSON API exposes the new aggregates (`provider_windows`, `daily_by_provider`,
  scale equivalents).
- Everything is offline and dependency-free; the full test suite passes, and the
  existing bench/pattern sync guards stay green.
