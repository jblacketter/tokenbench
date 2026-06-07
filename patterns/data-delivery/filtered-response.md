# Filtered Response

**Family:** Data Delivery

## Problem

A tool returns the entire record — every field, nested object, and HATEOAS link —
when the agent only needed a handful of values to answer the question. The unused
fields are pure overhead: they cost output tokens on the way in and clutter the
context for every subsequent turn.

## Forces

- The producing API often can't know which fields the caller needs, so it returns
  everything "to be safe."
- Filtering on the client *after* the full payload is in context saves nothing — the
  tokens were already spent receiving it.
- Over-filtering risks a second round-trip if a needed field was dropped.

## Solution

Shape the response to the question **before** it enters the context window: request
a field projection (sparse fieldset / GraphQL selection / a purpose-built endpoint)
so the tool returns only what the task needs.

## When to use

- Read paths where the caller knows exactly which fields it needs.
- Large records with deep nesting, metadata envelopes, or link sections.

## When not

- Exploratory work where you don't yet know which fields matter (use Progressive
  Disclosure instead — fetch a summary, then drill in).
- When a second round-trip would cost more than the fields you'd save.

## Token impact (measured)

<!-- BEGIN GENERATED: filtered-response -->
| Approach | Tokens |
| --- | ---: |
| Full user record (baseline) | 440 |
| Seat-usage projection (efficient) | 27 |
| **Saved** | **413 (93.9%)** |
| **Ratio** | **16.3×** |

_Source: estimated at ~4 chars/token._
<!-- END GENERATED -->

## Tradeoffs

- **Latency:** usually neutral or better (less to serialize/transfer).
- **Ergonomics:** the caller must declare its needs; a shared projection helper keeps
  this cheap.
- **Quality:** neutral — identical answer from fewer tokens.

## Related patterns

- **Progressive Disclosure** — summary first, details on demand.
- **Reference + Fetch** — return a handle to the big payload, fetch only if needed.
