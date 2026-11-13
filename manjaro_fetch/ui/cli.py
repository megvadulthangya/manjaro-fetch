# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

from ..config import default_download_dir
from ..downloader import download_release
from ..models import release_key
from ..sources import load_releases
from ..state import cache_metadata, list_downloaded, refresh_presence


def _format_size(size: int | None) -> str:
    if not size:
        return "?"
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _print_table(releases: list) -> None:
    if not releases:
        print("No releases found.")
        return
    print(f"{'KEY':<70} {'EDITION':<12} {'CATEGORY':<10} SIZE")
    print("-" * 108)
    for rel in releases:
        pf = rel.primary_file
        size = _format_size(pf.size) if pf else "?"
        print(
            f"{release_key(rel):<70} {rel.edition:<12} "
            f"{rel.category:<10} {size}"
        )


def cmd_list(args: argparse.Namespace) -> int:
    releases = load_releases(
        include_extras=args.extras, force=args.refresh
    )
    if args.source:
        releases = [r for r in releases if r.source == args.source]
    if args.category:
        releases = [r for r in releases if r.category == args.category]
    if not args.refresh:
        meta = cache_metadata()
        if meta["count"] == 0:
            print(
                "No releases cached. Run 'manjaro-fetch list --refresh' "
                "to fetch from network.",
                file=sys.stderr,
            )
            return 1
    if args.json:
        print(json.dumps([
            {
                "key": release_key(r),
                "source": r.source,
                "edition": r.edition,
                "category": r.category,
                "version": r.version,
                "date": r.date,
                "is_latest": r.is_latest,
                "files": [
                    {
                        "filename": f.filename,
                        "url": f.url,
                        "size": f.size,
                        "checksums": f.checksums,
                    }
                    for f in r.files
                ],
            }
            for r in releases
        ], indent=2))
    else:
        _print_table(releases)
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    releases = load_releases(include_extras=True, force=False)
    target = None
    for rel in releases:
        if release_key(rel) == args.release_id or rel.release_id == args.release_id:
            target = rel
            break
    if target is None:
        print(
            f"error: release not found in cache: {args.release_id}\n"
            f"hint: run 'manjaro-fetch list --refresh' first",
            file=sys.stderr,
        )
        return 1
    dest = Path(args.dir).expanduser() if args.dir else default_download_dir()

    def _progress(filename: str, received: int, total: int) -> None:
        if total > 0:
            pct = received * 100 // total
            sys.stderr.write(
                f"\r{filename}: {pct}% "
                f"({_format_size(received)} / {_format_size(total)})"
            )
        else:
            sys.stderr.write(f"\r{filename}: {_format_size(received)}")
        sys.stderr.flush()

    try:
        moved = download_release(
            target, dest, verify=not args.no_verify, progress=_progress
        )
    except Exception as exc:
        sys.stderr.write("\n")
        print(f"error: {exc}", file=sys.stderr)
        return 1
    sys.stderr.write("\n")
    for p in moved:
        print(str(p))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    download_dir = (
        Path(args.dir).expanduser() if args.dir else default_download_dir()
    )
    refresh_presence(download_dir)
    rows = list_downloaded()
    if not rows:
        print("No downloads recorded.")
        return 0
    print(f"{'KEY':<70} {'FILENAME':<45} {'PRESENT':<8} DOWNLOADED")
    print("-" * 155)
    for row in rows:
        present = "yes" if row["present"] else "no"
        print(
            f"{row['release_key']:<70} "
            f"{(row['filename'] or ''):<45} {present:<8} {row['downloaded_at']}"
        )
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    from ..config import user_config_dir, data_dir
    meta = cache_metadata()
    print(f"user config dir : {user_config_dir()}")
    print(f"data dir        : {data_dir()}")
    print(f"default download: {default_download_dir()}")
    user_cfg = user_config_dir() / "sources.toml"
    state = "present" if user_cfg.is_file() else "missing"
    print(f"user sources    : {user_cfg} ({state})")
    print(f"cached entries  : {meta['count']}")
    print(f"last refreshed  : {meta['last_refreshed'] or 'never'}")
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    releases = load_releases(include_extras=True, force=True)
    print(f"Refreshed {len(releases)} release(s) into cache.")
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    from ..config import load_source_configs
    print(f"{'NAME':<35} {'TYPE':<15} {'CATEGORY':<10} ENABLED")
    print("-" * 80)
    for cfg in load_source_configs():
        enabled = "yes" if cfg.enabled else "no"
        print(f"{cfg.name:<35} {cfg.type:<15} {cfg.category:<10} {enabled}")
    return 0


def cmd_gui(args: argparse.Namespace) -> int:
    try:
        from .gtk_app import run_gui
    except ImportError as exc:
        print(f"error: GTK3/PyGObject not available: {exc}", file=sys.stderr)
        print(
            "Install it with: sudo pacman -S python-gobject",
            file=sys.stderr,
        )
        return 1
    return run_gui()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manjaro-fetch",
        description=(
            "Download manager for Manjaro images. "
            "Cached data is served by default; use --refresh to fetch "
            "the latest releases from the network."
        ),
    )
    parser.add_argument(
        "--version", action="version", version="manjaro-fetch 0.1.0"
    )
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List cached releases (latest only)")
    p_list.add_argument(
        "-r", "--refresh", action="store_true",
        help="Fetch the latest releases from the network before listing",
    )
    p_list.add_argument(
        "-e", "--extras", action="store_true",
        help="Include extras (custom respins)",
    )
    p_list.add_argument("-s", "--source", help="Filter by source name")
    p_list.add_argument("-c", "--category", help="Filter by category")
    p_list.add_argument("--json", action="store_true", help="JSON output")
    p_list.set_defaults(func=cmd_list)

    p_refresh = sub.add_parser(
        "refresh", help="Fetch the latest releases from the network into the cache"
    )
    p_refresh.set_defaults(func=cmd_refresh)

    p_dl = sub.add_parser("download", help="Download a cached release by key")
    p_dl.add_argument("release_id", help="Release key from 'list' output")
    p_dl.add_argument("-d", "--dir", help="Destination directory")
    p_dl.add_argument(
        "--no-verify", action="store_true",
        help="Skip checksum verification",
    )
    p_dl.set_defaults(func=cmd_download)

    p_status = sub.add_parser("status", help="Show recorded downloads")
    p_status.add_argument(
        "-d", "--dir",
        help="Download directory to check for presence",
    )
    p_status.set_defaults(func=cmd_status)

    p_config = sub.add_parser("config", help="Show paths, cache state and config")
    p_config.set_defaults(func=cmd_config)

    p_sources = sub.add_parser("sources", help="List configured sources")
    p_sources.set_defaults(func=cmd_sources)

    p_gui = sub.add_parser("gui", help="Launch the graphical interface")
    p_gui.set_defaults(func=cmd_gui)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            return cmd_gui(args)
        parser.print_help()
        return 1
    return args.func(args)