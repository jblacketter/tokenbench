"""Privacy-safe work-family classification of token burn.

Nate Jones' "burn drivers" view classifies usage from session *prompts*. tokenbench
never stores prompts, so we classify from the **project path only** — a documented,
deterministic ruleset. This module reads nothing but the path string; it has no
access to (and never inspects) prompt/response/code content.

Rules are evaluated in order and the FIRST matching family wins, so order is
significant — keep the more specific families above the broader ones. Anything that
matches no rule is explicitly ``Other / mixed`` rather than guessed.
"""

from __future__ import annotations

from typing import Optional

OTHER_FAMILY = "Other / mixed"

# Ordered (family, keywords). First family with any keyword found in the lowercased
# project path wins. Order matters — specific before broad.
WORK_FAMILY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("QA & test automation", ("test", "qa", "automation", "e2e", "playwright", "selenium", "cypress")),
    ("Writing & content", ("article", "blog", "/docs", "content", "linkedin", "writing", "video")),
    ("Data & ML", ("dataset", "/ml", "ml-", "-ml", "analytics", "etl", "notebook", "model")),
    ("Infra & tooling", ("infra", "ops", "deploy", "tooling", "/cli", "config", "script", "agent")),
    ("Web & app", ("web", "frontend", "/ui", "site", "dashboard", "app", "grid", "client", "portal")),
)


def classify_project(path: Optional[str]) -> str:
    """Map a project path to a work family using path text only.

    Empty/unknown paths and paths matching no rule return ``Other / mixed``.
    """
    if not path or path == "unknown":
        return OTHER_FAMILY
    p = path.lower()
    for family, keywords in WORK_FAMILY_RULES:
        if any(k in p for k in keywords):
            return family
    return OTHER_FAMILY


def family_names() -> list[str]:
    """All families a path can be classified into (for docs/tests)."""
    return [family for family, _ in WORK_FAMILY_RULES] + [OTHER_FAMILY]
