#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
# Portable user-level installer for manjaro-fetch.
# Usage: ./install.sh -i   (or: ./install.sh i)
#        ./install.sh -r   (or: ./install.sh r)
# Silent on success; no output for missing arguments.
set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
APPS_DIR="${HOME}/.local/share/applications"
ICONS_ROOT="${HOME}/.local/share/icons/hicolor"

install_app() {
    mkdir -p "${BIN_DIR}" "${APPS_DIR}"

    python3 -m pip install --user --upgrade --quiet --no-warn-script-location .

    python3 - "${APPS_DIR}/manjaro-fetch.desktop" <<'PY'
import os
import sys
src = "manjaro-fetch.desktop"
dst = sys.argv[1]
with open(src, "r", encoding="utf-8") as fh:
    content = fh.read()
content = content.replace("Exec=manjaro-fetch", f"Exec={os.path.expanduser('~')}/.local/bin/manjaro-fetch")
with open(dst, "w", encoding="utf-8") as fh:
    fh.write(content)
PY
    chmod 644 "${APPS_DIR}/manjaro-fetch.desktop"

    for size in 16x16 22x22 24x24 32x32 48x48 64x64; do
        src="icons/hicolor/${size}/apps/dcmi.svg"
        if [ -f "${src}" ]; then
            mkdir -p "${ICONS_ROOT}/${size}/apps"
            cp -f "${src}" "${ICONS_ROOT}/${size}/apps/manjaro-fetch.svg"
        fi
    done
    if [ -f "icons/hicolor/scalable/apps/dcmi.svg" ]; then
        mkdir -p "${ICONS_ROOT}/scalable/apps"
        cp -f "icons/hicolor/scalable/apps/dcmi.svg" "${ICONS_ROOT}/scalable/apps/manjaro-fetch.svg"
    fi

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${APPS_DIR}" >/dev/null 2>&1 || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -t -f "${ICONS_ROOT}" >/dev/null 2>&1 || true
    fi
}

remove_app() {
    rm -f "${APPS_DIR}/manjaro-fetch.desktop"
    for size in 16x16 22x22 24x24 32x32 48x48 64x64 scalable; do
        rm -f "${ICONS_ROOT}/${size}/apps/manjaro-fetch.svg"
    done
    python3 -m pip uninstall -y --quiet manjaro-fetch >/dev/null 2>&1 || true
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "${APPS_DIR}" >/dev/null 2>&1 || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -t -f "${ICONS_ROOT}" >/dev/null 2>&1 || true
    fi
}

case "${1:-}" in
    -i|i|--install) install_app ;;
    -r|r|--remove)  remove_app ;;
    *)              exit 1 ;;
esac
