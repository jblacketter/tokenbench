# Phase 1: MCP Server vs Playwright CLI Case Study

## Summary

Publish an article and companion video demonstrating how the same browser automation task consumes 2.5x-3.8x more tokens via MCP Server compared to a CLI approach. Uses real measurements from a production QA workflow to establish concrete evidence, then generalizes to broader token-efficiency principles for any AI application making tool calls.

## Scope

### In Scope
- Article (~2,000 words): "Your AI Agent Is Using 3x More Tokens Than It Needs To"
- Companion video walkthrough showing both approaches side-by-side
- Comparison tables and architecture diagrams
- Reproducible example scripts (MCP and playwright-cli versions)
- General principles section (inline vs on-demand data delivery)
- Practical recommendations for tool builders and agent developers

### Out of Scope
- Token measurement toolkit (Phase 2)
- Pattern library beyond this case study (Phase 3)
- Benchmarking framework (Phase 4)
- Exact tokenizer counts (using ~4 chars/token approximation per decision log)

### Token Approximation Caveat
All token counts in this phase use the ~4 characters per token approximation for mixed English/code text (see `docs/decision_log.md`). Published content must include an explicit disclaimer: "Token counts are estimates based on ~4 chars/token. Exact counts vary by model and tokenizer." Phase 2 will introduce exact tokenizer tooling.

## Technical Approach

### Content Production
1. **Article** — Write based on existing outline (`docs/article-outline.md`), using `docs/content-safe-brief.md` as the primary source and `examples/mcp-vs-cli/comparison-data.md` for numeric verification
2. **Visual assets** — Architecture diagrams (MCP flow vs CLI flow), token breakdown bar chart, comparison table, inline vs on-demand pattern diagram
3. **Video** — Screen recording of both approaches running the same task, with token counter overlay
4. **Example scripts** — Reproducible Playwright scripts for both MCP and CLI approaches against a public-facing demo target (not the production Northstar app)

### Reproducible Demo
- **Primary target:** Self-contained local HTML fixture at `scripts/fixtures/demo-form.html` — a static page mimicking the Northstar form structure (form fields with `data-testid` attributes, a multi-option `<select>` dropdown, and a modal). No server or auth required.
- **Fallback:** The fixture is checked into the repo, so it cannot become unavailable or change unexpectedly. No external dependency.
- Scripts in `scripts/` directory with clear README
- Both demo scripts operate against the local fixture via `file://` or a local `python -m http.server`

### Reproducibility Acceptance Criteria
Both scripts must produce identical output: a sorted JSON array of `data-testid` attribute values found on the page.

**Verification commands:**
```bash
# Run MCP demo, capture output
python scripts/mcp-demo.py > /tmp/mcp-output.json

# Run CLI demo, capture output
python scripts/cli-demo.py > /tmp/cli-output.json

# Compare — must be identical
diff /tmp/mcp-output.json /tmp/cli-output.json
# Expected: no output (files are identical)

# Validate format — sorted JSON array of strings
python -c "import json, sys; d=json.load(open(sys.argv[1])); assert isinstance(d, list) and all(isinstance(s, str) for s in d) and d == sorted(d)" /tmp/mcp-output.json
```

Each script also prints a token usage summary to stderr (character counts per step, estimated tokens at ~4 chars/token) so readers can see the cost difference directly.

## Files

| File | Purpose | Status |
|------|---------|--------|
| `docs/article-outline.md` | Full article outline with section breakdowns | Done |
| `docs/content-safe-brief.md` | Sanitized drafting brief to reduce filter-trigger wording | Done |
| `examples/mcp-vs-cli/comparison-data.md` | Raw measurements from Northstar QA experiment | Done |
| `docs/decision_log.md` | Architecture decisions | Done |
| `docs/roadmap.md` | Project roadmap | Done |
| `scripts/fixtures/demo-form.html` | Local HTML fixture mimicking Northstar form | Done |
| `scripts/mcp-demo.py` | MCP Server version of the demo | Done |
| `scripts/cli-demo.py` | playwright-cli version of the demo | Done |
| `scripts/README.md` | How to run the demos + verification commands | Done |
| `content/article.md` | Final article draft in markdown | Draft Complete |
| `content/video-script.md` | Video script and recording notes | Draft Complete |
| `content/assets/` | Architecture diagrams, bar charts, comparison tables (PNG/SVG) | Draft Complete |

## Success Criteria

1. Article is published and clearly demonstrates the 2.5x-3.8x token cost difference with real numbers
2. Readers can reproduce the comparison using provided scripts
3. General principles (inline vs on-demand) are clearly articulated beyond just the browser automation case
4. Practical recommendations are actionable for both tool builders and agent developers
5. Video walkthrough makes the comparison visually compelling
