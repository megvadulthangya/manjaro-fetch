# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
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
