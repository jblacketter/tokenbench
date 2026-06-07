"""Standardized token-efficiency benchmark suite (Phase 4).

Generalizes the Phase 3 pattern harness from two-way comparisons to multi-approach
benchmark cases across a standard task set. Offline and deterministic. The pattern
scenario registry is the single source of truth for any Phase 3-derived numbers
(see ``cases.py`` — the pattern→benchmark bridge).
"""

from .cases import Approach, BenchmarkCase, all_cases
from .runner import (
    SCHEMA_VERSION,
    canonical_json,
    check_results,
    measure_all,
    render_table,
    results_payload,
)

__all__ = [
    "Approach",
    "BenchmarkCase",
    "all_cases",
    "SCHEMA_VERSION",
    "canonical_json",
    "check_results",
    "measure_all",
    "render_table",
    "results_payload",
]
