"""SQLite storage for normalized usage events.

The store only ever writes the whitelisted columns in ``PERSISTED_FIELDS``. The
``metadata`` dict is JSON-encoded but, by construction, parsers put only small
non-sensitive hints there. The privacy regression test asserts that no prompt,
response, code, or secret text from the raw logs reaches this database.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, Optional

from .schema import UsageEvent

DEFAULT_DB_PATH = Path("data/tokenbench.sqlite3")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS usage_events (
    id                      TEXT PRIMARY KEY,
    provider                TEXT NOT NULL,
    source                  TEXT NOT NULL,
    model                   TEXT,
    timestamp               TEXT NOT NULL,
    project_path            TEXT,
    session_id              TEXT NOT NULL,
    input_tokens            INTEGER NOT NULL DEFAULT 0,
    output_tokens           INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens       INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens      INTEGER NOT NULL DEFAULT 0,
    reasoning_output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens            INTEGER NOT NULL DEFAULT 0,
    metadata                TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_provider ON usage_events(provider);
CREATE INDEX IF NOT EXISTS idx_usage_session ON usage_events(session_id);
"""


class UsageStore:
    """A thin, whitelisted SQLite wrapper for usage events."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        if self.db_path.parent and str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def __enter__(self) -> "UsageStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def upsert_events(self, events: Iterable[UsageEvent]) -> int:
        """Insert or replace events by id. Returns the number written.

        Only the whitelisted persisted columns are bound — there is no code path
        here that can write raw log content.
        """
        rows = []
        for ev in events:
            d = ev.as_persisted_dict()
            d["metadata"] = json.dumps(d.get("metadata") or {}, sort_keys=True)
            rows.append(d)
        if not rows:
            return 0
        cols = list(rows[0].keys())
        placeholders = ", ".join(f":{c}" for c in cols)
        sql = (
            f"INSERT OR REPLACE INTO usage_events ({', '.join(cols)}) "
            f"VALUES ({placeholders})"
        )
        self.conn.executemany(sql, rows)
        self.conn.commit()
        return len(rows)

    def all_events(self) -> list[sqlite3.Row]:
        cur = self.conn.execute("SELECT * FROM usage_events ORDER BY timestamp")
        return cur.fetchall()

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM usage_events").fetchone()[0]

    def dump_text(self) -> str:
        """Return every stored value as one big string.

        Used by the privacy regression test to scan for forbidden substrings.
        """
        parts: list[str] = []
        for row in self.all_events():
            for key in row.keys():
                parts.append(str(row[key]))
        return "\n".join(parts)

    def close(self) -> None:
        self.conn.close()
