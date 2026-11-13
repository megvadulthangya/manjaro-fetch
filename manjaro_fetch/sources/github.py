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

API = "https://api.github.com"


def _get_json(url: str) -> object:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "manjaro-fetch/0.1",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


class GitHubSource(Source):
    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        self.repo = self.options["repo"]

    def list_releases(self, include_all: bool = False) -> list[Release]:
        releases_raw = self._fetch_all() if include_all else self._fetch_latest()
        out: list[Release] = []
        latest_tag = releases_raw[0]["tag_name"] if releases_raw else None
        for raw in releases_raw:
            for asset in raw.get("assets", []):
                if not asset["name"].endswith((".iso", ".img")):
                    continue
                edition = self._guess_edition(asset["name"])
                out.append(Release(
                    source=self.name,
                    release_id=f"{raw['tag_name']}/{asset['name']}",
                    edition=edition,
                    category=self.category,
                    version=raw.get("name") or raw["tag_name"],
                    date=raw.get("published_at", ""),
                    is_latest=(raw["tag_name"] == latest_tag),
                    notes=raw.get("body", "") or "",
                    files=[ReleaseFile(
                        filename=asset["name"],
                        url=asset["browser_download_url"],
                        size=asset.get("size"),
                    )],
                ))
        return out

    def _fetch_latest(self) -> list[dict]:
        return [_get_json(f"{API}/repos/{self.repo}/releases/latest")]

    def _fetch_all(self) -> list[dict]:
        results: list[dict] = []
        page = 1
        while True:
            batch = _get_json(
                f"{API}/repos/{self.repo}/releases?per_page=100&page={page}"
            )
            if not batch:
                break
            results.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return results

    @staticmethod
    def _guess_edition(filename: str) -> str:
        name = filename.lower()
        for edition in (
            "xfce", "gnome", "plasma", "kde", "cinnamon",
            "i3", "sway", "mate", "awesome", "lxqt", "openbox",
        ):
            if edition in name:
                return edition
        return "unknown"
