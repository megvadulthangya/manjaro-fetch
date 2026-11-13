# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

from ..state import get_cached, set_cached

if TYPE_CHECKING:
    from ..config import SourceConfig
    from ..models import Release


class Source(ABC):
    name: str
    category: str
    options: dict

    def __init__(self, cfg: "SourceConfig") -> None:
        self.name = cfg.name
        self.category = cfg.category
        self.options = dict(cfg.options)

    @abstractmethod
    def list_releases(self, force: bool = False) -> list["Release"]:
        ...

    def close(self) -> None:
        return None

    # -- cache helpers ------------------------------------------------------

    def cached_json(self, key: str, fetch_fn: Callable[[], object], force: bool) -> object:
        if not force:
            cached = get_cached(key)
            if cached is not None:
                return json.loads(cached)
        data = fetch_fn()
        set_cached(key, json.dumps(data))
        return data

    def cached_text(self, key: str, fetch_fn: Callable[[], str], force: bool) -> str:
        if not force:
            cached = get_cached(key)
            if cached is not None:
                return cached
        data = fetch_fn()
        set_cached(key, data)
        return data