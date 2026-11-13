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

    def list_releases(self, force: bool = False) -> list[Release]:
        cache_key = f"github:{self.repo}:latest"
        raw = self.cached_json(cache_key, self._fetch_latest_raw, force)
        releases_raw = raw if isinstance(raw, list) else [raw]
        out: list[Release] = []
        for entry in releases_raw:
            if not entry:
                continue
            tag = entry.get("tag_name", "")
            for asset in entry.get("assets", []):
                if not asset["name"].endswith((".iso", ".img")):
                    continue
                out.append(Release(
                    source=self.name,
                    release_id=f"{tag}/{asset['name']}",
                    edition=self._guess_edition(asset["name"]),
                    category=self.category,
                    version=entry.get("name") or tag,
                    date=entry.get("published_at", ""),
                    is_latest=True,
                    notes=entry.get("body", "") or "",
                    files=[ReleaseFile(
                        filename=asset["name"],
                        url=asset["browser_download_url"],
                        size=asset.get("size"),
                    )],
                ))
        return out

    def _fetch_latest_raw(self) -> list[dict]:
        # /releases/latest may point to a tag without ISO assets (e.g. a
        # release with only source tarballs). In that case walk the list
        # and return the first release that actually contains an ISO.
        try:
            latest = _get_json(f"{API}/repos/{self.repo}/releases/latest")
            if latest and self._has_iso(latest):
                return [latest]
        except Exception:
            pass
        page = 1
        while page <= 5:
            batch = _get_json(
                f"{API}/repos/{self.repo}/releases?per_page=30&page={page}"
            )
            if not batch:
                break
            for entry in batch:
                if self._has_iso(entry):
                    return [entry]
            if len(batch) < 30:
                break
            page += 1
        return []

    @staticmethod
    def _has_iso(release: dict) -> bool:
        return any(
            a.get("name", "").endswith((".iso", ".img"))
            for a in release.get("assets", [])
        )

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