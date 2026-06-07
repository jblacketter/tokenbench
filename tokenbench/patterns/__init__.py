"""Token-efficiency pattern library (Phase 3).

A small, dependency-free, fully-offline harness that pairs each documented
token-efficiency pattern with a *reproducible measurement*. The measurement source
of truth lives in code (``scenarios.py``); the markdown tables in ``patterns/`` are
generated from it so prose can never silently drift from the numbers.
"""

from .harness import (
    Scenario,
    Variant,
    estimate_tokens,
    render_markdown,
    render_markdown_block,
    render_table,
)
from .scenarios import all_scenarios, get_scenario

__all__ = [
    "Scenario",
    "Variant",
    "estimate_tokens",
    "render_markdown",
    "render_markdown_block",
    "render_table",
    "all_scenarios",
    "get_scenario",
]
