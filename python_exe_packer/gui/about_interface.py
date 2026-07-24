from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    BodyLabel, TitleLabel, CaptionLabel, ComboBox,
    MessageBox
)
from _metadata import APP_NAME, APP_VERSION, APP_AUTHOR, APP_COPYRIGHT
from utils.i18n import tr, set_language
from utils.config_manager import ConfigManager
from app.application import get_lang_manager


class AboutInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_manager = ConfigManager()
        self.setAutoFillBackground(False)
        self.setStyleSheet("background-color: transparent;")
        self._setup_ui()
        self.retranslateUi()

    def _setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignCenter)

        # 标题
        self.title = TitleLabel()
        self.title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.title)

        # 版本
        self.ver = BodyLabel()
        self.ver.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.ver)

        # 作者
        self.author = BodyLabel()
        self.author.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.author)

        # 版权
        self.copyright_label = CaptionLabel()
        self.copyright_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.copyright_label)

        self.main_layout.addSpacing(10)

        # 功能介绍
        self.desc_label = BodyLabel()
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.main_layout.addWidget(self.desc_label)

        self.main_layout.addSpacing(10)

        # GitHub 地址
        self.github_label = BodyLabel()
        self.github_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.github_label)

        self.main_layout.addSpacing(20)

        # 免责声明内容
        self.disclaimer_label = BodyLabel()
        self.disclaimer_label.setAlignment(Qt.AlignCenter)
        self.disclaimer_label.setWordWrap(True)
        self.main_layout.addWidget(self.disclaimer_label)

        self.main_layout.addSpacing(10)

        # 语言设置
        self.lang_label = BodyLabel()
        self.lang_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lang_label)
        lang_row = QHBoxLayout()
        lang_row.addStretch()
        self.lang_combo = ComboBox()
        self.lang_combo.addItem("中文", userData="zh")
        self.lang_combo.addItem("English", userData="en")
        config = self.config_manager.load_config()
        current_lang = config.get("language", "zh")
        idx = self.lang_combo.findData(current_lang)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        self.main_layout.addLayout(lang_row)

    def retranslateUi(self):
        self.title.setText(APP_NAME)
        self.ver.setText(f"{tr('app_version')} {APP_VERSION}")
        self.author.setText(f"{tr('author')}: {APP_AUTHOR}")
        self.copyright_label.setText(APP_COPYRIGHT)
        self.desc_label.setText(
            "基于 PyInstaller 的 Python 一键打包工具，提供直观的图形化界面，让打包变得简单高效。"
            "\n\n"
            "An intuitive PyInstaller GUI wrapper that simplifies Python app packaging into one click."
        )
        self.github_label.setText('GitHub: https://github.com/Gu-0312')
        self.disclaimer_label.setText(tr("disclaimer_text"))
        self.lang_label.setText(f"{tr('language')}:")

    def _on_lang_changed(self, index):
        lang_key = self.lang_combo.itemData(index)
        set_language(lang_key)
        get_lang_manager().set_language(lang_key)
        config = self.config_manager.load_config()
        config["language"] = lang_key
        self.config_manager.save_config(config)
        self.retranslateUi()