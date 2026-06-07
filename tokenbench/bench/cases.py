"""Benchmark cases: the standard task set, measured offline.

A ``BenchmarkCase`` is a task with two or more named ``Approach`` options, each
measured in tokens. The best approach is compared to the declared baseline.

Phase 3-derived numbers come **only** through ``_from_scenario`` (the pattern→
benchmark bridge), so patterns and benchmarks never duplicate a number. New
categories (Code Search, Document Analysis) add their own offline fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..patterns.harness import Variant, estimate_tokens
from ..patterns.scenarios import all_scenarios

_FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


@dataclass(frozen=True)
class Approach:
    label: str
    payload: Optional[str] = None
    tokens: Optional[int] = None
    source: str = "estimated"  # "estimated" | "measured"

    def token_count(self) -> int:
        if self.tokens is not None:
            return self.tokens
        return estimate_tokens(self.payload or "")


@dataclass(frozen=True)
class BenchmarkCase:
    category: str
    task: str
    baseline_label: str
    approaches: tuple[Approach, ...]

    def measure(self) -> dict:
        counts = {a.label: a.token_count() for a in self.approaches}
        baseline_tokens = counts[self.baseline_label]
        best_label = min(counts, key=lambda k: counts[k])
        best_tokens = counts[best_label]
        saved = baseline_tokens - best_tokens
        ratio = round(baseline_tokens / best_tokens, 2) if best_tokens else float("inf")
        pct = round(100.0 * saved / baseline_tokens, 1) if baseline_tokens else 0.0
        return {
            "category": self.category,
            "task": self.task,
            "baseline_label": self.baseline_label,
            "baseline_tokens": baseline_tokens,
            "best_label": best_label,
            "best_tokens": best_tokens,
            "saved_tokens": saved,
            "ratio_vs_baseline": ratio,
            "reduction_pct": pct,
            "approaches": [
                {"label": a.label, "tokens": a.token_count(), "source": a.source}
                for a in self.approaches
            ],
        }


# ---------------------------------------------------- pattern bridge (sole source)


def _variant_to_approach(v: Variant) -> Approach:
    # Carry over the pattern Variant's exact token logic so the number is identical.
    return Approach(label=v.label, payload=v.payload, tokens=v.tokens, source=v.source)


def _from_scenario(scenario) -> BenchmarkCase:
    """Bridge a Phase 3 pattern Scenario into a 2-approach benchmark case.

    The category is mapped to the standard task-set name; the numbers come straight
    from the pattern registry (no re-measurement, no duplication)."""
    category_map = {
        "Query": "Browser Automation",
        "Data Delivery": "API Interaction",
        "Agent Loop": "Agent Loop",
    }
    return BenchmarkCase(
        category=category_map.get(scenario.family, scenario.family),
        task=scenario.pattern,
        baseline_label=scenario.baseline.label,
        approaches=(
            _variant_to_approach(scenario.baseline),
            _variant_to_approach(scenario.efficient),
        ),
    )


# ---------------------------------------------------- new standard-task cases


def _code_search_case() -> BenchmarkCase:
    full = _read("code_search_full.txt")
    targeted = _read("code_search_targeted.txt")
    return BenchmarkCase(
        category="Code Search",
        task="Targeted ripgrep vs whole-file read",
        baseline_label="Read whole files into context",
        approaches=(
            Approach("Read whole files into context", payload=full),
            Approach("ripgrep match + targeted line range", payload=targeted),
        ),
    )


def _document_analysis_case() -> BenchmarkCase:
    full = _read("document_full.md")
    chunks = _read("document_chunks.md")
    return BenchmarkCase(
        category="Document Analysis",
        task="Chunk-and-retrieve vs whole-document inline",
        baseline_label="Inline the whole document",
        approaches=(
            Approach("Inline the whole document", payload=full),
            Approach("Retrieve only relevant chunks", payload=chunks),
        ),
    )


def all_cases() -> list[BenchmarkCase]:
    """All benchmark cases: pattern-derived (bridged) + new standard-task cases."""
    bridged = [_from_scenario(s) for s in all_scenarios()]
    extra = [_code_search_case(), _document_analysis_case()]
    cases = bridged + extra
    # Stable order by (category, task) so output is deterministic regardless of source.
    cases.sort(key=lambda c: (c.category, c.task))
    return cases
