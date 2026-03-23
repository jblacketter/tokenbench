#!/usr/bin/env python3
"""MCP-style browser demo (simulated).

This script does not call `@playwright/mcp` directly. It simulates MCP-like
inline responses by embedding a YAML-like accessibility snapshot in each step.

Outputs:
- stdout: sorted JSON array of data-testid values
- stderr: per-step character and token estimates
"""

from __future__ import annotations

import json
import math
import sys
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


def _clean_text(value: str) -> str:
    return " ".join((value or "").split())


def _escape(value: str) -> str:
    return _clean_text(value).replace('"', "'")


def build_accessibility_yaml(page) -> str:
    nodes = page.evaluate(
        """
        () => {
          const items = Array.from(document.querySelectorAll('[data-testid]'));
          return items.map((el) => ({
            tag: el.tagName.toLowerCase(),
            testid: el.getAttribute('data-testid') || '',
            name: el.getAttribute('name') || '',
            aria: el.getAttribute('aria-label') || '',
            text: (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 120),
            options: el.tagName.toLowerCase() === 'select'
              ? Array.from(el.options).map(o => (o.textContent || '').trim())
              : []
          }));
        }
        """
    )

    lines: list[str] = []
    lines.append("- document:")
    lines.append(f"  - url: \"{_escape(page.url)}\"")
    lines.append("  - accessibility_tree:")

    for idx, node in enumerate(nodes, start=1):
        tag = _escape(node.get("tag", "element"))
        testid = _escape(node.get("testid", ""))
        name = _escape(node.get("name", ""))
        aria = _escape(node.get("aria", ""))
        text = _escape(node.get("text", ""))
        options = node.get("options", []) or []

        lines.append(f"    - {tag} [ref=e{idx}] [data-testid=\"{testid}\"]")
        if name:
            lines.append(f"      name: \"{name}\"")
        if aria:
            lines.append(f"      aria_label: \"{aria}\"")
        if text:
            lines.append(f"      text: \"{text}\"")
        if options:
            lines.append("      options:")
            for option in options:
                lines.append(f"        - \"{_escape(option)}\"")

    return "\n".join(lines)


def main() -> None:
    steps: list[tuple[str, int, int]] = []
    values: list[str] = []
    url = fixture_url()
    sync_playwright = load_playwright()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        page.goto(url, wait_until="domcontentloaded")
        snapshot_yaml = build_accessibility_yaml(page)
        payload_navigate = json.dumps(
            {
                "tool": "browser_navigate",
                "url": page.url,
                "title": page.title(),
                "snapshot_format": "yaml-like accessibility tree (simulated)",
                "snapshot_yaml": snapshot_yaml,
                "events": ["domcontentloaded", "modal-auto-opened"],
            },
            separators=(",", ":"),
        )
        add_step(steps, "browser_navigate", payload_navigate)

        page.wait_for_selector("[data-testid='new-deal-first-name-input']")
        snapshot_yaml = build_accessibility_yaml(page)
        payload_wait = json.dumps(
            {
                "tool": "browser_wait_for",
                "selector": "[data-testid='new-deal-first-name-input']",
                "snapshot_format": "yaml-like accessibility tree (simulated)",
                "snapshot_yaml": snapshot_yaml,
                "note": "simulation of MCP-style inline snapshot behavior",
            },
            separators=(",", ":"),
        )
        add_step(steps, "browser_wait_for", payload_wait)

        count = page.evaluate("() => document.querySelectorAll('[data-testid]').length")
        assert count == EXPECTED_TESTID_COUNT, (
            f"Expected {EXPECTED_TESTID_COUNT} data-testid values, got {count}"
        )
        payload_count = json.dumps(
            {"tool": "browser_evaluate", "query": "count_testids", "result": count},
            separators=(",", ":"),
        )
        add_step(steps, "browser_evaluate(count)", payload_count)

        values = page.evaluate(
            """
            () => Array.from(document.querySelectorAll("[data-testid]"))
              .map(el => el.getAttribute("data-testid"))
              .filter(Boolean)
            """
        )
        unique_sorted = sorted(set(values))
        payload_list = json.dumps(
            {
                "tool": "browser_evaluate",
                "query": "list_testids",
                "result": unique_sorted,
            },
            separators=(",", ":"),
        )
        add_step(steps, "browser_evaluate(list)", payload_list)

        browser.close()

    total_chars = sum(step[1] for step in steps)
    total_tokens = sum(step[2] for step in steps)

    print("MCP-style token usage summary (simulated)", file=sys.stderr)
    for name, char_count, token_count in steps:
        print(f"- {name}: chars={char_count}, est_tokens={token_count}", file=sys.stderr)
    print(
        f"TOTAL: chars={total_chars}, est_tokens={total_tokens} (~{CHARS_PER_TOKEN} chars/token)",
        file=sys.stderr,
    )
    print(
        "NOTE: This simulation approximates MCP-like inline accessibility snapshots; it is not a direct @playwright/mcp run.",
        file=sys.stderr,
    )

    print(json.dumps(unique_sorted, separators=(",", ":")))


if __name__ == "__main__":
    main()
