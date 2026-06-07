"""Run benchmark cases and produce stable artifacts.

The results payload is canonical and deterministic (sorted keys, fixed ordering),
so it can be committed to ``benchmarks/results.json`` and re-verified with
``check_results`` — the living-benchmark guard that makes any change to the numbers
an intentional, reviewable diff.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..patterns.harness import CHARS_PER_TOKEN
from .cases import all_cases

SCHEMA_VERSION = 1

# Repo-root-relative committed results artifact.
RESULTS_PATH = Path(__file__).resolve().parents[2] / "benchmarks" / "results.json"


def measure_all() -> list[dict]:
    """Measure every case; ordering is stable (cases are pre-sorted)."""
    return [c.measure() for c in all_cases()]


def results_payload() -> dict:
    """The full, canonical results object (what lives in results.json)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "chars_per_token": CHARS_PER_TOKEN,
        "cases": measure_all(),
    }


def canonical_json(payload: dict | None = None) -> str:
    """Deterministic JSON text: sorted keys + trailing newline."""
    payload = payload if payload is not None else results_payload()
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _ratio_str(ratio) -> str:
    return "∞" if ratio == float("inf") else f"{ratio}×"


def render_table(rows: list[dict] | None = None) -> str:
    rows = rows if rows is not None else measure_all()
    headers = ["category", "task", "baseline", "best", "best→", "ratio", "src"]
    data = [
        [
            r["category"],
            r["task"],
            f'{r["baseline_tokens"]:,}',
            f'{r["best_tokens"]:,}',
            r["best_label"],
            _ratio_str(r["ratio_vs_baseline"]),
            (
                "meas"
                if any(a["source"] == "measured" for a in r["approaches"])
                else "esti"
            ),
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


def load_committed(path: Path = RESULTS_PATH) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def check_results(path: Path = RESULTS_PATH) -> list[str]:
    """Return human-readable diffs between current run and the committed artifact.

    Empty list == in sync.
    """
    committed = load_committed(path)
    if committed is None:
        return [f"missing results artifact: {path} (run `tokenbench bench --json > {path}`)"]
    current = results_payload()
    problems: list[str] = []
    if committed.get("schema_version") != current["schema_version"]:
        problems.append(
            f"schema_version: committed={committed.get('schema_version')} "
            f"current={current['schema_version']}"
        )
    if committed.get("chars_per_token") != current["chars_per_token"]:
        problems.append(
            f"chars_per_token: committed={committed.get('chars_per_token')} "
            f"current={current['chars_per_token']}"
        )
    cur_by_key = {(c["category"], c["task"]): c for c in current["cases"]}
    com_by_key = {(c["category"], c["task"]): c for c in committed.get("cases", [])}
    for key in sorted(set(cur_by_key) | set(com_by_key)):
        if key not in com_by_key:
            problems.append(f"new case not in artifact: {key}")
        elif key not in cur_by_key:
            problems.append(f"artifact case no longer produced: {key}")
        elif cur_by_key[key] != com_by_key[key]:
            problems.append(
                f"numbers changed for {key}: "
                f"committed best={com_by_key[key].get('best_tokens')} "
                f"current best={cur_by_key[key].get('best_tokens')}"
            )
    return problems


def write_results(path: Path = RESULTS_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(), encoding="utf-8")
    return path
