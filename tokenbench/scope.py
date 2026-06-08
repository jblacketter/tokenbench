"""Project scoping for the dashboard — a read-side filter, nothing more.

Every stored event already carries a ``project_path``: Claude decodes it from the
encoded ``~/.claude/projects/<encoded-cwd>`` directory, and Codex reads the session
``cwd`` from its ``session_meta`` header. So scoping the dashboard to a single
project means keeping only the events whose path *is* that project or sits *under*
it — no schema change, no re-ingestion, no new data read or stored.

Match semantics are best-effort and mirror ``decode_claude_project_dir``'s caveat:
paths are compared after ``expanduser`` + absolute normalization, and a sibling that
merely shares a name prefix (``/a/foo-bar`` vs ``/a/foo``) is **not** a match — only
the exact path or a true subdirectory (``/a/foo/x``) qualifies.
"""

from __future__ import annotations

import os
from typing import Optional


def normalize_project_path(path: Optional[str]) -> Optional[str]:
    """Canonicalize a target project path, or ``None`` for the machine-wide view.

    ``None``/empty/whitespace all mean "no scope". Everything else is expanded
    (``~``) and made absolute (a relative path resolves against the current working
    directory — the natural "scope to this repo" case for a pip-installed dependency).
    """
    if path is None:
        return None
    s = str(path).strip()
    if not s:
        return None
    return os.path.abspath(os.path.expanduser(s))


def event_in_project(event_path: Optional[str], target: Optional[str]) -> bool:
    """Does an event's ``project_path`` belong to the scoped ``target`` project?

    ``target`` falsy → no scope (machine-wide): every event matches. With a target
    set, an event matches only if its normalized path equals the target or is a true
    subdirectory of it, so ``/a/foo`` never captures sibling ``/a/foo-bar``.
    """
    if not target:
        return True
    if not event_path:
        return False
    s = str(event_path).strip()
    if not s:
        return False
    ep = os.path.abspath(os.path.expanduser(s))
    return ep == target or ep.startswith(target + os.sep)
