# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Source


def source_types() -> dict[str, type["Source"]]:
    from .archive_org import ArchiveOrgSource
    from .github import GitHubSource
    from .gitlab import GitLabSource
    from .sourceforge import SourceForgeSource
    from .sway import SwaySource

    return {
        "github": GitHubSource,
        "sourceforge": SourceForgeSource,
        "archive_org": ArchiveOrgSource,
        "sway_html": SwaySource,
        "gitlab": GitLabSource,
    }


def load_releases(include_all: bool = False, include_extras: bool = False) -> list:
    """Collect releases from all enabled sources.

    Sources in category 'extras' are skipped unless include_extras is True.
    """
    import sys
    from ..config import instantiate_sources

    sources = instantiate_sources(only_enabled=True)
    results: list = []
    for src in sources:
        if src.category == "extras" and not include_extras:
            continue
        try:
            results.extend(src.list_releases(include_all=include_all))
        except Exception as exc:
            print(f"warning: source '{src.name}' failed: {exc}", file=sys.stderr)
        finally:
            src.close()
    return results
