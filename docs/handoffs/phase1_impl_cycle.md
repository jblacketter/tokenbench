# Phase 1 Implementation Review Cycle

**Phase:** phase1
**Type:** impl
**Date:** 2026-02-12
**Lead:** codex
**Reviewer:** claude

**Plan file:** `docs/phases/phase1.md`
**Implementation files:** `scripts/fixtures/demo-form.html`, `scripts/mcp-demo.py`, `scripts/cli-demo.py`, `scripts/README.md`, `content/article.md`, `content/video-script.md`, `content/assets/architecture-mcp-vs-cli.svg`, `content/assets/token-breakdown.svg`, `content/assets/inline-vs-on-demand.svg`, `content/assets/comparison-table.md`

---

## Round 1

### Lead

**Action:** SUBMIT_FOR_REVIEW

Submitting Phase 1 implementation artifacts for review.

Implemented in this round:

1. **Reproducible demo target**
   - Added local fixture: `scripts/fixtures/demo-form.html`
   - Includes 24 `data-testid` attributes and a 51-option state dropdown as planned
2. **Demo scripts**
   - Added `scripts/mcp-demo.py` (MCP-style inline response simulation)
   - Added `scripts/cli-demo.py` (CLI-style on-demand response simulation)
   - Both scripts:
     - output identical sorted JSON arrays to stdout
     - print per-step character/token estimates to stderr
     - use local fixture only (no external services)
3. **Documentation and tracking alignment**
   - Updated `docs/phases/phase1.md` file status table for implemented artifacts
   - Added safe-language/source guidance earlier to reduce content-filter interruptions
4. **Content and assets**
   - Updated draft content language in `content/article.md` and `content/video-script.md`
   - Added visual assets:
     - `content/assets/architecture-mcp-vs-cli.svg`
     - `content/assets/token-breakdown.svg`
     - `content/assets/inline-vs-on-demand.svg`
     - `content/assets/comparison-table.md`

Validation run:
- `python -m py_compile scripts/mcp-demo.py scripts/cli-demo.py` (pass)
- SVG parse check for all `content/assets/*.svg` (pass)
- Fixture check for `data-testid` count (24) (pass)
- Full script execution could not be run in this environment because Playwright is not installed.

Please review for correctness, reproducibility, and alignment with phase scope.

### Reviewer

**Action:** REQUEST_CHANGES

Good implementation overall. The fixture is well-crafted, scripts are clean, article reads well, SVGs are clear, and the content-safe brief was a smart addition. A few issues before I can approve:

**Blocking:**

1. **MCP demo doesn't actually simulate MCP behavior faithfully.** `mcp-demo.py` uses `page.content()` (raw HTML) as the "inline snapshot" but the real MCP server returns an accessibility tree (YAML). This matters because the article's core argument is about accessibility tree verbosity, not raw HTML size. The token counts from this script won't match the ~3,075 from the article. Either:
   - (a) Generate an accessibility-tree-like YAML structure from the page (preferred — more honest to the claim), or
   - (b) Add a clear disclaimer in the script and README that this is a *simulation* showing the relative pattern, not exact reproduction of MCP output.

2. **CLI demo is missing the "snapshot to file" step for the form page.** The real CLI workflow in `comparison-data.md` does a `goto` to the form page which writes a snapshot file. `cli-demo.py` does `goto` but only writes a snapshot for the first navigation, not the second. Add a second snapshot write after the form page `goto` to match the documented workflow.

3. **`data-testid` count mismatch in the fixture.** The comparison data and article both say **24** testid attributes. I count 24 in the HTML fixture, which is correct. But `mcp-demo.py:81` runs a count query and `cli-demo.py:84` does the same — please add an assertion in each script (`assert count == 24`) so the acceptance criteria is self-verifying, not just via the external diff.

**Non-blocking suggestions:**

4. The article still references "31 form fields" in the setup section (`content/article.md:25`) but the fixture has fewer actual `<input>`/`<select>` elements (13 customer + 6 vehicle + 2 selects = ~21 form elements). Consider either adding more fields to the fixture or adjusting the article text to say "24 data-testid attributes across multiple form sections" instead of "31 form fields."

5. The SVG bar chart (`token-breakdown.svg`) y-axis goes to 3000 but the MCP total is 3,075. The MCP bar top is at y=150 which maps to ~3000 on the scale. Minor visual inaccuracy — consider adjusting the axis to 3200.

---

## Round 2

### Lead

**Action:** SUBMIT_FOR_REVIEW

Addressed all blocking items and both non-blocking suggestions:

1. **MCP snapshot fidelity / simulation clarity**
   - Updated `scripts/mcp-demo.py` to generate and embed a **YAML-like accessibility-tree snapshot** (`snapshot_yaml`) instead of raw HTML.
   - Added explicit simulation labeling in script output and payload metadata.
   - Updated `scripts/README.md` with an **Accuracy Note** clarifying this is a simulation of inline behavior, not a byte-for-byte `@playwright/mcp` run.

2. **CLI second snapshot-to-file step**
   - Updated `scripts/cli-demo.py` to perform two `goto` steps (`goto(initial)` and `goto(form)`), each writing its own snapshot file (`step-01` and `step-02`) before eval queries.

3. **Self-verifying count assertions**
   - Added `assert count == 24` in both scripts:
     - `scripts/mcp-demo.py`
     - `scripts/cli-demo.py`
   - This makes acceptance criteria explicit in-script, not only via external diff checks.

4. **Article fixture wording alignment (non-blocking)**
   - Updated `content/article.md` wording from "31 form fields" to "24 data-testid attributes across multiple form sections" to match the local fixture.

5. **Bar chart scale correction (non-blocking)**
   - Updated `content/assets/token-breakdown.svg` y-axis max to **3200** and adjusted MCP bar geometry accordingly.

Validation rerun:
- `python -m py_compile scripts/mcp-demo.py scripts/cli-demo.py` (pass)
- SVG parse check for `content/assets/token-breakdown.svg` (pass)
- Full runtime execution still requires Playwright installation in environment.

### Reviewer

**Action:** APPROVE

All 5 items from Round 1 verified:

1. **MCP snapshot fidelity** — `mcp-demo.py` now generates a YAML-like accessibility tree via `build_accessibility_yaml()` including element refs, names, aria labels, and expanded select options. Docstring and stderr output clearly label it as a simulation. Good.
2. **CLI second snapshot** — `cli-demo.py` now has two `goto` steps (`goto(initial)` and `goto(form)`), each writing a separate snapshot file. Matches the documented workflow.
3. **Self-verifying assertions** — Both scripts have `assert count == EXPECTED_TESTID_COUNT` with `EXPECTED_TESTID_COUNT = 24`. Clean.
4. **Article wording** — "31 form fields" replaced with "24 data-testid attributes across multiple form sections" at `content/article.md:25`. Matches fixture.
5. **SVG axis** — `token-breakdown.svg` y-axis max is now 3200 (line 16), MCP bar geometry adjusted. Accurate.

README accuracy note at `scripts/README.md:42-46` is clear and honest about the simulation vs production distinction.

Implementation approved.

---

<!-- CYCLE_STATUS -->
```
READY_FOR: lead
ROUND: 2
STATE: approved
```
