# Article Outline: "Your AI Agent Is Using 3x More Tokens Than It Needs To"

Use `docs/content-safe-brief.md` as the primary drafting source.
Use `examples/mcp-vs-cli/comparison-data.md` only to verify exact numbers and step details.

**Format:** Article (Medium/blog) + companion video
**Audience:** Developers building AI-powered tools, especially those using MCP, browser automation, or multi-step agent workflows
**Length:** ~2,000 words + comparison tables + diagrams

---

## 1. Hook (200 words)

- Open with the punchline: same task, same browser, same result — but one approach used 3,075 tokens and the other used 800
- Frame the stakes: tokens = cost + latency + context window pressure
- "The difference isn't in what you're doing, it's in how your tools deliver data back to the LLM"

## 2. The Setup (300 words)

- Introduce the task: open the local fixture page, navigate to the form view, and list all `data-testid` attributes
- Real app: Angular + Auth0, 31 form fields, 51-option state dropdown, auto-opening modal
- Why this matters: this is a standard QA automation / DOM inspection task that AI agents do regularly
- Two approaches:
  - **@playwright/mcp** — Anthropic's official MCP server for browser automation
  - **playwright-cli** — CLI tool that wraps Playwright, invoked via shell commands

## 3. The Experiment (400 words)

### MCP Server Approach
- Walk through each step: navigate → fill form → click → navigate → wait → evaluate
- Show the inline snapshot from `browser_wait_for` — the full YAML accessibility tree
- Highlight: the 51-state dropdown, every form field, console events — all inline, every time
- **Total: ~3,075 tokens across 6 tool calls**

### playwright-cli Approach
- Walk through: open → goto → snapshot (file) → fill → click → goto → eval (count) → eval (list)
- Show the eval response: just a JSON array of 24 testid strings
- Highlight: snapshots written to files, only ~30 chars returned per step
- **Total: ~800–1,225 tokens across 7-8 tool calls**

### Side-by-side Table
- The comparison table with input/output/total tokens
- Call out: input tokens nearly identical, all the difference is output

## 4. Why MCP Is More Expensive (300 words)

- **Inline snapshots on every action** — navigate, click, wait all return full page tree
- **No opt-out** — you can't say "just click, don't give me the snapshot"
- **Console/event logs appended** — session metadata, API warnings, network events
- **Dropdown/table expansion** — 51 states × ~10 tokens each = 500 tokens per snapshot just for one `<select>`
- Show the math: 4-5 snapshots × ~1,200 tokens each = 4,800–6,000 tokens of overhead

## 5. When MCP Wins Anyway (200 words)

- **Interactive exploration** — agent needs to see the page to decide what to click next
- **Simple pages** — low element count, no large dropdowns/tables
- **Fewer tool calls** — `fill_form` handles multiple fields at once
- **No file management** — no need to read snapshot files separately
- The tradeoff: higher per-call cost, but sometimes fewer calls and simpler code

## 6. The General Principle (300 words)

- **Inline vs On-Demand data delivery** — this isn't just about Playwright
- Examples in other domains:
  - API responses: returning full nested objects vs references + fetch
  - Database queries: `SELECT *` vs `SELECT count(*)` first
  - File operations: `cat` entire file vs `grep` for what you need
  - Code search: full AST dump vs targeted regex
- The pattern: **return the minimum data needed for the next decision**
- When you're building tools for AI agents, think about what the LLM actually needs to see

## 7. Practical Recommendations (200 words)

**For tool builders:**
1. Support filtered/targeted responses — let the caller specify what they need
2. Offer a "quiet mode" — action confirmation without full state dump
3. Write verbose data to files — return a reference, let the agent read if needed
4. Separate concerns — don't bundle console logs with DOM snapshots

**For agent developers:**
1. Two-phase queries — count first, then list, then detail
2. Snapshot budgets — limit full snapshots to decision points
3. Targeted eval over full scan — JS `querySelector` beats accessibility tree for specific queries
4. Measure your token spend — you can't optimize what you don't measure

## 8. Closing (100 words)

- Token efficiency is the new performance optimization for AI applications
- Small per-call differences compound across agent workflows
- The best AI tools will be the ones that respect the context window
- Link to full comparison data and reproduction scripts

---

## Visual Assets Needed

1. **Architecture diagram**: MCP flow (tool call → inline snapshot → LLM) vs CLI flow (command → file ref → optional read → LLM)
2. **Token breakdown bar chart**: stacked bars showing per-step token cost for each approach
3. **Screenshot/recording**: actual MCP snapshot output showing the verbose YAML
4. **Screenshot/recording**: playwright-cli eval output showing the clean JSON result
5. **Comparison table**: formatted version of the results table
6. **General principle diagram**: inline vs on-demand data delivery pattern

## Video Script Notes

- Screen record both approaches live (or replay from saved sessions)
- Split screen: MCP on left, CLI on right, running the same steps
- Overlay token counters that increment with each step
- Pause on the big MCP snapshot to let viewers see the verbosity
- End with the general principle applied to other domains
