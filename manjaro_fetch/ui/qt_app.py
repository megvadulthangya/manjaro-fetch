# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2022-2025 Stefano Capitani (Ste74)
# Copyright (C) 2026 Gyöngyösi Gábor (megvadulthangya)
#
# This file is part of manjaro-fetch, a download manager for Manjaro images.
# Based on manjaro-iso-downloader by Stefano Capitani.
# See the LICENSE file in the project root for full license text.
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from ..config import default_download_dir
from ..downloader import download_release
from ..models import release_key
from ..sources import load_releases
from ..state import is_downloaded

DARK_QSS = """
QMainWindow, QWidget { background-color: #2b2b2b; color: #e0e0e0; }
QTreeWidget { background-color: #1e1e1e; alternate-background-color: #262626; color: #e0e0e0; }
QTreeWidget::item:selected { background-color: #3b6ea5; }
QTextBrowser { background-color: #1e1e1e; color: #e0e0e0; }
QPushButton { background-color: #3a3a3a; color: #e0e0e0; padding: 6px 12px; }
QPushButton:hover { background-color: #4a4a4a; }
QLineEdit, QComboBox { background-color: #1e1e1e; color: #e0e0e0; padding: 4px; }
"""

LIGHT_QSS = """
QMainWindow, QWidget { background-color: #f5f5f5; color: #1a1a1a; }
QTreeWidget { background-color: #ffffff; alternate-background-color: #f0f0f0; color: #1a1a1a; }
QTreeWidget::item:selected { background-color: #99c1f1; color: #000; }
QTextBrowser { background-color: #ffffff; color: #1a1a1a; }
QPushButton { background-color: #e0e0e0; padding: 6px 12px; }
QPushButton:hover { background-color: #d0d0d0; }
QLineEdit, QComboBox { padding: 4px; }
"""


def _is_dark() -> bool:
    hints = QGuiApplication.styleHints()
    try:
        scheme = hints.colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except Exception:
        pass
    palette = QGuiApplication.palette()
    return palette.window().color().lightness() < 128


class LoaderWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, include_all: bool, include_extras: bool) -> None:
        super().__init__()
        self._include_all = include_all
        self._include_extras = include_extras

    def run(self) -> None:
        try:
            releases = load_releases(
                include_all=self._include_all,
                include_extras=self._include_extras,
            )
            self.finished_ok.emit(releases)
        except Exception as exc:
            self.failed.emit(str(exc))


class DownloadWorker(QThread):
    progress = Signal(str, int, int)
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, release, dest: Path) -> None:
        super().__init__()
        self._release = release
        self._dest = dest

    def run(self) -> None:
        try:
            moved = download_release(
                self._release,
                self._dest,
                verify=True,
                progress=lambda name, rec, tot: self.progress.emit(name, rec, tot),
            )
            self.finished_ok.emit(moved)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("manjaro-fetch")
        self.resize(1050, 680)
        self._releases: list = []
        self._by_key: dict = {}
        self._loader: LoaderWorker | None = None
        self._download_worker: DownloadWorker | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        filters = QHBoxLayout()
        self.show_all = QCheckBox("Show all versions")
        self.show_extras = QCheckBox("Show extras (custom respins)")
        self.reload_btn = QPushButton("Reload")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter…")
        filters.addWidget(self.show_all)
        filters.addWidget(self.show_extras)
        filters.addWidget(self.reload_btn)
        filters.addWidget(self.search, 1)
        root.addLayout(filters)

        splitter = QSplitter(Qt.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Release", "Category", "Status"])
        self.tree.setAlternatingRowColors(True)
        self.details = QTextBrowser()
        splitter.addWidget(self.tree)
        splitter.addWidget(self.details)
        splitter.setSizes([550, 500])
        root.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        self.status_label = QLabel("")
        self.open_btn = QPushButton("Open download folder")
        self.download_btn = QPushButton("Download")
        buttons.addWidget(self.status_label, 1)
        buttons.addWidget(self.open_btn)
        buttons.addWidget(self.download_btn)
        root.addLayout(buttons)

        self.show_all.toggled.connect(self._reload)
        self.show_extras.toggled.connect(self._reload)
        self.reload_btn.clicked.connect(self._reload)
        self.search.textChanged.connect(self._populate_tree)
        self.tree.currentItemChanged.connect(self._on_select)
        self.download_btn.clicked.connect(self._on_download)
        self.open_btn.clicked.connect(self._on_open_folder)

        self._reload()

    def _reload(self) -> None:
        if self._loader and self._loader.isRunning():
            return
        self.status_label.setText("Loading…")
        self._loader = LoaderWorker(
            include_all=self.show_all.isChecked(),
            include_extras=self.show_extras.isChecked(),
        )
        self._loader.finished_ok.connect(self._on_loaded)
        self._loader.failed.connect(self._on_load_failed)
        self._loader.start()

    def _on_loaded(self, releases: list) -> None:
        self._releases = releases
        self._by_key = {release_key(r): r for r in releases}
        self.status_label.setText(f"{len(releases)} release(s)")
        self._populate_tree()

    def _on_load_failed(self, message: str) -> None:
        self.status_label.setText("Load failed")
        QMessageBox.warning(self, "Load failed", message)

    def _populate_tree(self) -> None:
        needle = self.search.text().strip().lower()
        self.tree.clear()
        for rel in self._releases:
            haystack = (
                f"{rel.edition} {rel.version} {rel.date} {rel.source}".lower()
            )
            if needle and needle not in haystack:
                continue
            item = QTreeWidgetItem(
                [
                    f"{rel.edition} — {rel.version or rel.release_id}",
                    rel.category,
                    "",
                ]
            )
            key = release_key(rel)
            item.setData(0, Qt.UserRole, key)
            if is_downloaded(key):
                item.setText(2, "downloaded")
            self.tree.addTopLevelItem(item)

    def _on_select(self, current, _previous) -> None:
        if current is None:
            self.details.clear()
            return
        key = current.data(0, Qt.UserRole)
        rel = self._by_key.get(key)
        if rel is None:
            self.details.clear()
            return
        lines = [
            f"<h2>{rel.edition}</h2>",
            f"<p><b>Source:</b> {rel.source}<br>",
            f"<b>Category:</b> {rel.category}<br>",
            f"<b>Version:</b> {rel.version or '—'}<br>",
            f"<b>Date:</b> {rel.date or '—'}<br>",
            f"<b>Latest:</b> {'yes' if rel.is_latest else 'no'}</p>",
            "<h3>Files</h3><ul>",
        ]
        for f in rel.files:
            lines.append(f"<li>{f.filename} — {f.url}</li>")
        lines.append("</ul>")
        if rel.notes:
            lines.append(f"<h3>Notes</h3><pre>{rel.notes}</pre>")
        self.details.setHtml("".join(lines))

    def _on_download(self) -> None:
        current = self.tree.currentItem()
        if current is None:
            return
        key = current.data(0, Qt.UserRole)
        rel = self._by_key.get(key)
        if rel is None:
            return
        if is_downloaded(key):
            answer = QMessageBox.question(
                self,
                "Already downloaded",
                "This release is already marked as downloaded. Re-download anyway?",
            )
            if answer != QMessageBox.Yes:
                return
        dest = default_download_dir()
        self.status_label.setText(f"Downloading {rel.edition}…")
        self._download_worker = DownloadWorker(rel, dest)
        self._download_worker.progress.connect(self._on_progress)
        self._download_worker.finished_ok.connect(self._on_download_done)
        self._download_worker.failed.connect(self._on_download_failed)
        self._download_worker.start()

    def _on_progress(self, filename: str, received: int, total: int) -> None:
        if total > 0:
            pct = received * 100 // total
            self.status_label.setText(f"{filename}: {pct}%")
        else:
            self.status_label.setText(f"{filename}: {received} B")

    def _on_download_done(self, moved: list) -> None:
        self.status_label.setText(f"Done: {len(moved)} file(s)")
        self._populate_tree()

    def _on_download_failed(self, message: str) -> None:
        self.status_label.setText("Download failed")
        QMessageBox.warning(self, "Download failed", message)

    def _on_open_folder(self) -> None:
        path = default_download_dir()
        path.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", str(path)])
        except FileNotFoundError:
            QMessageBox.information(self, "Folder", str(path))


def run_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("manjaro-fetch")
    app.setApplicationDisplayName("manjaro-fetch")
    app.setOrganizationName("manjaro-fetch")
    app.setStyleSheet(DARK_QSS if _is_dark() else LIGHT_QSS)
    window = MainWindow()
    window.show()
    return app.exec()
