# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import os
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

APP_NAME = "manjaro-fetch"


@dataclass
class SourceConfig:
    name: str
    type: str
    category: str = "extras"
    enabled: bool = True
    options: dict[str, Any] = field(default_factory=dict)


def user_config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / APP_NAME


def data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    p = Path(base) / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def default_download_dir() -> Path:
    return Path(os.path.expanduser("~/Manjaro-ISO"))


def _bundled_sources_path() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here / "default_sources.toml",
        here.parent / "config" / "sources.toml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "bundled sources.toml not found (searched: "
        + ", ".join(str(c) for c in candidates) + ")"
    )


def _read_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def load_source_configs() -> list[SourceConfig]:
    from .sources import source_types

    known = source_types()
    merged: dict[str, SourceConfig] = {}

    paths: list[Path] = [_bundled_sources_path()]
    user = user_config_dir() / "sources.toml"
    if user.is_file():
        paths.append(user)

    for path in paths:
        data = _read_toml(path)
        for entry in data.get("source", []):
            name = entry.get("name")
            if not name:
                continue
            stype = entry.get("type", "")
            if stype not in known:
                print(
                    f"warning: skipping source '{name}': unknown type '{stype}'",
                    file=sys.stderr,
                )
                continue
            options = {
                k: v
                for k, v in entry.items()
                if k not in ("name", "type", "category", "enabled")
            }
            merged[name] = SourceConfig(
                name=name,
                type=stype,
                category=entry.get("category", "extras"),
                enabled=bool(entry.get("enabled", True)),
                options=options,
            )

    return list(merged.values())


def instantiate_sources(only_enabled: bool = True) -> list:
    from .sources import source_types

    known = source_types()
    result = []
    for cfg in load_source_configs():
        if only_enabled and not cfg.enabled:
            continue
        cls = known.get(cfg.type)
        if cls is None:
            continue
        try:
            result.append(cls(cfg))
        except Exception as exc:
            print(
                f"warning: failed to initialise source '{cfg.name}': {exc}",
                file=sys.stderr,
            )
    return result
