# MCP Server vs playwright-cli: Raw Comparison Data

**Source:** Northstar QA environment (`https://northstar-qa.fly.dev`)
**Date:** 2026-02-10
**App:** Angular + Auth0, build v3.1.5818
**Page:** `/clearpath/new-deal` — 31 form elements, 51-option state dropdown, auto-opening Customer Priorities modal

---

## Task

Log in via Auth0, navigate to new-deal page, find all `data-testid` attributes.

**Result:** 24 data-testid attributes found on both approaches (identical output).

---

## MCP Server (`@playwright/mcp`) — 6 Tool Calls

| Step | Tool | Action | Output Tokens | Notes |
|------|------|--------|---------------|-------|
| 1 | `browser_navigate` | Go to QA URL (redirects to Auth0) | ~600 | Full login form snapshot inline + console events |
| 2 | `browser_fill_form` | Fill email + password (2 fields) | ~125 | Confirmation + console |
| 3 | `browser_click` | Click "Continue" button | ~250 | Empty snapshot + console (auth token strings) |
| 4 | `browser_navigate` | Go to `/clearpath/new-deal` | ~200 | Partial snapshot (page still loading) + console |
| 5 | `browser_wait_for` | Wait for "First Name" text | **~1,200** | **Full page snapshot inline** — all fields, 51 state options, console |
| 6 | `browser_evaluate` | `querySelectorAll('[data-testid]')` | ~550 | JSON array of 24 objects with tag/testid/text |
| | **TOTAL** | | **~2,925 output** | **~150 input, ~3,075 total** |

### Biggest Cost: Step 5 Snapshot

The `browser_wait_for` call returned the full accessibility tree including:
- 31 form fields with labels, roles, refs
- 51 state dropdown options (each ~10 tokens)
- Console events (Google Maps warning, auth logs)
- Navigation metadata

This single response was ~4,800 characters / ~1,200 tokens.

---

## playwright-cli (via Bash) — 8 Tool Calls

| Step | Command | Action | Output Tokens | Notes |
|------|---------|--------|---------------|-------|
| 1 | `open` | Launch headless browser | ~60 | Browser PID + blank page URL |
| 2 | `goto <url>` | Navigate to QA (redirects to Auth0) | ~90 | URL + title + snapshot **file path** |
| 3 | `snapshot` | Get element refs for login page | ~50 | Snapshot **file path** only |
| 3b | `Read` (file) | Read snapshot file to get refs | ~400 | Login form YAML (optional) |
| 4 | `fill e23 <password>` | Fill password field | ~25 | One-line confirmation |
| 5 | `click e28` | Click Continue button | ~90 | URL change + snapshot file path |
| 6 | `goto <url>` | Navigate to new-deal | ~90 | URL + snapshot file path |
| 7 | `eval <count>` | `querySelectorAll('[data-testid]').length` | ~60 | Returns `24` |
| 8 | `eval <reduce>` | Get all testid values as JSON string | ~210 | JSON string of 24 names |
| | **TOTAL** | | **~1,075 output** (with file read) | **~150 input, ~1,225 total** |
| | **TOTAL** | | **~675 output** (without file read) | **~125 input, ~800 total** |

### Key Difference: Snapshots to Files

Every `goto`, `click`, and `snapshot` command writes the accessibility tree to a `.yml` file and returns only the file path (~30 characters). The agent chooses when to read the file into context.

---

## Head-to-Head

| Metric | MCP Server | playwright-cli (with read) | playwright-cli (no read) |
|--------|-----------|---------------------------|--------------------------|
| Tool calls | 6 | 8 | 7 |
| Input tokens | ~150 | ~150 | ~125 |
| Output tokens | ~2,925 | ~1,075 | ~675 |
| **Total tokens** | **~3,075** | **~1,225** | **~800** |
| **Ratio** | **2.5x–3.8x** | 1x | 1x |

### Input tokens are nearly identical

The tool call parameters (URLs, refs, JS expressions) are roughly the same size. All of the cost difference is on the output side.

### The 51-state dropdown

The State `<select>` element has 51 options. In MCP, this appears in every snapshot:
```yaml
- combobox [ref=e58]:
  - option "Select State" [selected]
  - option "Oregon"
  - option "Washington"
  - option "Alabama"
  ... (51 total)
```
That's ~500 tokens per snapshot just for one dropdown. playwright-cli never includes this unless you explicitly read the snapshot file.

---

## Ergonomics Notes

### MCP Advantages
- `browser_fill_form` fills multiple fields in one call (email + password together)
- Element refs always available from inline snapshot — no separate read step
- Session management is automatic
- `browser_evaluate` returns structured JSON cleanly

### playwright-cli Advantages
- Snapshots to files — only read when needed
- `eval` returns just the answer (targeted queries)
- Multiple named sessions supported
- Lower per-step token cost

### playwright-cli Quirks
- `eval` chokes on `.map()` — use `.reduce()` or `forEach` + push instead
- `run-code` has issues with `await` and multi-statement expressions
- Need to manually `open` / `close` browser sessions
- `fill <ref> <value>` requires a prior `snapshot` to get refs

---

## data-testid Attributes Found (24)

**Navigation (3):**
`nav-create-writeup-btn`, `nav-user-menu-btn`, `nav-logout-link`

**Customer Section (13):**
`new-deal-customer-section`, `new-deal-first-name-input`, `new-deal-middle-name-input`, `new-deal-last-name-input`, `new-deal-company-name-input`, `new-deal-street-input`, `new-deal-city-input`, `new-deal-state-select`, `new-deal-county-input`, `new-deal-county-select`, `new-deal-zip-input`, `new-deal-phone-input`, `new-deal-email-input`

**Vehicle Section (8):**
`new-deal-vehicle-section`, `new-deal-vehicle-lookup-btn`, `new-deal-stock-number-input`, `new-deal-odometer-input`, `new-deal-plate-number-input`, `new-deal-plate-expires-input`, `new-deal-sales-id-input`, `new-deal-continue-btn`
