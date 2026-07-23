import subprocess
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from qfluentwidgets import Dialog, PushButton, ListWidget, BodyLabel


class PyInstallerVersionDialog(Dialog):
    def __init__(self, parent=None):
        super().__init__("PyInstaller 版本管理", "", parent)
        layout = self.vBoxLayout

        check_btn = PushButton("检测版本")
        check_btn.clicked.connect(self._check)
        layout.addWidget(check_btn)

        self.list_widget = ListWidget()
        layout.addWidget(self.list_widget)

        close_btn = PushButton("关闭")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        self._check()

    def _check(self):
        self.list_widget.clear()
        cmds = [
            [sys.executable, "-m", "PyInstaller", "--version"],
            ["pyinstaller", "--version"],
        ]
        for cmd in cmds:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.list_widget.addItem(f"✓ {' '.join(cmd)}: {result.stdout.strip()}")
                else:
                    self.list_widget.addItem(f"✗ {' '.join(cmd)}: 无输出")
            except Exception as e:
                self.list_widget.addItem(f"✗ {' '.join(cmd)}: {str(e)}")
