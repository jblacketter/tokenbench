# Decision Log

This log tracks important decisions made during the project.

<!-- Add new decisions at the top in reverse chronological order -->

---

## 2026-02-10: Start with Browser Automation Case Study

**Decision:** Use the MCP Server vs playwright-cli comparison as the first case study and article topic.

**Context:** Needed a concrete, measurable example to anchor the project. The Northstar QA project provided real-world data from testing both approaches on the same task.

**Alternatives Considered:**
- RAG chunking comparison: Good topic but requires more setup to produce reproducible measurements
- API response shaping: Too abstract without a concrete app to test against
- General "token efficiency tips" article: Too broad, lacks the punch of real numbers

**Rationale:** Browser automation is relatable (many developers use Playwright/Selenium), MCP is timely (growing adoption), and we already have real measurements (3,075 vs 800 tokens). The specific-to-general arc makes for compelling content.

**Decided By:** Human + Claude (collaborative)

**Phase:** Phase 1

**Follow-ups:**
- Capture raw data in `examples/mcp-vs-cli/`
- Write article outline
- Build reproducible demo scripts

---

## 2026-02-10: Measure Characters as Token Proxy

**Decision:** Use ~4 characters per token as the standard approximation for mixed English/code text.

**Context:** Need a consistent way to estimate tokens from tool output without access to a tokenizer in every context.

**Alternatives Considered:**
- Exact tiktoken counts: More accurate but requires Python tooling and specific model tokenizer
- Word-based estimates (~1.3 tokens/word): Less accurate for code-heavy output
- Character-based (~4 chars/token): Good balance of accuracy and simplicity

**Rationale:** Industry-standard approximation. Close enough for comparison purposes (we care about ratios, not exact counts). Can upgrade to exact counts in Phase 2 toolkit.

**Decided By:** Claude (technical recommendation)

**Phase:** Phase 1

**Follow-ups:**
- Phase 2 toolkit should include exact tokenizer support
- Note approximation method in all published measurements
