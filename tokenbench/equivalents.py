"""Fermi 'scale equivalents' that translate raw token burn into relatable quantities.

These are deliberately rough order-of-magnitude translations — NOT measured utility,
billing, or environmental accounting. Following Nate Jones' framing, they exist to
make a huge token number feel like *something*, with every basis constant documented
so the math is auditable. Pure, offline, deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass

# One "query-equivalent" is a notional 1,000-token interaction. All factors below are
# expressed per query-equivalent and are intentionally approximate.
TOKENS_PER_QUERY_EQUIV = 1_000

# Documented basis constants (rough public estimates; adjust deliberately).
WATER_GAL_PER_QUERY = 0.000085          # gallons of water per query-equivalent
ELECTRICITY_WH_PER_QUERY = 0.34          # watt-hours per query-equivalent
TOKENS_PER_LOC = 15                      # tokens per line of code (generation proxy)
LOC_PER_ENGINEER_YEAR = 10_000           # net lines/engineer-year

# Human-relatable conversion anchors.
GAL_PER_SHOWER = 17.0                    # ~17 gal for a typical shower
KWH_PER_MOVIE = 0.45                     # ~0.45 kWh to stream a 2h movie

CAVEAT = (
    "Scale translations, not measured utility, billing, or environmental accounting."
)


@dataclass(frozen=True)
class Equivalent:
    measure: str
    estimate: str
    equivalent: str
    basis: str


def _fmt_int(n: float) -> str:
    return f"{round(n):,}"


def scale_equivalents(total_tokens: int) -> list[Equivalent]:
    """Return order-of-magnitude equivalents for ``total_tokens`` (offline)."""
    if total_tokens <= 0:
        return []
    qe = total_tokens / TOKENS_PER_QUERY_EQUIV

    water_gal = qe * WATER_GAL_PER_QUERY
    elec_kwh = qe * ELECTRICITY_WH_PER_QUERY / 1000.0
    loc = total_tokens / TOKENS_PER_LOC
    eng_years = loc / LOC_PER_ENGINEER_YEAR

    return [
        Equivalent(
            measure="Water",
            estimate=f"{_fmt_int(water_gal)} gal",
            equivalent=f"~{_fmt_int(water_gal / GAL_PER_SHOWER)} showers",
            basis=f"{WATER_GAL_PER_QUERY} gal/query-equiv; "
            f"1,000 tokens/query-equiv; {GAL_PER_SHOWER} gal/shower",
        ),
        Equivalent(
            measure="Electricity",
            estimate=f"{_fmt_int(elec_kwh)} kWh",
            equivalent=f"~{_fmt_int(elec_kwh / KWH_PER_MOVIE)} streamed movies",
            basis=f"{ELECTRICITY_WH_PER_QUERY} Wh/query-equiv; "
            f"{KWH_PER_MOVIE} kWh per 2h movie",
        ),
        Equivalent(
            measure="Code volume",
            estimate=f"{_fmt_int(loc)} LOC",
            equivalent=f"~{_fmt_int(eng_years)} engineer-years",
            basis=f"{TOKENS_PER_LOC} tokens/LOC; "
            f"{LOC_PER_ENGINEER_YEAR:,} net LOC/engineer-year",
        ),
    ]


def as_dicts(total_tokens: int) -> list[dict]:
    return [e.__dict__ for e in scale_equivalents(total_tokens)]
