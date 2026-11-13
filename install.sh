#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
INSTALL() {
	cp -f manjaro-iso-downloader.sh /usr/share/bin/manjaro-iso-downloader
	chmod 755 /usr/share/bin/manjaro-iso-downloader
	cp -f manjaro-iso-downloader.desktop /usr/share/applications/manjaro-iso-downloader.desktop
	chmod 644 /usr/share/applications/manjaro-iso-downloader.desktop
}

REMOVE () {
	rm -f /usr/share/applications/manjaro-iso-downloader.desktop
	rm -f /usr/share/bin/manjaro-iso-downloader
}

USAGE() {
	echo
    echo "Usage: you need to specific an argument:"
	echo "(i)pply or (r)emove"
	echo
}

# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
echo "This script must be run as root" 1>&2
exit 1
fi

if [[ ${@} == 0 ]]; then
	USAGE
	exit 1
else case ${@} in
	i|I) INSTALL ;;
	r|R) REMOVE ;;
	*) USAGE ;;
	esac
fi
