# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import json
import re
import urllib.request

from ..models import Release, ReleaseFile
from .base import Source


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "manjaro-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


class SourceForgeSource(Source):
    def __init__(self, cfg) -> None:
        super().__init__(cfg)
        self.project = self.options["project"]

    def list_releases(self, include_all: bool = False) -> list[Release]:
        if include_all:
            return self._rss_all()
        return self._best_release()

    def _best_release(self) -> list[Release]:
        url = f"https://sourceforge.net/projects/{self.project}/best_release.json"
        try:
            data = json.loads(_get(url))
        except Exception:
            return []
        rel = data.get("release") or {}
        iso = rel.get("file") or {}
        name = iso.get("name", "")
        if not name.endswith(".iso"):
            return []
        download_url = (
            f"https://sourceforge.net/projects/{self.project}/files/latest/download"
        )
        return [Release(
            source=self.name,
            release_id=f"latest/{name}",
            edition=self.project,
            category=self.category,
            version=rel.get("date", ""),
            date=rel.get("date", ""),
            is_latest=True,
            files=[ReleaseFile(
                filename=name,
                url=download_url,
                size=iso.get("bytes"),
            )],
        )]

    def _rss_all(self) -> list[Release]:
        url = f"https://sourceforge.net/projects/{self.project}/rss?path=/"
        try:
            xml = _get(url).decode("utf-8", errors="replace")
        except Exception:
            return []
        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)
        files: dict[str, str] = {}
        for item in items:
            t = re.search(r"<title>(.*?)</title>", item, re.DOTALL)
            l = re.search(r"<link>(.*?)</link>", item, re.DOTALL)
            if t and l:
                files[t.group(1).strip()] = l.group(1).strip()
        results: list[Release] = []
        for fname, dl_url in files.items():
            if not fname.endswith(".iso"):
                continue
            checksum_urls: dict[str, str] = {}
            for algo in ("sha1", "sha256", "sha512"):
                key = fname + "." + algo
                if key in files:
                    checksum_urls[algo] = files[key]
            results.append(Release(
                source=self.name,
                release_id=fname,
                edition=self.project,
                category=self.category,
                is_latest=False,
                files=[ReleaseFile(
                    filename=fname,
                    url=dl_url,
                    checksum_urls=checksum_urls,
                    sig_url=files.get(fname + ".sig"),
                )],
            ))
        return results
