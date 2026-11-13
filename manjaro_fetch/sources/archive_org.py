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

    def list_releases(self, include_all: bool = False) -> list[Release]:
        url = f"https://archive.org/metadata/{self.identifier}"
        req = urllib.request.Request(url, headers={"User-Agent": "manjaro-fetch/0.1"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.load(resp)
        files = data.get("files", [])
        iso_files = [f for f in files if f.get("name", "").endswith(".iso")]
        if not iso_files:
            return []
        iso_files.sort(key=lambda f: f["name"], reverse=True)
        if not include_all:
            iso_files = iso_files[:1]
        by_name = {f["name"]: f for f in files}
        results: list[Release] = []
        for i, f in enumerate(iso_files):
            name = f["name"]
            checksum_urls: dict[str, str] = {}
            for algo in ("sha1", "sha256", "sha512"):
                side = name + "." + algo
                if side in by_name:
                    checksum_urls[algo] = (
                        f"https://archive.org/download/{self.identifier}/{side}"
                    )
            size = None
            try:
                size = int(f.get("size", 0)) or None
            except (TypeError, ValueError):
                size = None
            results.append(Release(
                source=self.name,
                release_id=name,
                edition=self.identifier,
                category=self.category,
                is_latest=(i == 0),
                files=[ReleaseFile(
                    filename=name,
                    url=f"https://archive.org/download/{self.identifier}/{name}",
                    size=size,
                    checksum_urls=checksum_urls,
                )],
            ))
        return results
