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


class ArchiveOrgSource(Source):
    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        self.identifier = self.options["identifier"]

    def list_releases(self, force: bool = False) -> list[Release]:
        cache_key = f"archive_org:{self.identifier}:latest"
        raw = self.cached_json(cache_key, self._fetch_latest_raw, force)
        if not raw or not raw.get("iso_name"):
            return []
        iso_name = raw["iso_name"]
        return [Release(
            source=self.name,
            release_id=iso_name,
            edition=self.identifier,
            category=self.category,
            is_latest=True,
            files=[ReleaseFile(
                filename=iso_name,
                url=raw["url"],
                size=raw.get("size"),
                checksum_urls=raw.get("checksums", {}),
            )],
        )]

    def _fetch_latest_raw(self) -> dict:
        url = f"https://archive.org/metadata/{self.identifier}"
        req = urllib.request.Request(url, headers={"User-Agent": "manjaro-fetch/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
        except Exception:
            return {}
        files = data.get("files", [])
        iso_files = [f for f in files if f.get("name", "").endswith(".iso")]
        if not iso_files:
            return {}
        iso_files.sort(key=lambda f: f["name"], reverse=True)
        latest = iso_files[0]
        name = latest["name"]
        by_name = {f["name"]: f for f in files}
        checksums: dict[str, str] = {}
        for algo in ("sha1", "sha256", "sha512"):
            side = name + "." + algo
            if side in by_name:
                checksums[algo] = (
                    f"https://archive.org/download/{self.identifier}/{side}"
                )
        try:
            size = int(latest.get("size", 0)) or None
        except (TypeError, ValueError):
            size = None
        return {
            "iso_name": name,
            "url": f"https://archive.org/download/{self.identifier}/{name}",
            "size": size,
            "checksums": checksums,
        }