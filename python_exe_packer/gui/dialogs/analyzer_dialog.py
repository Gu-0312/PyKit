import os
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QFileDialog
from qfluentwidgets import Dialog, PushButton, BodyLabel


class AnalyzerDialog(Dialog):
    def __init__(self, parent=None):
        super().__init__("", "", parent)
        layout = self.vBoxLayout

        self.path_edit = BodyLabel()
        layout.addWidget(self.path_edit)

        btn_row = QHBoxLayout()
        self.analyze_exe_btn = PushButton()
        self.analyze_exe_btn.clicked.connect(self._pick_exe)
        btn_row.addWidget(self.analyze_exe_btn)
        self.analyze_dir_btn = PushButton()
        self.analyze_dir_btn.clicked.connect(self._pick_dir)
        btn_row.addWidget(self.analyze_dir_btn)
        layout.addLayout(btn_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["", ""])
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, self.tree.header().Stretch)
        layout.addWidget(self.tree)

        close_btn = PushButton()
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def retranslateUi(self):
        from utils.i18n import tr
        self.setTitle(tr("analyzer_title"))
        self.analyze_exe_btn.setText(tr("analyzer_exe"))
        self.analyze_dir_btn.setText(tr("analyzer_dir"))
        close_btn = self.vBoxLayout.itemAt(self.vBoxLayout.count() - 1).widget()
        close_btn.setText(tr("close"))

    def _pick_exe(self):
        path, _ = QFileDialog.getOpenFileName(self, "", "", "EXE (*.exe);;All Files (*)")
        if path:
            self._analyze(path)

    def _pick_dir(self):
        path = QFileDialog.getExistingDirectory(self)
        if path:
            self._analyze(path)

    def _analyze(self, path):
        self.tree.clear()
        self.path_edit.setText(path)

        if os.path.isfile(path) and path.endswith(".exe"):
            self._analyze_exe(path)
        elif os.path.isdir(path):
            self._analyze_dir(path)

    def _analyze_exe(self, path):
        try:
            result = self._run_archive_viewer(path)
            if result:
                root = QTreeWidgetItem(self.tree, [os.path.basename(path), f"{os.path.getsize(path) / 1024:.1f} KB"])
                for line in result:
                    QTreeWidgetItem(root, [line, ""])
                return
        except Exception:
            pass

        size = os.path.getsize(path)
        root = QTreeWidgetItem(self.tree, [os.path.basename(path), f"{size / 1024:.1f} KB"])
        QTreeWidgetItem(root, ["(pyi-archive_viewer not available)", ""])

    def _analyze_dir(self, path):
        total = 0
        items = []
        for root_dir, dirs, files in os.walk(path):
            for f in files:
                fp = os.path.join(root_dir, f)
                try:
                    sz = os.path.getsize(fp)
                except OSError:
                    sz = 0
                rel = os.path.relpath(fp, path)
                items.append((rel, sz))
                total += sz

        root = QTreeWidgetItem(self.tree, [os.path.basename(path), f"{total / 1024:.1f} KB ({len(items)} files)"])
        for rel, sz in sorted(items):
            QTreeWidgetItem(root, [rel, f"{sz / 1024:.1f} KB" if sz > 0 else "0 B"])

    def _run_archive_viewer(self, exe_path):
        import subprocess, sys, tempfile
        out = tempfile.mktemp(suffix=".txt")
        try:
            subprocess.run(
                [sys.executable, "-m", "PyInstaller.utils.cliutils.archive_viewer", exe_path],
                capture_output=True, text=True, timeout=15
            )
            result = subprocess.run(
                [sys.executable, "-m", "PyInstaller.utils.cliutils.archive_viewer", exe_path],
                capture_output=True, text=True, timeout=15
            )
            lines = [l for l in result.stdout.splitlines() if l.strip() and "?" not in l[:3]]
            return lines[:100] if lines else None
        except Exception:
            return None
