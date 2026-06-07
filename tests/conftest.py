"""Shared test helpers: build a fake home directory laid out like the real one."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# Strings deliberately embedded in the fixtures that must NEVER reach SQLite.
FORBIDDEN_STRINGS = [
    "SECRET_PROMPT_TEXT_alpha",
    "my_secret_function",
    "sk-LEAKME-111",
    "SECRET_RESPONSE_TEXT_beta",
    "hunter2",
    "class Foo",
    "SECRET_USER_PROMPT_gamma",
    "SECRET_CODEX_PROMPT_delta",
    "ghp_LEAKME222",
    "SECRET_CODEX_CODE_epsilon",
    "AWS_SECRET_ACCESS_KEY",
    "SECRET_CODEX_RESPONSE_zeta",
]


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    """A temp home with Claude + Codex logs mirroring the real on-disk layout."""
    # Claude: ~/.claude/projects/<encoded-cwd>/<session>.jsonl
    claude_dir = tmp_path / ".claude" / "projects" / "-Users-jack-projects-demo"
    claude_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "claude_session.jsonl", claude_dir / "claude-sess-1.jsonl")

    # Codex: ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
    codex_dir = tmp_path / ".codex" / "sessions" / "2026" / "06" / "02"
    codex_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "codex_rollout.jsonl", codex_dir / "rollout-codex-sess-1.jsonl")

    # A decoy file that must be ignored (history has no token usage).
    (tmp_path / ".codex" / "history.jsonl").write_text(
        '{"session_id":"x","ts":1,"text":"SECRET_PROMPT_TEXT_alpha should be ignored"}\n'
    )
    return tmp_path


@pytest.fixture
def empty_home(tmp_path: Path) -> Path:
    """A temp home with no provider logs at all."""
    return tmp_path
