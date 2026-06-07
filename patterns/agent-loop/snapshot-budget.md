# Snapshot Budget

**Family:** Agent Loop

## Problem

In a multi-step agent loop, each step often appends a fresh full snapshot (page
state, tool output, intermediate result) to the running context. By the last step
the early snapshots are still sitting in context — re-paid on every model call —
even though they're rarely re-read.

## Forces

- Recent snapshots genuinely matter; the agent needs current state.
- Older snapshots *occasionally* matter, so you can't blindly delete them.
- Cost scales with loop length × snapshot size — exactly the regime where small
  per-step waste becomes large.

## Solution

Keep a **budget**: retain the *N* most recent full snapshots and replace older ones
with a one-line reference (a path + size). If the agent needs an old snapshot, it
fetches it back (see Reference + Fetch). The carried context stays roughly constant
instead of growing linearly with the loop.

## When to use

- Long tool loops (browser automation, iterative refactors, multi-file edits) where
  each step emits a sizable snapshot.
- Any loop whose context grows step-over-step with mostly-stale state.

## When not

- Short loops (2–3 steps) where the budget machinery isn't worth it.
- Tasks that genuinely re-read all prior state each step (rare).

## Token impact (measured)

<!-- BEGIN GENERATED: snapshot-budget -->
| Approach | Tokens |
| --- | ---: |
| Full snapshot every step (×6) (baseline) | 1,434 |
| Budget: last 2 full, rest referenced (efficient) | 545 |
| **Saved** | **889 (62.0%)** |
| **Ratio** | **2.63×** |

_Source: estimated at ~4 chars/token._
<!-- END GENERATED -->

## Tradeoffs

- **Latency:** a re-fetch costs one step on the rare occasions an old snapshot is
  needed.
- **Ergonomics:** needs a retention policy; a fixed "keep last N" is simple and good.
- **Quality:** neutral when the budget covers the snapshots actually in play; tune N
  if the agent keeps re-fetching.

## Related patterns

- **Reference + Fetch** — the mechanism for pulling an evicted snapshot back.
- **Context Pruning** — the general case of dropping low-value context.
