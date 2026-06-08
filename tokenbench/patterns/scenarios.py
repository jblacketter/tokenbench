"""Concrete, offline, reproducible pattern scenarios — the measurement source of truth.

Three families are represented, each with one anchor scenario:

- **Data Delivery / Filtered Response** — return only the fields the caller needs
  instead of the whole record. Measured from real fixture payloads.
- **Query / Reference + Fetch** — a captured browser-automation measurement where one
  approach inlines a full snapshot per tool call and the other writes the snapshot to
  a file and returns a path, so the agent pulls the full tree into context only on
  demand. Anchored in real captured token counts.
- **Agent Loop / Snapshot Budget** — across a multi-step loop, keep a bounded set of
  recent full snapshots and replace older ones with a one-line reference, instead of
  re-inlining every snapshot every step.

The numbers here are what the ``patterns/`` docs render, so the docs cannot drift.
"""

from __future__ import annotations

from pathlib import Path

from .harness import Scenario, Variant

_FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


# --------------------------------------------------------------- Data Delivery


def _data_delivery_scenario() -> Scenario:
    full = _read("api_response_full.json")
    filtered = _read("api_response_filtered.json")
    return Scenario(
        key="filtered-response",
        family="Data Delivery",
        pattern="Filtered Response",
        title="Return only the fields the caller needs instead of the whole record.",
        baseline=Variant("Full user record", payload=full),
        efficient=Variant("Seat-usage projection", payload=filtered),
        note="A 'how many seats are used?' question needs 5 fields, not the entire "
        "user object with billing, address, flags, and HATEOAS links.",
    )


# --------------------------------------------------------------- Query (real)


def _query_scenario() -> Scenario:
    # Real captured totals from a browser-automation measurement: same task, same
    # output, two tool-output delivery styles (inline snapshots vs snapshot-to-file).
    return Scenario(
        key="reference-fetch",
        family="Query",
        pattern="Reference + Fetch",
        title="Write large snapshots to files and return a path; pull into context "
        "only when needed.",
        baseline=Variant("Inline tool snapshots", tokens=3075, source="measured"),
        efficient=Variant("Snapshot → file reference", tokens=800, source="measured"),
        note="Identical task and identical output (24 elements found). All of the "
        "difference is snapshot inlining on the output side.",
    )


# --------------------------------------------------------------- Agent Loop


def _agent_loop_scenario(steps: int = 6, keep: int = 2) -> Scenario:
    """Across ``steps`` steps, baseline re-inlines the full snapshot every step;
    Snapshot Budget keeps only the ``keep`` most recent full snapshots and replaces
    older ones with a short reference line."""
    snapshot = _read("step_snapshot.txt")
    reference_line = "[snapshot step {i} → ./snapshots/step_{i}.txt (1,042 chars)]\n"

    baseline_payload = "".join(
        f"## Step {i}\n{snapshot}\n" for i in range(1, steps + 1)
    )

    budget_parts = []
    for i in range(1, steps + 1):
        if i > steps - keep:
            budget_parts.append(f"## Step {i}\n{snapshot}\n")
        else:
            budget_parts.append(f"## Step {i}\n{reference_line.format(i=i)}")
    budget_payload = "".join(budget_parts)

    return Scenario(
        key="snapshot-budget",
        family="Agent Loop",
        pattern="Snapshot Budget",
        title=f"Across a {steps}-step loop, keep the {keep} most recent full "
        "snapshots and reference older ones instead of re-inlining every step.",
        baseline=Variant(f"Full snapshot every step (×{steps})", payload=baseline_payload),
        efficient=Variant(
            f"Budget: last {keep} full, rest referenced", payload=budget_payload
        ),
        note="Older snapshots are rarely re-read, but re-inlining them every step "
        "multiplies their cost by the loop length.",
    )


_SCENARIOS: list[Scenario] = [
    _data_delivery_scenario(),
    _query_scenario(),
    _agent_loop_scenario(),
]


def all_scenarios() -> list[Scenario]:
    return list(_SCENARIOS)


def get_scenario(key: str) -> Scenario:
    for s in _SCENARIOS:
        if s.key == key:
            return s
    raise KeyError(f"unknown scenario: {key!r}")
