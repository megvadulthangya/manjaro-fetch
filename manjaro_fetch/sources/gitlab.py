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


class GitLabSource(Source):
    """Legacy source reading file-info.json from gitlab.manjaro.org.

    NOTE: gitlab.manjaro.org currently returns HTTP 502 (server-side outage).
    Manjaro is migrating to code.manjaro.org (Forgejo). This source is kept
    so that if the endpoint comes back, behaviour is preserved. Replace it
    with a Forgejo API or a maintained manifest once one is confirmed.
    """

    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        self.url = self.options["url"]

    def list_releases(self, include_all: bool = False) -> list[Release]:
        req = urllib.request.Request(
            self.url, headers={"User-Agent": "manjaro-fetch/0.1"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
        except Exception:
            return []
        releases: list[Release] = []
        for entry in data.get("image", []):
            url = entry.get("download", "")
            if not url.startswith("https://download.manjaro.org/"):
                continue
            filename = url.rsplit("/", 1)[-1]
            if not filename.endswith(".iso"):
                continue
            releases.append(Release(
                source=self.name,
                release_id=filename,
                edition=self._edition_from_path(url),
                category=self.category,
                version=entry.get("version", ""),
                date=entry.get("date", ""),
                is_latest=True,
                files=[ReleaseFile(
                    filename=filename,
                    url=url,
                    checksum_urls={
                        "sha1": url + ".sha1",
                        "sha256": url + ".sha256",
                    },
                    sig_url=url + ".sig",
                )],
            ))
        return releases

    @staticmethod
    def _edition_from_path(url: str) -> str:
        for edition in ("xfce", "gnome", "kde", "cinnamon", "i3", "sway"):
            if f"/{edition}/" in url:
                return edition
        return "unknown"
