# Reproduction Scripts

Reproduce the MCP vs playwright-cli token comparison from the article.

## Prerequisites

- Python 3.11+
- Playwright: `pip install playwright && playwright install`
- No external accounts or services needed — uses a local HTML fixture

## Files

| File | Description |
|------|-------------|
| `fixtures/demo-form.html` | Local HTML page with form fields and `data-testid` attributes |
| `mcp-demo.py` | Simulates MCP-style inline accessibility snapshots |
| `cli-demo.py` | Runs the task via playwright-cli shell commands |

## Quick Start

```bash
# Run MCP approach
python scripts/mcp-demo.py > /tmp/mcp-output.json

# Run CLI approach
python scripts/cli-demo.py > /tmp/cli-output.json

# Verify identical output
diff /tmp/mcp-output.json /tmp/cli-output.json
# Expected: no output (files match)
```

## Verification

Both scripts output a sorted JSON array of `data-testid` values to stdout and a token usage summary to stderr.

```bash
# Validate output format
python -c "import json, sys; d=json.load(open(sys.argv[1])); assert isinstance(d, list) and all(isinstance(s, str) for s in d) and d == sorted(d)" /tmp/mcp-output.json
```

## Accuracy Note

- `mcp-demo.py` is a simulation of MCP-style inline verbosity and uses a YAML-like accessibility snapshot representation.
- It is intended to demonstrate the **relative inline-vs-on-demand pattern**, not to reproduce exact `@playwright/mcp` token totals byte-for-byte.
- `comparison-data.md` remains the source of truth for measured production numbers.

## How It Works

Both scripts open the local fixture page (`fixtures/demo-form.html`) in a headless browser and extract all elements with `data-testid` attributes. The key difference is how each approach returns data to the caller:

- **MCP (simulated)** returns full accessibility-tree-style snapshots inline with every tool response
- **CLI** writes snapshots to files and returns only targeted query results

Each script logs per-step character counts and estimated token usage (~4 chars/token) to stderr so you can see exactly where the cost difference comes from.
