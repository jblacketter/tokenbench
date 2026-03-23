# Content-Safe Brief: MCP vs CLI Token Efficiency Case Study

Use this brief as the default source when drafting public-facing article or video content.
Use `examples/mcp-vs-cli/comparison-data.md` only for numeric verification and command-level details.

## Core Message

The same browser-automation outcome can use 2.5x to 3.8x more tokens depending on how tool output is delivered back to the model.

- MCP-style inline snapshots: ~3,075 total tokens
- CLI with on-demand reads: ~800 to ~1,225 total tokens

## Safe Demo Context

- Demo target: local fixture `scripts/fixtures/demo-form.html`
- No external accounts, authentication, or third-party services
- Task: enumerate `data-testid` values from the fixture page
- Output parity: both approaches return the same sorted JSON list

## Why the Gap Appears

1. Inline snapshots return full page trees repeatedly.
2. On-demand workflows return concise responses and only load details when requested.
3. Large page structures (for example dropdown option lists) inflate repeated snapshot size.

## Numerics To Preserve

- MCP total: ~3,075 tokens
- CLI total: ~800 (without snapshot file read) or ~1,225 (with file read)
- Ratio: ~2.5x to ~3.8x

## Language Guardrails

Prefer neutral wording:

- Say "uses more tokens" instead of "burns tokens"
- Say "open the local fixture page" instead of "get past login"
- Say "session metadata" instead of "auth token strings"
- Say "extract page attributes from the fixture" instead of account-oriented phrasing

Avoid instructions that imply bypassing security or handling real credentials.
