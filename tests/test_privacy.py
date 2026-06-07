"""Privacy regression test — the enforceable privacy guarantee.

The fixtures DELIBERATELY embed prompt text, source code, and secret-looking
strings inline (as the real logs do). After a full ingest, NONE of those strings
may appear anywhere in the SQLite store. This converts the privacy claim from
documentation into something CI verifies.
"""

from __future__ import annotations

from pathlib import Path

from tokenbench.ingest import ingest
from tokenbench.storage import UsageStore

from conftest import FORBIDDEN_STRINGS


def test_no_sensitive_content_reaches_sqlite(fake_home, tmp_path):
    db = tmp_path / "store.sqlite3"
    result = ingest(home=fake_home, db_path=db)
    assert result.written > 0  # we actually ingested something to test

    with UsageStore(db) as store:
        dump = store.dump_text()

    for forbidden in FORBIDDEN_STRINGS:
        assert forbidden not in dump, f"LEAK: {forbidden!r} reached the SQLite store"


def test_raw_db_bytes_contain_no_secrets(fake_home, tmp_path):
    """Belt-and-suspenders: scan the raw database file bytes, not just queried rows."""
    db = tmp_path / "store.sqlite3"
    ingest(home=fake_home, db_path=db)
    raw = Path(db).read_bytes()
    for forbidden in FORBIDDEN_STRINGS:
        assert forbidden.encode("utf-8") not in raw, f"LEAK in db bytes: {forbidden!r}"


def test_persisted_fields_are_whitelisted():
    from tokenbench.schema import PERSISTED_FIELDS

    # The persisted set must not include any content-bearing field.
    forbidden_columns = {"content", "items", "message", "prompt", "response", "text"}
    assert forbidden_columns.isdisjoint(set(PERSISTED_FIELDS))
