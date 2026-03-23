# MCP vs CLI Comparison Table

| Metric | MCP Server | playwright-cli (with read) | playwright-cli (no read) |
|---|---:|---:|---:|
| Tool calls | 6 | 8 | 7 |
| Input tokens | ~150 | ~150 | ~125 |
| Output tokens | ~2,925 | ~1,075 | ~675 |
| Total tokens | **~3,075** | **~1,225** | **~800** |
| Ratio vs best case | **3.8x** | 1.5x | 1.0x |

Source: `examples/mcp-vs-cli/comparison-data.md`
