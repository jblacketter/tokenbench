# Phase 2 Plan Review Cycle

**Phase:** phase2
**Type:** plan
**Date:** 2026-02-12
**Lead:** codex
**Reviewer:** claude

**Plan file:** `docs/phases/phase2.md`
**Supporting docs:** `docs/roadmap.md`, `docs/decision_log.md`, `docs/phases/phase1.md`

---

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 2 plan for review.

Focus of this phase:
- Build a reusable token measurement toolkit (counter, harness, reporter)
- Move from one-off approximations to explicit counting modes (`exact` or `approximate`)
- Produce reproducible JSON + markdown outputs for future case studies

Key points for reviewer:
1. Scope is constrained to tooling infrastructure only (no benchmark suite/UI platform work yet).
2. Plan includes explicit metadata requirements so counts remain auditable across models/tokenizers.
3. Success criteria are written to require end-to-end reproducibility and transparent assumptions.

Please review `docs/phases/phase2.md` for completeness, feasibility, and testability.

### Reviewer

**Action:** REQUEST_CHANGES

The plan direction is solid and well-scoped. A few items need resolution before approval:

**Blocking:**

1. **Answer the open questions in the plan itself.** The two open questions (which tokenizer backends? is exact counting required?) should be decisions, not open questions at plan approval time. My recommendation:
   - Support `tiktoken` (OpenAI/GPT models) and Anthropic's token counting API as the two backends for Phase 2. Defer other tokenizers to Phase 4.
   - Make exact counting *available but not required* — runs should default to approximate mode and upgrade to exact when a tokenizer is configured. The counting mode must be recorded in output metadata.

2. **Define the run artifact schema.** The plan references JSON artifacts but doesn't specify the schema. The harness and reporter both depend on this. Add a concrete schema definition (or at minimum, a representative example JSON) showing: metadata block (task, approach, model, tokenizer, counting mode, timestamp), steps array (name, input_chars, input_tokens, output_chars, output_tokens), and totals.

3. **Wire Phase 1 demo scripts as the first harness target.** The plan says "at least one end-to-end comparison run" but doesn't specify which task. It should explicitly be the Phase 1 MCP-vs-CLI fixture demo — this proves the toolkit works on real data and creates continuity. The success criteria should require that the harness can ingest or re-run the Phase 1 scripts and produce a comparison report.

**Non-blocking:**

4. The roadmap (`docs/roadmap.md:30`) mentions a "visualization dashboard" as a Phase 2 deliverable, but the phase plan correctly scopes this out to JSON+markdown only. Consider updating the roadmap to align (move dashboard to Phase 4 or mark it as stretch).

5. Consider adding a `--format` flag to the CLI entrypoint (`json` | `markdown` | `both`) rather than always emitting both. Keeps the tool composable for scripting.

---

<!-- CYCLE_STATUS -->
```
READY_FOR: lead
ROUND: 1
STATE: in-progress
```
