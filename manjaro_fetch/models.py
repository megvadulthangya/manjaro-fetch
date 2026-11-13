# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ReleaseFile:
    filename: str
    url: str
    size: Optional[int] = None
    checksums: dict[str, str] = field(default_factory=dict)
    checksum_urls: dict[str, str] = field(default_factory=dict)
    sig_url: Optional[str] = None


@dataclass
class Release:
    source: str
    release_id: str
    edition: str
    category: str = "extras"
    version: str = ""
    date: str = ""
    is_latest: bool = False
    notes: str = ""
    files: list[ReleaseFile] = field(default_factory=list)

    @property
    def primary_file(self) -> Optional[ReleaseFile]:
        for f in self.files:
            if f.filename.endswith(".iso"):
                return f
        return self.files[0] if self.files else None


def release_key(release: Release) -> str:
    return f"{release.source}:{release.release_id}"
