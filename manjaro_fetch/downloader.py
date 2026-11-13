# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import shutil
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from .config import cache_dir
from .integrity import hash_file, verify_checksum, verify_gpg
from .models import Release, ReleaseFile, release_key
from .state import mark_downloaded

ProgressCallback = Callable[[str, int, int], None]


def _download(
    url: str,
    dest: Path,
    progress: Optional[ProgressCallback] = None,
    filename: str = "",
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "manjaro-fetch/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        received = 0
        with tmp.open("wb") as out:
            while True:
                block = resp.read(1024 * 256)
                if not block:
                    break
                out.write(block)
                received += len(block)
                if progress:
                    progress(filename or dest.name, received, total)
    tmp.replace(dest)


def _verify_iso(primary_path: Path, primary_file: ReleaseFile, work: Path) -> None:
    verified = False
    for algo, url in primary_file.checksum_urls.items():
        hash_path = work / (primary_file.filename + "." + algo)
        if not hash_path.is_file():
            try:
                _download(url, hash_path, None, filename=hash_path.name)
            except Exception:
                continue
        try:
            content = hash_path.read_text().strip()
            expected = content.split()[0] if content else ""
        except Exception:
            continue
        if not expected:
            continue
        if not verify_checksum(primary_path, expected, algo):
            raise RuntimeError(
                f"checksum mismatch for {primary_path.name} ({algo})"
            )
        primary_file.checksums[algo] = expected
        verified = True
        break
    if not verified and primary_file.checksums:
        algo, expected = next(iter(primary_file.checksums.items()))
        if not verify_checksum(primary_path, expected, algo):
            raise RuntimeError(
                f"checksum mismatch for {primary_path.name} ({algo})"
            )


def download_release(
    release: Release,
    dest_dir: Path,
    verify: bool = True,
    progress: Optional[ProgressCallback] = None,
) -> list[Path]:
    dest_dir = dest_dir.expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    work = cache_dir() / "downloads" / release.source / release.release_id.replace("/", "_")
    work.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []
    primary_path: Optional[Path] = None
    primary_file: Optional[ReleaseFile] = None

    for rf in release.files:
        target = work / rf.filename
        if not target.is_file():
            _download(rf.url, target, progress, filename=rf.filename)
        downloaded.append(target)
        if rf.filename.endswith(".iso"):
            primary_path = target
            primary_file = rf
        if rf.sig_url:
            sig_target = work / (rf.filename + ".sig")
            if not sig_target.is_file():
                try:
                    _download(rf.sig_url, sig_target, None, filename=sig_target.name)
                except Exception:
                    pass

    if primary_path is None or primary_file is None:
        raise RuntimeError(f"release {release.release_id} has no ISO file")

    if verify:
        _verify_iso(primary_path, primary_file, work)
        if primary_file.sig_url:
            sig_path = work / (primary_file.filename + ".sig")
            if sig_path.is_file():
                ok, output = verify_gpg(sig_path, primary_path)
                if not ok:
                    raise RuntimeError(f"GPG verification failed: {output}")

    final_iso = dest_dir / primary_path.name
    if final_iso.exists():
        final_iso.unlink()
    shutil.move(str(primary_path), str(final_iso))

    moved = [final_iso]
    for p in downloaded:
        if p == primary_path:
            continue
        final = dest_dir / p.name
        if final.exists():
            final.unlink()
        shutil.move(str(p), str(final))
        moved.append(final)

    sha256 = ""
    for algo, val in primary_file.checksums.items():
        if algo == "sha256":
            sha256 = val
            break
    if not sha256:
        sha256 = hash_file(final_iso, "sha256")
    mark_downloaded(
        release_key=release_key(release),
        source=release.source,
        edition=release.edition,
        filename=final_iso.name,
        sha256=sha256,
        size=final_iso.stat().st_size,
    )
    return moved
