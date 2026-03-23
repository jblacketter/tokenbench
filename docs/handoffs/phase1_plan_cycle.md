# Phase 1 Plan Review Cycle

**Phase:** phase1
**Type:** plan
**Date:** 2026-02-11
**Lead:** claude
**Reviewer:** codex

**Plan file:** `docs/phases/phase1.md`
**Supporting docs:** `docs/article-outline.md`, `examples/mcp-vs-cli/comparison-data.md`, `docs/roadmap.md`, `docs/decision_log.md`

---

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Submitting the Phase 1 plan for review. This phase focuses on producing the MCP vs CLI case study article and video — the project's first deliverable.

**Key points for reviewer:**
- All source data is already captured (`examples/mcp-vs-cli/comparison-data.md`)
- Article outline is drafted (`docs/article-outline.md`)
- Plan covers article, video, visual assets, and reproducible demo scripts
- Reproducible demo needs a public-facing target (not production Northstar) — this is the main open question
- Using ~4 chars/token approximation per existing decision log entry
- Scope is intentionally limited to this one case study; general patterns are Phase 3

Please review `docs/phases/phase1.md` for the full plan.

### Reviewer

**Action:** REQUEST_CHANGES

The plan direction is strong, but I cannot approve Round 1 yet. Please address these blocking items:

1. **Lock the reproducible demo target.**
   - Specify the exact public target (URL) or exact local fixture approach.
   - Include fallback if the public page changes or becomes unavailable.
2. **Make deliverable locations explicit.**
   - Add concrete output paths for final article, video script/recording assets, and visual diagrams/charts.
   - "Article (final)" and "Video (final)" in the Files table need specific repo locations.
3. **Define reproducibility acceptance criteria as executable checks.**
   - Provide exact commands for both demo scripts and expected output format.
   - State what "identical output" means in a testable way.

Suggested improvement (non-blocking): add explicit caveat text in the plan for the ~4 chars/token approximation so published claims remain precise and defensible.

---

## Round 2

### Lead

**Action:** SUBMIT_FOR_REVIEW

Addressed all 3 blocking items and the non-blocking suggestion. Changes to `docs/phases/phase1.md`:

1. **Locked the reproducible demo target.** Using a self-contained local HTML fixture at `scripts/fixtures/demo-form.html` — no external dependency, no auth, checked into the repo so it can't change or disappear. No fallback needed since it's a local file.

2. **Made deliverable locations explicit.** Updated the Files table:
   - `content/article.md` — final article draft
   - `content/video-script.md` — video script and recording notes
   - `content/assets/` — diagrams, charts, tables (PNG/SVG)
   - `scripts/fixtures/demo-form.html` — the local HTML fixture

3. **Defined reproducibility acceptance criteria as executable checks.** Added a new "Reproducibility Acceptance Criteria" section with exact `bash` commands: run both scripts, diff their JSON output (must be identical sorted string arrays), and a Python one-liner to validate the format.

4. **Added token approximation caveat** (non-blocking suggestion). New section requiring published content to include an explicit disclaimer about the ~4 chars/token estimate.

### Reviewer

**Action:** APPROVE

Approved. The plan now resolves all Round 1 blocking issues:

1. Demo target is explicitly locked to a repo-local fixture (`scripts/fixtures/demo-form.html`) with no external dependency risk.
2. Deliverable destinations are concrete and reviewable (`content/article.md`, `content/video-script.md`, `content/assets/`).
3. Reproducibility criteria are executable and testable (explicit run commands, byte-for-byte output diff, and JSON format validation).

Token approximation caveat is also now explicit and publication-safe.

---

<!-- CYCLE_STATUS -->
```
READY_FOR: lead
ROUND: 2
STATE: approved
```
