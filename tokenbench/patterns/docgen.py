"""Keep the ``patterns/`` docs' measurement tables generated from the harness.

Each pattern doc contains a generated region delimited by HTML comment markers:

    <!-- BEGIN GENERATED: <scenario-key> -->
    ...harness output...
    <!-- END GENERATED -->

``sync_all()`` rewrites those regions from the live scenarios; ``check_all()`` reports
any doc whose region has drifted. A test calls ``check_all()`` so prose can never
diverge from the numbers.
"""

from __future__ import annotations

from pathlib import Path

from .harness import render_markdown_block
from .scenarios import all_scenarios, get_scenario

# Repo-root-relative doc files, one per scenario.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOC_DIR = _REPO_ROOT / "patterns"

_DOC_FILES = {
    "filtered-response": _DOC_DIR / "data-delivery" / "filtered-response.md",
    "reference-fetch": _DOC_DIR / "query" / "reference-fetch.md",
    "snapshot-budget": _DOC_DIR / "agent-loop" / "snapshot-budget.md",
}


def _markers(key: str) -> tuple[str, str]:
    return f"<!-- BEGIN GENERATED: {key} -->", "<!-- END GENERATED -->"


def generated_region(key: str) -> str:
    """The full marker-delimited block for a scenario (what lives in the doc)."""
    begin, end = _markers(key)
    block = render_markdown_block(get_scenario(key))
    return f"{begin}\n{block}\n{end}"


def replace_region(text: str, key: str) -> str:
    begin, end = _markers(key)
    region = generated_region(key)
    if begin in text and end in text:
        pre = text[: text.index(begin)]
        post = text[text.index(end) + len(end) :]
        return f"{pre}{region}{post}"
    # No markers yet — append the region.
    sep = "" if text.endswith("\n") else "\n"
    return f"{text}{sep}\n{region}\n"


def doc_files() -> dict[str, Path]:
    return dict(_DOC_FILES)


def sync_all() -> list[Path]:
    """Rewrite every doc's generated region. Returns the files changed."""
    changed = []
    for key, path in _DOC_FILES.items():
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated = replace_region(original, key)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(path)
    return changed


def check_all() -> list[str]:
    """Return human-readable problems: missing docs or out-of-sync regions."""
    problems: list[str] = []
    keys = {s.key for s in all_scenarios()}
    for key in keys:
        path = _DOC_FILES.get(key)
        if path is None:
            problems.append(f"no doc mapping for scenario {key!r}")
            continue
        if not path.exists():
            problems.append(f"missing doc file: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if generated_region(key) not in text:
            problems.append(f"out-of-sync measurement block in {path} (run `sync_all`)")
    return problems
