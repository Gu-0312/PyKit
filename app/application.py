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
        icon_path = self._find_icon()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

    def _find_icon(self):
        """查找图标文件：优先 PyInstaller 打包目录，其次项目源码目录"""
        if getattr(sys, 'frozen', False):
            meipass = getattr(sys, '_MEIPASS', '')
            if meipass:
                bundled = os.path.join(meipass, "icon.ico")
                if os.path.exists(bundled):
                    return bundled
        dev_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "icon.ico"
        )
        if os.path.exists(dev_path):
            return dev_path
        return None

    @staticmethod
    def ensure_single_instance():
        from core.single_instance import SingleInstance
        instance = SingleInstance()
        if not instance.acquire():
            return False
        return instance
