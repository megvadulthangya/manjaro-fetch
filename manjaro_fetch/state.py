# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import data_dir

SCHEMA = """
CREATE TABLE IF NOT EXISTS downloaded (
    release_key TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    edition TEXT,
    filename TEXT,
    sha256 TEXT,
    size INTEGER,
    downloaded_at TEXT NOT NULL,
    present INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS cache (
    cache_key TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
"""


def _db_path() -> Path:
    return data_dir() / "state.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(_connect()) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


# ---------------------------------------------------------------------------
# Downloaded releases
# ---------------------------------------------------------------------------

def mark_downloaded(
    release_key: str,
    source: str,
    edition: str,
    filename: str,
    sha256: Optional[str],
    size: Optional[int],
) -> None:
    init_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_connect()) as conn:
        conn.execute(
            """
            INSERT INTO downloaded
                (release_key, source, edition, filename, sha256, size, downloaded_at, present)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(release_key) DO UPDATE SET
                filename = excluded.filename,
                sha256 = excluded.sha256,
                size = excluded.size,
                downloaded_at = excluded.downloaded_at,
                present = 1
            """,
            (release_key, source, edition, filename, sha256, size, now),
        )
        conn.commit()


def is_downloaded(release_key: str) -> bool:
    init_db()
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT present FROM downloaded WHERE release_key = ?", (release_key,)
        ).fetchone()
    return bool(row and row["present"])


def get_downloaded(release_key: str) -> Optional[dict]:
    init_db()
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM downloaded WHERE release_key = ?", (release_key,)
        ).fetchone()
    return dict(row) if row else None


def list_downloaded() -> list[dict]:
    init_db()
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT * FROM downloaded ORDER BY downloaded_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def refresh_presence(download_dir: Path) -> None:
    init_db()
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT release_key, filename FROM downloaded"
        ).fetchall()
        for row in rows:
            fname = row["filename"]
            present = int(bool(fname) and (download_dir / fname).is_file())
            conn.execute(
                "UPDATE downloaded SET present = ? WHERE release_key = ?",
                (present, row["release_key"]),
            )
        conn.commit()


def forget_downloaded(release_key: str) -> None:
    init_db()
    with closing(_connect()) as conn:
        conn.execute("DELETE FROM downloaded WHERE release_key = ?", (release_key,))
        conn.commit()


# ---------------------------------------------------------------------------
# Source cache: stores raw source payloads, keyed by source + scope.
# No TTL: cached data is served until the user explicitly refreshes.
# ---------------------------------------------------------------------------

def get_cached(cache_key: str) -> Optional[str]:
    init_db()
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT payload FROM cache WHERE cache_key = ?", (cache_key,)
        ).fetchone()
    return row["payload"] if row else None


def set_cached(cache_key: str, payload: str) -> None:
    init_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_connect()) as conn:
        conn.execute(
            """
            INSERT INTO cache (cache_key, payload, fetched_at)
            VALUES (?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                payload = excluded.payload,
                fetched_at = excluded.fetched_at
            """,
            (cache_key, payload, now),
        )
        conn.commit()


def clear_cache(prefix: Optional[str] = None) -> None:
    init_db()
    with closing(_connect()) as conn:
        if prefix:
            conn.execute(
                "DELETE FROM cache WHERE cache_key LIKE ?", (prefix + "%",)
            )
        else:
            conn.execute("DELETE FROM cache")
        conn.commit()


def cache_metadata() -> dict:
    init_db()
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, MAX(fetched_at) AS last FROM cache"
        ).fetchone()
    return {"count": row["n"], "last_refreshed": row["last"]}


def seed_from_file(path: Path) -> int:
    """Load a seed cache file into the DB.

    Format: {"<cache_key>": {"payload": "<json string>", "fetched_at": "<iso8601>"}, ...}
    Existing entries are kept; only missing keys are inserted.
    """
    if not path.is_file():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    init_db()
    count = 0
    with closing(_connect()) as conn:
        for key, entry in data.items():
            if not isinstance(entry, dict):
                continue
            payload = entry.get("payload", "")
            fetched_at = entry.get("fetched_at", "")
            if not payload:
                continue
            if not isinstance(payload, str):
                payload = json.dumps(payload)
            conn.execute(
                """
                INSERT INTO cache (cache_key, payload, fetched_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO NOTHING
                """,
                (key, payload, fetched_at),
            )
            count += 1
        conn.commit()
    return count


def seed_from_bundled() -> int:
    here = Path(__file__).resolve().parent
    return seed_from_file(here / "seed_cache.json")