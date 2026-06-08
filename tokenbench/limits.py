"""Configurable limits and (optional) offline cost-equivalent tables.

Claude Code logs carry no native rate-limit data, so the Claude side of the limits
view is a *configurable budget* the user can set per rolling window; usage is
compared against it and always labeled an estimate. Codex limits, by contrast, come
straight from the logs (see ``parsers.parse_codex_rate_limits``).

Pricing here is a static, offline table used only for an optional API-equivalent
value figure — it is NOT subscription cost and never triggers a network call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ClaudeBudget:
    """Optional, user-set token budgets for Claude rolling windows.

    Defaults are ``None`` (unconfigured) — the dashboard then shows a clear
    "no native limit data — configure to enable" state rather than a fake number.
    """

    five_hour_tokens: Optional[int] = None
    weekly_tokens: Optional[int] = None


# Default: unconfigured. Users can construct their own ClaudeBudget and pass it in.
DEFAULT_CLAUDE_BUDGET = ClaudeBudget()


# Static, offline, approximate per-model pricing for an *API-equivalent* value only
# (USD per 1M tokens, input/output). Subscription usage has no per-token cost; this
# answers "what would this have cost on metered API pricing?". Unknown models fall
# back to a generic rate. Update deliberately; never fetched over the network.
PRICING_USD_PER_MTOK = {
    "claude-opus": {"input": 15.0, "output": 75.0},
    "claude-sonnet": {"input": 3.0, "output": 15.0},
    "claude-haiku": {"input": 0.80, "output": 4.0},
    "gpt-5": {"input": 1.25, "output": 10.0},
    "gpt-5-codex": {"input": 1.25, "output": 10.0},
    "_default": {"input": 2.0, "output": 8.0},
}


def _price_for_model(model: Optional[str]) -> dict[str, float]:
    if not model:
        return PRICING_USD_PER_MTOK["_default"]
    m = model.lower()
    for key, price in PRICING_USD_PER_MTOK.items():
        if key != "_default" and key in m:
            return price
    return PRICING_USD_PER_MTOK["_default"]


def api_equivalent_usd(rows: list[dict]) -> float:
    """Approximate metered-API cost of the given usage rows (offline, illustrative).

    Cache-read tokens are billed far cheaper than fresh input on real APIs; we apply a
    coarse 0.1× factor to cache reads and price reasoning tokens as output.
    """
    total = 0.0
    for r in rows:
        price = _price_for_model(r.get("model"))
        fresh_input = r.get("input_tokens", 0)
        cache_read = r.get("cache_read_tokens", 0)
        cache_write = r.get("cache_write_tokens", 0)
        output = r.get("output_tokens", 0) + r.get("reasoning_output_tokens", 0)
        input_cost = (fresh_input + cache_write) * price["input"] / 1_000_000
        cache_cost = cache_read * price["input"] * 0.1 / 1_000_000
        output_cost = output * price["output"] / 1_000_000
        total += input_cost + cache_cost + output_cost
    return round(total, 2)
