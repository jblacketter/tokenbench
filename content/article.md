# Your AI Agent Is Using 3x More Tokens Than It Needs To

*Real measurements from a production workflow show how data delivery patterns make or break token efficiency.*

> **Note:** Token counts in this article are estimates based on ~4 characters per token, a standard approximation for mixed English/code text. Exact counts vary by model and tokenizer.

---

## The Punchline

Same task. Same browser. Same result. But one approach used **3,075 tokens** and the other used **800**.

The difference isn't in *what* you're doing — it's in *how your tools deliver data back to the LLM*.

If you're building AI-powered applications that make tool calls, this matters more than you think. Token usage directly maps to three things: **cost**, **latency**, and **context window pressure**. A 3x difference in token overhead per tool call becomes a 30x difference across a 10-step workflow. As AI agents get more autonomous — more tool calls, longer chains — token efficiency becomes a first-class engineering concern.

Here's what we found.

---

## The Setup

We needed to test a real QA automation task: open a local fixture page, navigate to a complex form view, and extract all `data-testid` attributes for test coverage analysis.

The target page has **24 data-testid attributes** across multiple form sections, a **51-option state dropdown**, and an auto-opening modal dialog. This isn't a toy example — it's a realistic workflow with real complexity.

We ran the same task two ways:

1. **@playwright/mcp** — Anthropic's MCP (Model Context Protocol) server for browser automation. The AI agent calls MCP tools like `browser_navigate`, `browser_click`, and `browser_evaluate`.

2. **playwright-cli** — A CLI wrapper around Playwright, invoked via shell commands. The agent runs commands like `goto`, `click`, `eval`, and reads results from stdout or files.

Both approaches completed the task successfully. Both found the same 24 `data-testid` attributes. The difference was entirely in how much data flowed through the context window to get there.

---

## The Experiment

### MCP Server: 6 Tool Calls, ~3,075 Tokens

| Step | Tool | Action | Output Tokens |
|------|------|--------|---------------|
| 1 | `browser_navigate` | Go to app URL | ~600 |
| 2 | `browser_fill_form` | Populate fixture fields | ~125 |
| 3 | `browser_click` | Click continue | ~250 |
| 4 | `browser_navigate` | Go to form page | ~200 |
| 5 | `browser_wait_for` | Wait for page load | **~1,200** |
| 6 | `browser_evaluate` | Query testid attributes | ~550 |
| | **Total** | | **~3,075** |

The killer is **Step 5**. The `browser_wait_for` call returned the **full accessibility tree** of the page — inline, in the tool response. Every form field with its label, role, and ref. All 51 state dropdown options (each ~10 tokens). Session metadata and warnings. Navigation metadata. One tool call, ~1,200 tokens of output.

And here's the thing: *this happens on every action*. Navigate? Full snapshot. Click? Full snapshot. Wait? Full snapshot. The agent didn't ask for this data — it's just how MCP delivers results.

### playwright-cli: 7-8 Tool Calls, ~800-1,225 Tokens

| Step | Command | Action | Output Tokens |
|------|---------|--------|---------------|
| 1 | `open` | Launch browser | ~60 |
| 2 | `goto` | Navigate to app | ~90 |
| 3 | `fill` / `click` | Populate fields + continue | ~115 |
| 4 | `goto` | Navigate to form page | ~90 |
| 5 | `eval` (count) | `querySelectorAll('[data-testid]').length` | ~60 |
| 6 | `eval` (list) | Get all testid values | ~210 |
| | **Total** | | **~800** |

The difference? Snapshots go to **files**, not inline. Every `goto` and `click` writes the accessibility tree to a `.yml` file and returns just the file path — about 30 characters. The agent *chooses* when to read that file into context.

And the `eval` command returns just the answer. Ask for a count? You get `24`. Ask for the list? You get a JSON array of 24 strings. No accessibility tree, no console logs, no dropdown options.

### The Numbers Side by Side

| Metric | MCP Server | playwright-cli |
|--------|-----------|----------------|
| Tool calls | 6 | 7-8 |
| Input tokens | ~150 | ~125 |
| Output tokens | ~2,925 | ~675 |
| **Total tokens** | **~3,075** | **~800** |
| **Ratio** | **3.8x** | **1x** |

Input tokens are nearly identical — the tool call parameters (URLs, element refs, JS expressions) are roughly the same size. **All of the cost difference is on the output side.**

---

## Why MCP Costs More

Four factors compound to create the 3x+ overhead:

**1. Inline snapshots on every action.** Navigate, click, wait — they all return the full page accessibility tree. There's no way to say "just click the button, I don't need to see the page."

**2. No opt-out.** The snapshot is baked into every tool response. You can't request a "quiet mode" that confirms the action without the state dump.

**3. Console and event logs.** Session metadata, API warnings, browser initialization messages, network events — all appended to every response.

**4. Element expansion.** That 51-option state dropdown? It appears in full in every snapshot:

```yaml
- combobox "State":
  - option "Select State" [selected]
  - option "Alabama"
  - option "Alaska"
  ... (51 total)
```

That's ~500 tokens per snapshot *just for one dropdown*. Multiply by the 4-5 snapshots in a typical workflow and you're looking at 2,000-2,500 tokens of dropdown options the agent never needed.

---

## When MCP Wins Anyway

This isn't a one-sided story. MCP has real advantages:

- **Interactive exploration.** When the agent needs to see the page to decide what to click next, inline snapshots mean fewer round-trips.
- **Simple pages.** Low element count, no large dropdowns or tables? The snapshot overhead is minimal.
- **Fewer tool calls.** `browser_fill_form` handles multiple fields at once. The CLI approach needs separate commands.
- **No file management.** No snapshot files to track, read, or clean up.

The tradeoff is clear: higher per-call cost, but sometimes fewer calls and simpler orchestration. For exploratory tasks on simple pages, MCP can actually be more efficient overall.

---

## The General Principle: Inline vs On-Demand

This isn't just about Playwright. The same pattern appears everywhere AI agents interact with tools:

| Domain | Inline (expensive) | On-Demand (efficient) |
|--------|-------------------|----------------------|
| API responses | Full nested objects | References + fetch |
| Database | `SELECT *` | `SELECT count(*)` first |
| File operations | `cat` entire file | `grep` for what you need |
| Code search | Full AST dump | Targeted regex |
| Browser automation | Full page snapshot | Targeted eval |

The principle: **return the minimum data needed for the next decision.**

When you're building tools that AI agents will call, think about what the LLM actually needs to see at each step. Usually it's not everything. Usually it's a confirmation, a count, or a targeted extraction. The full data should be available on demand, not forced into every response.

---

## Practical Recommendations

### For Tool Builders

1. **Support filtered responses.** Let the caller specify what they need. A `fields` parameter, a `verbose` flag, a `format` option.
2. **Offer a quiet mode.** Action confirmation without the full state dump. "Clicked button — OK" is often all the agent needs.
3. **Write verbose data to files.** Return a reference (file path, URL, ID). Let the agent decide whether to read the full content.
4. **Separate concerns.** Don't bundle console logs with DOM snapshots. Don't mix metadata with results.

### For Agent Developers

1. **Two-phase queries.** Count first, then list, then detail. Don't start with "give me everything."
2. **Snapshot budgets.** Limit full page reads to decision points. Most steps just need confirmation.
3. **Targeted eval over full scan.** `document.querySelector` beats the full accessibility tree when you know what you're looking for.
4. **Measure your token spend.** You can't optimize what you don't measure. Log token counts per step and look for outliers.

---

## The Takeaway

Token efficiency is the new performance optimization for AI applications. We've spent decades optimizing CPU cycles, memory usage, and network calls. Now we need to optimize context window usage with the same rigor.

Small per-call differences compound across agent workflows. That 500-token dropdown showing up in every snapshot? Across a 20-step agent workflow, it's 10,000 tokens of state options nobody asked for.

The best AI tools won't just be the most capable — they'll be the ones that respect the context window.

---

*Full comparison data and reproduction scripts are available in the [tokenbench repository](https://github.com/jackblacketter/tokenbench).*
