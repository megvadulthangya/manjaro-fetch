# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import hashlib
import subprocess
from pathlib import Path

CHUNK = 1024 * 1024


def hash_file(path: Path, algorithm: str = "sha256") -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as fh:
        while True:
            block = fh.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def verify_checksum(path: Path, expected: str, algorithm: str = "sha256") -> bool:
    if not expected:
        return True
    return hash_file(path, algorithm).lower() == expected.lower()


def verify_gpg(sig_path: Path, data_path: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["gpg", "--verify", str(sig_path), str(data_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return False, "gpg is not installed"
    except subprocess.TimeoutExpired:
        return False, "gpg verification timed out"
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, output
