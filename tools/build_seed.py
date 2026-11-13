#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
"""Generate manjaro_fetch/seed_cache.json.

Usage (from the repo root, after `pip install .` into a venv or with the
package importable via PYTHONPATH):

    python tools/build_seed.py > manjaro_fetch/seed_cache.json

This fetches the latest release from every configured source with
force=True and dumps the raw cache payloads. The installer loads the
resulting file into the SQLite cache so a fresh install has an
out-of-box list without hitting the network.
"""
from __future__ import annotations
import json
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    import manjaro_fetch.sources  # noqa: F401
    from manjaro_fetch.config import instantiate_sources
    from manjaro_fetch.state import _connect

    sources = instantiate_sources(only_enabled=True)
    for src in sources:
        try:
            src.list_releases(force=True)
        except Exception as exc:
            print(f"warning: {src.name}: {exc}", file=sys.stderr)
        finally:
            src.close()

    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT cache_key, payload, fetched_at FROM cache"
        ).fetchall()

    out = {
        row["cache_key"]: {
            "payload": row["payload"],
            "fetched_at": row["fetched_at"],
        }
        for row in rows
    }
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())