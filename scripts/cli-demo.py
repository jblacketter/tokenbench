#!/usr/bin/env python3
"""CLI-style browser demo.

Outputs:
- stdout: sorted JSON array of data-testid values
- stderr: per-step character and token estimates
"""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path

CHARS_PER_TOKEN = 4
EXPECTED_TESTID_COUNT = 24


def estimate_tokens(char_count: int) -> int:
    return max(1, math.ceil(char_count / CHARS_PER_TOKEN))


def fixture_url() -> str:
    fixture = Path(__file__).resolve().parent / "fixtures" / "demo-form.html"
    if not fixture.exists():
        raise SystemExit(f"Fixture not found: {fixture}")
    return fixture.as_uri()


def add_step(steps: list[tuple[str, int, int]], name: str, payload: str) -> None:
    char_count = len(payload)
    token_count = estimate_tokens(char_count)
    steps.append((name, char_count, token_count))


def load_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise SystemExit(
            "Playwright is required. Install with: pip install playwright && playwright install"
        ) from exc
    return sync_playwright


def main() -> None:
    steps: list[tuple[str, int, int]] = []
    values: list[str] = []
    url = fixture_url()
    sync_playwright = load_playwright()
    snapshot_dir = Path(tempfile.mkdtemp(prefix="tokenbench-cli-"))

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        payload_open = json.dumps(
            {
                "cmd": "open",
                "status": "ok",
                "browser": "chromium",
                "session": "default",
            },
            separators=(",", ":"),
        )
        add_step(steps, "open", payload_open)

        first_url = f"{url}#initial"
        page.goto(first_url, wait_until="domcontentloaded")
        snapshot_path_1 = snapshot_dir / "step-01-snapshot.html"
        snapshot_path_1.write_text(page.content(), encoding="utf-8")
        payload_goto_1 = json.dumps(
            {
                "cmd": "goto",
                "url": page.url,
                "title": page.title(),
                "snapshot_file": str(snapshot_path_1),
            },
            separators=(",", ":"),
        )
        add_step(steps, "goto(initial)", payload_goto_1)

        second_url = f"{url}#form"
        page.goto(second_url, wait_until="domcontentloaded")
        snapshot_path_2 = snapshot_dir / "step-02-snapshot.html"
        snapshot_path_2.write_text(page.content(), encoding="utf-8")
        payload_goto_2 = json.dumps(
            {
                "cmd": "goto",
                "url": page.url,
                "title": page.title(),
                "snapshot_file": str(snapshot_path_2),
            },
            separators=(",", ":"),
        )
        add_step(steps, "goto(form)", payload_goto_2)

        count = page.evaluate("() => document.querySelectorAll('[data-testid]').length")
        assert count == EXPECTED_TESTID_COUNT, (
            f"Expected {EXPECTED_TESTID_COUNT} data-testid values, got {count}"
        )
        payload_count = json.dumps(
            {"cmd": "eval", "query": "count_testids", "result": count},
            separators=(",", ":"),
        )
        add_step(steps, "eval(count)", payload_count)

        values = page.evaluate(
            """
            () => Array.from(document.querySelectorAll("[data-testid]"))
              .map(el => el.getAttribute("data-testid"))
              .filter(Boolean)
            """
        )
        unique_sorted = sorted(set(values))
        payload_list = json.dumps(
            {"cmd": "eval", "query": "list_testids", "result": unique_sorted},
            separators=(",", ":"),
        )
        add_step(steps, "eval(list)", payload_list)

        browser.close()

    total_chars = sum(step[1] for step in steps)
    total_tokens = sum(step[2] for step in steps)

    print("CLI-style token usage summary", file=sys.stderr)
    for name, char_count, token_count in steps:
        print(f"- {name}: chars={char_count}, est_tokens={token_count}", file=sys.stderr)
    print(
        f"TOTAL: chars={total_chars}, est_tokens={total_tokens} (~{CHARS_PER_TOKEN} chars/token)",
        file=sys.stderr,
    )
    print(f"Snapshot directory: {snapshot_dir}", file=sys.stderr)

    print(json.dumps(unique_sorted, separators=(",", ":")))


if __name__ == "__main__":
    main()
