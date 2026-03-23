# Video Script: "Your AI Agent Is Using 3x More Tokens Than It Needs To"

**Format:** Screen recording with voiceover, ~5-7 minutes
**Software:** Split-screen terminal recording (e.g., OBS, ScreenFlow)

---

## Opening (30 seconds)

**Visual:** Title card with the headline and the number "3.8x"

**Voiceover:**
> "Same task. Same browser. Same result. But one approach used almost four times more tokens than the other. Today I'll show you exactly why — and what it means for anyone building AI-powered tools."

---

## Part 1: The Task (45 seconds)

**Visual:** Browser showing the target form page — 31 fields, state dropdown, modal

**Voiceover:**
> "Here's the task: open a local fixture page in a browser, navigate to this form view, and extract all the data-testid attributes. It's a standard QA automation task.
>
> The page has 31 form fields, a 51-option state dropdown, and a modal that auto-opens. Real production complexity.
>
> We'll run this with two different browser automation approaches and count every token."

---

## Part 2: MCP Server Run (90 seconds)

**Visual:** Terminal on the left, running the MCP demo. Token counter overlay in the corner, incrementing with each step.

**Voiceover (step by step):**
> "First up: the MCP Server approach. We call browser_navigate..."
> [Show the inline snapshot appearing — the full YAML accessibility tree]
>
> "See that? The tool returned the entire page structure inline. Every field, every label, every dropdown option. We didn't ask for this — it's just how MCP delivers results."
>
> [Pause on the 51-state dropdown in the snapshot output]
>
> "There's our 51-state dropdown. That's about 500 tokens right there. And this shows up in *every* snapshot."
>
> [Continue through remaining steps, token counter climbing]
>
> "Six tool calls. 3,075 tokens total. Most of it output we never needed."

**Visual:** Final token count highlighted: **3,075**

---

## Part 3: playwright-cli Run (90 seconds)

**Visual:** Terminal on the right (or switch to right side of split screen). Same token counter overlay.

**Voiceover:**
> "Now the same task with playwright-cli."
>
> [Show goto command, response is just a file path]
>
> "See the difference? The snapshot went to a file. All we got back was the file path — about 30 characters."
>
> [Show eval command returning just the count: 24]
>
> "We ask 'how many testid attributes?' and get back just the number. No accessibility tree, no dropdown options, no console logs."
>
> [Show eval command returning the JSON array]
>
> "Then we ask for the list and get a clean JSON array. 24 strings, nothing else."

**Visual:** Final token count highlighted: **800**

---

## Part 4: Side by Side (60 seconds)

**Visual:** Split screen with both terminals. Comparison table overlay.

| | MCP Server | playwright-cli |
|--|-----------|----------------|
| Tool calls | 6 | 7-8 |
| Output tokens | ~2,925 | ~675 |
| **Total** | **3,075** | **800** |

**Voiceover:**
> "Side by side, the input tokens are almost identical — the URLs, the JavaScript expressions, they're the same size. All the difference is on the output side.
>
> MCP returned nearly 3,000 tokens of output. The CLI returned 675. Same information extracted at the end."

---

## Part 5: Why It Matters (60 seconds)

**Visual:** Animated diagram showing token costs multiplying across a 10-step workflow

**Voiceover:**
> "Now multiply this by a real agent workflow. Ten steps? Twenty? That 2,000-token difference per step becomes 20,000 to 40,000 tokens of overhead.
>
> That's not just cost — though at current API prices it adds up. It's context window pressure. Every unnecessary token in context makes the model slightly less focused on what matters. And eventually, you hit the window limit."

---

## Part 6: The Principle (45 seconds)

**Visual:** Diagram showing "Inline vs On-Demand Data Delivery" with examples across domains

**Voiceover:**
> "This isn't just about Playwright. It's a general principle: inline versus on-demand data delivery.
>
> API responses that return everything versus letting you fetch what you need. Database queries that select star versus counting first. File operations that cat the whole file versus grepping for what matters.
>
> The principle: return the minimum data needed for the next decision."

---

## Closing (30 seconds)

**Visual:** Recommendations list, then repo link

**Voiceover:**
> "If you're building tools for AI agents: support filtered responses, offer a quiet mode, write verbose data to files.
>
> If you're building agents: count first then list, budget your snapshots, and measure your token spend.
>
> All the raw data and reproduction scripts are linked below. Token efficiency is the new performance optimization — and it starts with how your tools talk to your models."

---

## Production Notes

- Total runtime target: 5-7 minutes
- Record both demos against the local HTML fixture (`scripts/fixtures/demo-form.html`)
- Token counter can be a simple overlay graphic, updated per-step in post-production
- Key moment to emphasize: the first time the full MCP snapshot appears — pause and let the viewer scroll through it
- The 51-state dropdown in the snapshot is the most visual "aha moment"
- End card: repo URL, social links
