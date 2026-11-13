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
from typing import Callable, Optional

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

    def list_releases(
        self,
        force: bool = False,
        include_all: bool = False,
        cancel: Optional[Callable[[], bool]] = None,
    ) -> list[Release]:
        if include_all:
            return self._list_all(force=force, cancel=cancel)
        return self._list_latest(force=force)

    # -- latest only --------------------------------------------------------

    def _list_latest(self, force: bool = False) -> list[Release]:
        cache_key = f"github:{self.repo}:latest"
        raw = self.cached_json(cache_key, self._fetch_latest_raw, force)
        if not raw:
            return []
        return self._release_from_entry(raw[0] if isinstance(raw, list) else raw)

    def _fetch_latest_raw(self) -> list[dict]:
        # Walk releases newest-first and return the first one that
        # actually contains an ISO asset. GitHub returns releases in
        # reverse chronological order, so the first match is the newest.
        page = 1
        while page <= 10:
            batch = _get_json(
                f"{API}/repos/{self.repo}/releases?per_page=100&page={page}"
            )
            if not batch:
                break
            for entry in batch:
                if self._has_iso(entry):
                    return [entry]
            if len(batch) < 100:
                break
            page += 1
        return []

    # -- all releases (paged, cancellable) ---------------------------------

    def _list_all(
        self, force: bool = False, cancel: Optional[Callable[[], bool]] = None
    ) -> list[Release]:
        cache_key = f"github:{self.repo}:all"
        raw = self.cached_json(cache_key, self._fetch_all_raw, force)
        if not isinstance(raw, list):
            return []
        out: list[Release] = []
        for entry in raw:
            if cancel and cancel():
                break
            out.extend(self._release_from_entry(entry))
        return out

    def _fetch_all_raw(self) -> list[dict]:
        results: list[dict] = []
        page = 1
        while page <= 20:  # hard cap: 2000 releases
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

    # -- helpers ------------------------------------------------------------

    def _release_from_entry(self, entry: dict) -> list[Release]:
        tag = entry.get("tag_name", "")
        out: list[Release] = []
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
                is_latest=False,
                notes=entry.get("body", "") or "",
                files=[ReleaseFile(
                    filename=asset["name"],
                    url=asset["browser_download_url"],
                    size=asset.get("size"),
                )],
            ))
        return out

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