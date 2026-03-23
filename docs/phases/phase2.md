# Phase 2: Token Measurement Toolkit

## Summary

Build a reusable measurement toolkit that records token usage per step and compares multiple approaches for the same task. This phase converts the current case-study workflow into repeatable measurement infrastructure so future case studies can use exact, auditable numbers.

## Scope

### In Scope
- Token counter utility for input/output accounting per step
- Comparison harness that runs the same task with two approaches and reports deltas
- Per-step and aggregate token breakdown reports (machine-readable + markdown)
- Character-to-token conversion utilities, including exact tokenizer support where available
- Documentation for running measurements and interpreting outputs

### Out of Scope
- Full benchmark suite across all planned domains (Phase 4)
- Broad pattern-library authoring and multi-case-study synthesis (Phase 3)
- Video/content publishing work from Phase 1
- Advanced UI dashboarding beyond lightweight report artifacts

## Technical Approach

1. **Measurement primitives**
   - Implement a core token accounting module to track:
     - input chars/tokens
     - output chars/tokens
     - per-step totals and run totals
   - Provide two counting modes:
     - exact tokenizer mode (when tokenizer is available for a target model)
     - approximation mode (configurable chars/token fallback)

2. **Comparison harness**
   - Standardize run outputs for both sides of a comparison:
     - metadata (task, approach, environment, timestamp)
     - step-level records
     - totals and ratio summaries
   - Ensure both approaches can be compared from a single report command.

3. **Reporting**
   - Emit JSON artifacts for automation and reproducibility.
   - Emit markdown summaries for article-ready tables.
   - Add a small CLI entrypoint to generate a side-by-side report from run files.

4. **Validation**
   - Unit-test deterministic parts of token counting and report generation.
   - Validate harness output schema and ratio calculations.

## Files

| File | Purpose | Status |
|------|---------|--------|
| `scripts/token_counter.py` | Core token accounting and counting modes | Not Started |
| `scripts/comparison_harness.py` | Runs/compares two approaches for one task | Not Started |
| `scripts/token_report.py` | Generates JSON + markdown summaries | Not Started |
| `scripts/README.md` | Extend with Phase 2 toolkit usage docs | Not Started |
| `data/measurements/` | Stored run artifacts (JSON) | Not Started |
| `docs/token-toolkit.md` | Toolkit design and usage reference | Not Started |

## Success Criteria

1. Toolkit can record per-step input/output token counts for a run.
2. Toolkit can compare two run artifacts and compute total/ratio deltas.
3. Report output includes both JSON and markdown summaries suitable for publication workflows.
4. Counting mode is explicit in output (`exact` vs `approximate`) and approximation assumptions are recorded.
5. At least one end-to-end comparison run is documented with reproducible commands.

## Open Questions

- Which tokenizer backends should be supported in Phase 2 versus deferred?
- Should exact counting be required for approval, or is exact-when-available acceptable for this phase?

## Risks

- **Tokenizer mismatch risk:** Different models/tokenizers produce different counts.
  - **Mitigation:** Persist model/tokenizer metadata with every run and document interpretation rules.
- **Over-scoping risk:** Building dashboard/UI too early could delay core measurement infrastructure.
  - **Mitigation:** Restrict outputs to JSON + markdown in Phase 2.
