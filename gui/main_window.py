import os
import sys
import threading
import time
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSystemTrayIcon
from qfluentwidgets import (
    MSFluentWindow, NavigationItemPosition, FluentIcon,
    PushButton, MessageBox,
    BodyLabel, setTheme, Theme, qconfig,
)
from _metadata import APP_NAME
from gui.pack_interface import PackInterface
from gui.template_interface import TemplateInterface
from gui.history_interface import HistoryInterface
from gui.env_interface import EnvInterface
from gui.icon_maker_interface import IconMakerInterface
from gui.about_interface import AboutInterface

from core.packer import Packer
from utils.config_manager import ConfigManager
from utils.env_checker import EnvChecker
from utils.build_cleaner import BuildCleaner
from utils.icon_cache_cleaner import IconCacheCleaner
from utils.i18n import tr
from app.application import get_lang_manager


class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()

        self.config_manager = ConfigManager()
        self.packer = Packer()
        self.build_cleaner = BuildCleaner()
        self._stop_event = threading.Event()
        self._nav_items = []

        config = self.config_manager.load_config()
        theme_mode = config.get("theme", "auto")
        
        # 使用qfluentwidgets的setTheme()处理主题
        if theme_mode == "dark":
            setTheme(Theme.DARK)
        elif theme_mode == "light":
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.AUTO)
        
        lang = config.get("language", "zh")
        get_lang_manager().set_language(lang)

        get_lang_manager().changed.connect(self._on_language_changed)
        
        # 监听主题变化，保存配置
        qconfig.themeChanged.connect(self._on_theme_changed)

        self._create_sub_interfaces()
        self._init_window()
        self._check_environment()
    
    def _on_theme_changed(self, theme):
        """主题变化时保存配置并更新所有子界面样式"""
        config = self.config_manager.load_config()
        if theme == Theme.DARK:
            config["theme"] = "dark"
        elif theme == Theme.LIGHT:
            config["theme"] = "light"
        else:
            config["theme"] = "auto"
        self.config_manager.save_config(config)
        
        for interface in [
            self.pack_interface,
            self.template_interface,
            self.history_interface,
            self.icon_maker_interface,
            self.env_interface,
            self.about_interface
        ]:
            interface.setAutoFillBackground(False)
        
        # 更新HistoryInterface的表格样式
        self.history_interface._update_table_style()
        # 更新日志区域的样式
        self.pack_interface.log_widget._update_style()
        # 更新图标制作界面的预览样式
        self.icon_maker_interface._update_preview_style()

    def _create_sub_interfaces(self):
        self.pack_interface = PackInterface(self.packer, self.config_manager)
        self.pack_interface.setObjectName("packInterface")
        self.template_interface = TemplateInterface(self.config_manager)
        self.template_interface.setObjectName("templateInterface")
        self.history_interface = HistoryInterface(self.config_manager)
        self.history_interface.setObjectName("historyInterface")
        self.icon_maker_interface = IconMakerInterface()
        self.icon_maker_interface.setObjectName("iconMakerInterface")
        self.env_interface = EnvInterface()
        self.env_interface.setObjectName("envInterface")
        self.about_interface = AboutInterface()
        self.about_interface.setObjectName("aboutInterface")

        self._nav_keys = ["pack", "template", "history", "icon", "env", "about"]
        self._nav_items = {}
        for interface, icon, key, pos in [
            (self.pack_interface, FluentIcon.VIEW, "pack", NavigationItemPosition.TOP),
            (self.template_interface, FluentIcon.LIBRARY, "template", NavigationItemPosition.TOP),
            (self.history_interface, FluentIcon.DATE_TIME, "history", NavigationItemPosition.TOP),
            (self.icon_maker_interface, FluentIcon.PHOTO, "icon", NavigationItemPosition.TOP),
            (self.env_interface, FluentIcon.SETTING, "env", NavigationItemPosition.TOP),
            (self.about_interface, FluentIcon.INFO, "about", NavigationItemPosition.BOTTOM),
        ]:
            item = self.addSubInterface(interface, icon, tr(key), position=pos)
            self._nav_items[key] = item

        self.pack_interface.start_pack_signal.connect(self._on_start_pack)
        self.pack_interface.stop_pack_signal.connect(self._on_stop_pack)
        self.pack_interface.pack_finished_signal.connect(self._on_pack_finished)
        self.pack_interface.clean_build_signal.connect(self._on_clean_build)
        self.build_cleaner.set_log_callback(
            lambda msg: self.pack_interface.log_widget.add_log(msg)
        )

    def _on_language_changed(self, lang):
        for key in self._nav_keys:
            item = self._nav_items.get(key)
            if item:
                item.setText(tr(key))
                item.setToolTip(tr(key))
        for name in ("pack_interface", "template_interface", "history_interface", "env_interface", "about_interface"):
            iface = getattr(self, name, None)
            if iface and hasattr(iface, "retranslateUi"):
                iface.retranslateUi()

    def _init_window(self):
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        screen = QGuiApplication.primaryScreen()
        if screen:
            center = screen.availableGeometry().center()
            self.move(
                center.x() - self.width() // 2,
                center.y() - self.height() // 2
            )

        icon_path = self._find_icon()
        if icon_path:
            ico = QIcon(icon_path)
            self.setWindowIcon(ico)
            self._tray = QSystemTrayIcon(ico, self)
            self._tray.show()
        else:
            self._tray = None

    def _find_icon(self):
        """查找图标文件：优先 PyInstaller 打包目录，其次项目源码目录"""
        # PyInstaller 打包后，图标作为数据文件在临时目录中
        if getattr(sys, 'frozen', False):
            meipass = getattr(sys, '_MEIPASS', '')
            print(f"[ICON] frozen mode, _MEIPASS={meipass}")
            if meipass:
                bundled = os.path.join(meipass, "icon.ico")
                print(f"[ICON] checking bundled: {bundled}, exists={os.path.exists(bundled)}")
                # 列出 _MEIPASS 下所有 ico 文件帮助排查
                for f in os.listdir(meipass):
                    if f.endswith('.ico'):
                        print(f"[ICON] found ico in bundle: {f}")
                if os.path.exists(bundled):
                    return bundled
        # 开发环境：项目根目录
        dev_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "icon.ico"
        )
        print(f"[ICON] checking dev: {dev_path}, exists={os.path.exists(dev_path)}")
        if os.path.exists(dev_path):
            return dev_path
        return None

    def _check_environment(self):
        checker = EnvChecker()
        results = checker.check_all()
        for key, result in results.items():
            msg = f"[{result['status'].upper()}] {result['name']}: {result['value']} - {result['message']}"
            self.pack_interface.log_widget.add_log(msg)

        summary = checker.get_summary()
        if summary["has_error"]:
            self.pack_interface.log_widget.add_log(
                f"[ERROR] {tr('env_summary_error')}: {summary['success']} {tr('passed')}, "
                f"{summary['warning']} {tr('warnings')}, {summary['error']} {tr('errors')}"
            )
        elif summary["has_warning"]:
            self.pack_interface.log_widget.add_log(
                f"[WARNING] {tr('env_summary_warning')}: {summary['success']} {tr('passed')}, "
                f"{summary['warning']} {tr('warnings')}"
            )
        else:
            self.pack_interface.log_widget.add_log(
                f"[SUCCESS] {tr('env_summary_success')}: {summary['success']} {tr('passed')}"
            )

    def _on_start_pack(self, config):
        self._stop_event.clear()
        self._pack_start_time = time.time()
        thread = threading.Thread(
            target=self._run_pack, args=(config,), daemon=True
        )
        thread.start()

    def _on_stop_pack(self):
        self._stop_event.set()

    def _run_pack(self, config):
        try:
            success = self.packer.pack(config, stop_event=self._stop_event)
            duration = time.time() - getattr(self, '_pack_start_time', time.time())
            self.packer.finished_signal.emit(success, config, int(duration))
        except Exception as e:
            self.packer.log_signal.emit(f"[ERROR] {tr('pack_failed')}: {str(e)}")
            self.packer.finished_signal.emit(False, config, 0)

    def _on_pack_finished(self, success, config, duration):
        name = config.get("name", "") or os.path.splitext(os.path.basename(config.get("source_file", "")))[0]
        if success:
            self.pack_interface.log_widget.add_log(f"[SUCCESS] {tr('pack_done')}")
            # 清理Windows图标缓存，确保EXE图标正确显示
            try:
                IconCacheCleaner.clear_icon_cache()
                self.pack_interface.log_widget.add_log("[INFO] 已刷新图标缓存")
            except Exception:
                pass
            if config.get("auto_open_output", True) and config.get("output_dir"):
                try:
                    os.startfile(config["output_dir"])
                except Exception:
                    pass
        else:
            self.pack_interface.log_widget.add_log(f"[ERROR] {tr('pack_failed')}")
        self.config_manager.add_to_history(config, success, duration)
        if self._tray and self._tray.supportsMessages():
            title = tr("pack_notify_title")
            msg = tr("pack_notify_success").format(name=name) if success else tr("pack_notify_fail").format(name=name)
            self._tray.showMessage(title, msg, QSystemTrayIcon.Information, 5000)

    def _on_clean_build(self, project_dir):
        count = self.build_cleaner.clean(project_dir)
        self.pack_interface.log_widget.add_log(
            f"[SUCCESS] {tr('clean_done')} ({count})"
        )
