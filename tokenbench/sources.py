"""Discovery of local subscription-account usage logs.

Confirmed sources (see docs/phases/standalone-dashboard-mvp.md):
  - Claude Code: ``~/.claude/projects/<encoded-cwd>/<session-uuid>.jsonl``
  - Codex:       ``~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl``

We deliberately do NOT touch ``~/.codex/history.jsonl`` — it carries session text
but no token usage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SourceDiscovery:
    """What we found on disk for one provider."""

    provider: str
    root: Path
    available: bool
    files: list[Path] = field(default_factory=list)

    @property
    def file_count(self) -> int:
        return len(self.files)


def _claude_root(home: Path) -> Path:
    return home / ".claude" / "projects"


def _codex_root(home: Path) -> Path:
    return home / ".codex" / "sessions"


def discover_claude(home: Path | None = None) -> SourceDiscovery:
    home = home or Path.home()
    root = _claude_root(home)
    files: list[Path] = []
    if root.is_dir():
        files = sorted(root.glob("*/*.jsonl"))
    return SourceDiscovery(
        provider="claude", root=root, available=root.is_dir(), files=files
    )


def discover_codex(home: Path | None = None) -> SourceDiscovery:
    home = home or Path.home()
    root = _codex_root(home)
    files: list[Path] = []
    if root.is_dir():
        # YYYY/MM/DD/rollout-*.jsonl
        files = sorted(root.glob("*/*/*/rollout-*.jsonl"))
    return SourceDiscovery(
        provider="codex", root=root, available=root.is_dir(), files=files
    )


def discover_all(home: Path | None = None) -> list[SourceDiscovery]:
    return [discover_claude(home), discover_codex(home)]


def decode_claude_project_dir(encoded: str) -> str:
    """Recover a filesystem path from a Claude Code encoded project directory.

    ``-Users-jack-projects-foo`` -> ``/Users/jack/projects/foo``.

    This is best-effort: directory names that themselves contain dashes are
    ambiguous, but the leading-dash + dash-as-separator convention round-trips the
    common case. We keep the encoded form in metadata so nothing is lost.
    """
    if not encoded:
        return ""
    if encoded.startswith("-"):
        return "/" + encoded[1:].replace("-", "/")
    return encoded.replace("-", "/")
