"""Measurement harness for the token-efficiency pattern library.

Design goals:
- **Deterministic & offline.** No model/API calls. Token counts come from a
  character-proxy estimator (the project standard, ~4 chars/token; see the
  2026-02-10 decision-log entry) or from explicit real-world overrides for
  scenarios anchored in captured production data (e.g. MCP-vs-CLI).
- **Single source of truth.** Scenarios live in code; the markdown tables in the
  ``patterns/`` docs are generated from these objects so prose cannot drift from the
  numbers. A test regenerates each block and asserts the docs are in sync.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

# The project's standard token proxy (decision log, 2026-02-10). The library cares
# about ratios between approaches, so an approximate-but-stable estimator is ideal;
# an exact tokenizer can be plugged in later without changing the scenario API.
CHARS_PER_TOKEN = 4


def estimate_tokens(text: str, chars_per_token: int = CHARS_PER_TOKEN) -> int:
    """Estimate tokens for a payload string via the character proxy."""
    if not text:
        return 0
    return math.ceil(len(text) / chars_per_token)


@dataclass(frozen=True)
class Variant:
    """One approach in a comparison.

    Provide either a representative ``payload`` (token count is estimated) or a
    ``tokens`` override for scenarios anchored in real captured measurements.
    """

    label: str
    payload: Optional[str] = None
    tokens: Optional[int] = None
    source: str = "estimated"  # "estimated" | "measured"

    def token_count(self) -> int:
        if self.tokens is not None:
            return self.tokens
        return estimate_tokens(self.payload or "")


@dataclass(frozen=True)
class Scenario:
    """A named baseline-vs-efficient comparison for one pattern."""

    key: str
    family: str  # "Data Delivery" | "Query" | "Agent Loop"
    pattern: str  # the pattern name this scenario demonstrates
    title: str
    baseline: Variant  # the inefficient approach
    efficient: Variant  # the token-efficient approach
    note: str = ""

    def measure(self) -> dict:
        b = self.baseline.token_count()
        e = self.efficient.token_count()
        saved = b - e
        ratio = round(b / e, 2) if e else float("inf")
        pct = round(100.0 * saved / b, 1) if b else 0.0
        return {
            "key": self.key,
            "family": self.family,
            "pattern": self.pattern,
            "title": self.title,
            "baseline_label": self.baseline.label,
            "efficient_label": self.efficient.label,
            "baseline_tokens": b,
            "efficient_tokens": e,
            "saved_tokens": saved,
            "ratio": ratio,
            "reduction_pct": pct,
            "source": (
                "measured"
                if "measured" in (self.baseline.source, self.efficient.source)
                else "estimated"
            ),
            "note": self.note,
        }


# --------------------------------------------------------------------------- render


def _ratio_str(ratio) -> str:
    return "∞" if ratio == float("inf") else f"{ratio}×"


def render_table(scenarios: list[Scenario]) -> str:
    """Plain-text results table for the CLI."""
    rows = [s.measure() for s in scenarios]
    headers = ["family", "pattern", "baseline", "efficient", "saved", "ratio", "src"]
    data = [
        [
            r["family"],
            r["pattern"],
            f'{r["baseline_tokens"]:,}',
            f'{r["efficient_tokens"]:,}',
            f'{r["saved_tokens"]:,} ({r["reduction_pct"]}%)',
            _ratio_str(r["ratio"]),
            r["source"][:4],
        ]
        for r in rows
    ]
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in data)) if data else len(headers[i])
        for i in range(len(headers))
    ]
    def fmt(cols):
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))

    lines = [fmt(headers), "  ".join("-" * w for w in widths)]
    lines += [fmt(row) for row in data]
    return "\n".join(lines)


def render_markdown_block(scenario: Scenario) -> str:
    """The generated measurement block embedded into a pattern doc.

    Kept tightly formatted so the in-sync test can match it exactly.
    """
    r = scenario.measure()
    src_note = (
        "real captured measurement"
        if r["source"] == "measured"
        else f"estimated at ~{CHARS_PER_TOKEN} chars/token"
    )
    return (
        f"| Approach | Tokens |\n"
        f"| --- | ---: |\n"
        f"| {r['baseline_label']} (baseline) | {r['baseline_tokens']:,} |\n"
        f"| {r['efficient_label']} (efficient) | {r['efficient_tokens']:,} |\n"
        f"| **Saved** | **{r['saved_tokens']:,} ({r['reduction_pct']}%)** |\n"
        f"| **Ratio** | **{_ratio_str(r['ratio'])}** |\n"
        f"\n_Source: {src_note}._"
    )


def render_markdown(scenarios: list[Scenario]) -> str:
    """Full markdown for all scenarios (used by `--markdown`)."""
    out = ["# Pattern measurements\n"]
    for s in scenarios:
        out.append(f"## {s.family} — {s.pattern}\n")
        out.append(f"_{s.title}_\n")
        out.append(render_markdown_block(s))
        if s.note:
            out.append(f"\n> {s.note}")
        out.append("")
    return "\n".join(out)
