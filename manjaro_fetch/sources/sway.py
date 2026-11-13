# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import re
import urllib.request
from urllib.parse import urljoin

from ..models import Release, ReleaseFile
from .base import Source


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "manjaro-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


class SwaySource(Source):
    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        self.url = self.options.get("url", "https://manjaro-sway.download/iso/")

    def list_releases(self, include_all: bool = False) -> list[Release]:
        try:
            html = _get(self.url)
        except Exception:
            return []
        folders = re.findall(r'href="(?:\./)?(\d{12})/"', html)
        if not folders:
            return []
        folders = sorted(set(folders), reverse=True)
        latest = folders[0]
        results: list[Release] = []
        for folder in folders:
            if not include_all and folder != latest:
                continue
            folder_url = urljoin(self.url, folder + "/")
            try:
                folder_html = _get(folder_url)
            except Exception:
                continue
            iso_match = re.search(r'href="([^"]+\.iso)"', folder_html)
            if not iso_match:
                continue
            iso_url = urljoin(folder_url, iso_match.group(1))
            iso_name = iso_url.rsplit("/", 1)[-1]
            results.append(Release(
                source=self.name,
                release_id=f"{folder}/{iso_name}",
                edition="sway",
                category=self.category,
                version=self._parse_version(iso_name),
                date=self._parse_date(folder),
                is_latest=(folder == latest),
                files=[ReleaseFile(
                    filename=iso_name,
                    url=iso_url,
                    checksum_urls={"sha256": urljoin(folder_url, "SHA256SUMS")},
                )],
            ))
        return results

    @staticmethod
    def _parse_version(filename: str) -> str:
        m = re.search(r"manjaro-sway-(\d+\.\d+\.\d+)", filename)
        return m.group(1) if m else ""

    @staticmethod
    def _parse_date(folder: str) -> str:
        if len(folder) >= 8:
            return f"{folder[0:4]}-{folder[4:6]}-{folder[6:8]}"
        return ""
