import sys
import os
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from qfluentwidgets import setTheme, Theme
from _metadata import APP_NAME


class LanguageManager(QObject):
    changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._lang = "zh"

    def set_language(self, lang):
        if lang != self._lang:
            self._lang = lang
            self.changed.emit(lang)

    def get_language(self):
        return self._lang


_lang_mgr = LanguageManager()


def get_lang_manager():
    return _lang_mgr


class Application(QApplication):
    def __init__(self, args=None):
        super().__init__(args or sys.argv)
        self.setApplicationName(APP_NAME)
        self.setOrganizationName("PyPacker")
        self.setQuitOnLastWindowClosed(True)
        setTheme(Theme.AUTO)
        
        # 设置应用程序图标
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "icon.ico"
        )
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    @staticmethod
    def ensure_single_instance():
        from core.single_instance import SingleInstance
        instance = SingleInstance()
        if not instance.acquire():
            return False
        return instance
