# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import subprocess
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from ..config import default_download_dir
from ..downloader import download_release
from ..models import release_key
from ..sources import load_releases
from ..state import is_downloaded


class _LoaderThread(threading.Thread):
    def __init__(self, include_extras, force, on_done, on_error):
        super().__init__(daemon=True)
        self._include_extras = include_extras
        self._force = force
        self._on_done = on_done
        self._on_error = on_error

    def run(self):
        try:
            releases = load_releases(
                include_extras=self._include_extras,
                force=self._force,
            )
            GLib.idle_add(self._on_done, releases)
        except Exception as exc:
            GLib.idle_add(self._on_error, str(exc))


class _DownloadThread(threading.Thread):
    def __init__(self, release, dest, on_progress, on_done, on_error):
        super().__init__(daemon=True)
        self._release = release
        self._dest = dest
        self._on_progress = on_progress
        self._on_done = on_done
        self._on_error = on_error

    def run(self):
        try:
            moved = download_release(
                self._release,
                self._dest,
                verify=True,
                progress=lambda n, r, t: GLib.idle_add(self._on_progress, n, r, t),
            )
            GLib.idle_add(self._on_done, moved)
        except Exception as exc:
            GLib.idle_add(self._on_error, str(exc))


class MainWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="manjaro-fetch")
        self.set_default_size(1050, 680)
        self._releases = []
        self._by_key = {}
        self._generation = 0

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_top(6)
        vbox.set_margin_bottom(6)
        vbox.set_margin_start(6)
        vbox.set_margin_end(6)
        self.add(vbox)

        filters = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.show_extras_check = Gtk.CheckButton(
            label="Show extras (custom respins)"
        )
        self.reload_btn = Gtk.Button(label="Refresh from network")
        self.reload_btn.set_tooltip_text(
            "Fetch the latest releases from GitHub, Sway, SourceForge "
            "and Internet Archive. This uses network quota."
        )
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Filter…")
        self.search_entry.set_hexpand(True)
        filters.pack_start(self.show_extras_check, False, False, 0)
        filters.pack_start(self.reload_btn, False, False, 0)
        filters.pack_start(self.search_entry, True, True, 0)
        vbox.pack_start(filters, False, False, 0)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(550)

        scroll_tree = Gtk.ScrolledWindow()
        scroll_tree.set_hexpand(True)
        scroll_tree.set_vexpand(True)
        self.store = Gtk.ListStore(str, str, str, str)
        self.tree = Gtk.TreeView(model=self.store)
        for i, title in enumerate(["Release", "Category", "Status"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.tree.append_column(column)
        scroll_tree.add(self.tree)
        paned.pack1(scroll_tree, resize=True, shrink=False)

        scroll_details = Gtk.ScrolledWindow()
        self.details = Gtk.TextView()
        self.details.set_editable(False)
        self.details.set_wrap_mode(Gtk.WrapMode.WORD)
        self.details.set_left_margin(8)
        self.details.set_right_margin(8)
        scroll_details.add(self.details)
        paned.pack2(scroll_details, resize=True, shrink=False)
        vbox.pack_start(paned, True, True, 0)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.status_label = Gtk.Label(label="")
        self.status_label.set_hexpand(True)
        self.status_label.set_xalign(0)
        self.open_btn = Gtk.Button(label="Open download folder")
        self.download_btn = Gtk.Button(label="Download")
        bottom.pack_start(self.status_label, True, True, 0)
        bottom.pack_start(self.open_btn, False, False, 0)
        bottom.pack_start(self.download_btn, False, False, 0)
        vbox.pack_start(bottom, False, False, 0)

        self.show_extras_check.connect("toggled", lambda *_: self._load(force=False))
        self.reload_btn.connect("clicked", lambda *_: self._load(force=True))
        self.search_entry.connect("search-changed", lambda *_: self._populate_tree())
        self.tree.get_selection().connect("changed", self._on_select)
        self.download_btn.connect("clicked", lambda *_: self._on_download())
        self.open_btn.connect("clicked", lambda *_: self._on_open_folder())

        self._load(force=False)

    def _load(self, force: bool):
        self._generation += 1
        gen = self._generation
        self.reload_btn.set_sensitive(False)
        self.status_label.set_text(
            "Refreshing from network…" if force else "Loading from cache…"
        )

        def on_done(releases):
            if gen != self._generation:
                return False
            self._releases = releases
            self._by_key = {release_key(r): r for r in releases}
            if not releases and not force:
                self.status_label.set_text(
                    "Cache is empty. Click 'Refresh from network' to populate it."
                )
            else:
                self.status_label.set_text(f"{len(releases)} release(s)")
            self._populate_tree()
            self.reload_btn.set_sensitive(True)
            return False

        def on_error(msg):
            if gen != self._generation:
                return False
            self.status_label.set_text("Load failed")
            dlg = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="Load failed",
            )
            dlg.format_secondary_text(msg)
            dlg.run()
            dlg.destroy()
            self.reload_btn.set_sensitive(True)
            return False

        _LoaderThread(
            self.show_extras_check.get_active(),
            force,
            on_done, on_error,
        ).start()

    def _populate_tree(self):
        needle = self.search_entry.get_text().strip().lower()
        self.store.clear()
        for rel in self._releases:
            haystack = f"{rel.edition} {rel.version} {rel.date} {rel.source}".lower()
            if needle and needle not in haystack:
                continue
            display = f"{rel.edition} — {rel.version or rel.release_id}"
            status = "downloaded" if is_downloaded(release_key(rel)) else ""
            self.store.append([display, rel.category, status, release_key(rel)])

    def _on_select(self, selection):
        model, iter_ = selection.get_selected()
        if iter_ is None:
            self.details.get_buffer().set_text("")
            return
        key = model[iter_][3]
        rel = self._by_key.get(key)
        if rel is None:
            self.details.get_buffer().set_text("")
            return
        lines = [
            f"{rel.edition}",
            "",
            f"Source:   {rel.source}",
            f"Category: {rel.category}",
            f"Version:  {rel.version or '—'}",
            f"Date:     {rel.date or '—'}",
            "",
            "Files:",
        ]
        for f in rel.files:
            lines.append(f"  {f.filename}")
            lines.append(f"    {f.url}")
        if rel.notes:
            lines.append("")
            lines.append("Notes:")
            lines.append(rel.notes)
        self.details.get_buffer().set_text("\n".join(lines))

    def _on_download(self):
        model, iter_ = self.tree.get_selection().get_selected()
        if iter_ is None:
            return
        key = model[iter_][3]
        rel = self._by_key.get(key)
        if rel is None:
            return
        if is_downloaded(key):
            dlg = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Already downloaded",
            )
            dlg.format_secondary_text("Re-download anyway?")
            response = dlg.run()
            dlg.destroy()
            if response != Gtk.ResponseType.YES:
                return
        dest = default_download_dir()

        def on_progress(name, rec, tot):
            if tot > 0:
                pct = rec * 100 // tot
                self.status_label.set_text(f"{name}: {pct}%")
            else:
                self.status_label.set_text(f"{name}: {rec} B")
            return False

        def on_done(moved):
            self.status_label.set_text(f"Done: {len(moved)} file(s)")
            self._populate_tree()
            return False

        def on_error(msg):
            self.status_label.set_text("Download failed")
            dlg = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text="Download failed",
            )
            dlg.format_secondary_text(msg)
            dlg.run()
            dlg.destroy()
            return False

        self.status_label.set_text(f"Downloading {rel.edition}…")
        _DownloadThread(rel, dest, on_progress, on_done, on_error).start()

    def _on_open_folder(self):
        path = default_download_dir()
        path.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", str(path)])
        except FileNotFoundError:
            subprocess.Popen(["gio", "open", str(path)])


def run_gui() -> int:
    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return 0