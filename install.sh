#!/usr/bin/env bash
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
# Silent on success; prints errors and exits non-zero on failure.
set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
APPS_DIR="${HOME}/.local/share/applications"
ICONS_ROOT="${HOME}/.local/share/icons/hicolor"
VENV_DIR="${HOME}/.local/share/manjaro-fetch/venv"
WRAPPER="${BIN_DIR}/manjaro-fetch"

fail() {
    echo "error: $*" >&2
    exit 1
}

install_app() {
    if ! python3 -c "import gi" 2>/dev/null; then
        fail "python-gobject is required for the GTK3 GUI: sudo pacman -S python-gobject"
    fi

    mkdir -p "${BIN_DIR}" "${APPS_DIR}" "${HOME}/.local/share/manjaro-fetch"

    python3 -m venv --system-site-packages --clear "${VENV_DIR}"
    "${VENV_DIR}/bin/pip" install --upgrade --quiet pip
    "${VENV_DIR}/bin/pip" install --quiet "."

    if ! "${VENV_DIR}/bin/python" -c "import manjaro_fetch.ui.cli" >/dev/null 2>&1; then
        echo "error: installed package failed to import; traceback follows" >&2
        "${VENV_DIR}/bin/python" -c "import manjaro_fetch.ui.cli" || true
        fail "package is broken; fix the source and reinstall"
    fi
    if ! "${VENV_DIR}/bin/python" -c "from manjaro_fetch.sources import load_releases" >/dev/null 2>&1; then
        echo "error: manjaro_fetch.sources.load_releases is missing" >&2
        fail "sources/__init__.py is broken or missing"
    fi
    if ! "${VENV_DIR}/bin/python" -c "from manjaro_fetch.ui.gtk_app import run_gui" >/dev/null 2>&1; then
        echo "error: GTK3 GUI failed to import; traceback follows" >&2
        "${VENV_DIR}/bin/python" -c "from manjaro_fetch.ui.gtk_app import run_gui" || true
        fail "GTK3 GUI is broken; verify python-gobject is installed"
    fi
    if [ ! -x "${VENV_DIR}/bin/manjaro-fetch" ]; then
        fail "entry point ${VENV_DIR}/bin/manjaro-fetch missing"
    fi

    # Seed the cache from the bundled seed_cache.json, if present.
    "${VENV_DIR}/bin/python" -c "
from manjaro_fetch.state import seed_from_bundled
try:
    seed_from_bundled()
except Exception:
    pass
" >/dev/null 2>&1 || true

    cat > "${WRAPPER}" <<EOF
#!/usr/bin/env bash
exec "${VENV_DIR}/bin/manjaro-fetch" "\$@"
EOF
    chmod 755 "${WRAPPER}"

    cat > "${APPS_DIR}/manjaro-fetch.desktop" <<EOF
[Desktop Entry]
Type=Application
Encoding=UTF-8
Name=Manjaro Fetch
Comment=Download Manjaro official, community and custom images
Exec=${WRAPPER}
Icon=manjaro-fetch
Terminal=false
Categories=Utility;System;
StartupNotify=false
EOF
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
    rm -f "${WRAPPER}"
    rm -f "${APPS_DIR}/manjaro-fetch.desktop"
    for size in 16x16 22x22 24x24 32x32 48x48 64x64 scalable; do
        rm -f "${ICONS_ROOT}/${size}/apps/manjaro-fetch.svg"
    done
    rm -rf "${HOME}/.local/share/manjaro-fetch"
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