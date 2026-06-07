# Reference + Fetch

**Family:** Query

## Problem

Browser- and tool-automation surfaces tend to inline a full accessibility/DOM
snapshot in *every* tool result. Most of that tree is never read, but it is paid for
on every navigation, click, and wait — and it accumulates in context across the
whole session.

## Forces

- The agent sometimes *does* need the full tree (to find a ref), so you can't just
  drop it.
- Inlining is the path of least resistance for a tool author — returning everything
  "just works."
- The cost is invisible per-call but compounds across a multi-step task.

## Solution

Have the tool **write the large artifact to a file and return only a reference**
(a path + a one-line summary). The agent pulls the full tree into context **on
demand**, only when it actually needs to resolve a ref or inspect structure.

This is the core finding of the project's MCP-vs-CLI case study: same task, same
output (24 `data-testid` attributes), but the CLI snapshots-to-file approach spends a
fraction of the tokens because the giant trees stay out of context until asked for.

## When to use

- Any tool that emits large, mostly-unread structured artifacts (DOM trees, API
  dumps, logs, build output).
- Multi-step agent loops where the artifact would otherwise be re-inlined repeatedly.

## When not

- Tiny results where a file indirection adds more ceremony than it saves.
- One-shot lookups where the agent will definitely read the whole artifact anyway.

## Token impact (measured)

<!-- BEGIN GENERATED: reference-fetch -->
| Approach | Tokens |
| --- | ---: |
| MCP Server (inline snapshots) (baseline) | 3,075 |
| playwright-cli (snapshot→file) (efficient) | 800 |
| **Saved** | **2,275 (74.0%)** |
| **Ratio** | **3.84×** |

_Source: real captured measurement._
<!-- END GENERATED -->

## Tradeoffs

- **Latency:** one extra read step when the artifact *is* needed; net win because most
  artifacts aren't.
- **Ergonomics:** the agent must opt in to reading; worth it at scale.
- **Quality:** identical — the data is still available, just not forced into context.

## Related patterns

- **Filtered Response** — when you can shape the payload instead of referencing it.
- **Snapshot Budget** — bound how many fetched snapshots you keep around in a loop.

## Source

`examples/mcp-vs-cli/comparison-data.md` (Northstar QA, 2026-02-10).
