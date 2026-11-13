# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import json
import urllib.request

from ..models import Release, ReleaseFile
from .base import Source


def _get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "manjaro-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


class SourceForgeSource(Source):
    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        self.project = self.options["project"]

    def list_releases(self, force: bool = False) -> list[Release]:
        cache_key = f"sourceforge:{self.project}:latest"
        raw = self.cached_json(cache_key, self._fetch_latest_raw, force)
        if not raw or not raw.get("name"):
            return []
        name = raw["name"]
        if not name.endswith(".iso"):
            return []
        return [Release(
            source=self.name,
            release_id=f"latest/{name}",
            edition=self.project,
            category=self.category,
            version=raw.get("date", ""),
            date=raw.get("date", ""),
            is_latest=True,
            files=[ReleaseFile(
                filename=name,
                url=(
                    f"https://sourceforge.net/projects/{self.project}/"
                    f"files/latest/download"
                ),
                size=raw.get("bytes"),
            )],
        )]

    def _fetch_latest_raw(self) -> dict:
        url = f"https://sourceforge.net/projects/{self.project}/best_release.json"
        try:
            data = json.loads(_get_bytes(url))
        except Exception:
            return {}
        rel = data.get("release") or {}
        iso = rel.get("file") or {}
        return {
            "name": iso.get("name", ""),
            "bytes": iso.get("bytes"),
            "date": rel.get("date", ""),
        }