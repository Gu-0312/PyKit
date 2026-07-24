from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit
from qfluentwidgets import BodyLabel, ToolButton, PrimaryToolButton, FluentIcon, qconfig, setTheme, Theme
from utils.i18n import tr
from utils.theme_manager import get_theme_manager


class LogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self.title = BodyLabel()
        header.addWidget(self.title)
        header.addStretch()

        self.theme_btn = PrimaryToolButton(FluentIcon.CONSTRACT)
        self.theme_btn.clicked.connect(self._toggle_theme)
        header.addWidget(self.theme_btn)

        copy_btn = ToolButton(FluentIcon.COPY)
        copy_btn.clicked.connect(self._copy_all)
        header.addWidget(copy_btn)

        clear_btn = ToolButton(FluentIcon.DELETE)
        clear_btn.clicked.connect(self.clear_log)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(10000)
        self.text_edit.setUndoRedoEnabled(False)
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        layout.addWidget(self.text_edit)

        # 应用初始样式
        self._update_style()

    def _update_style(self):
        """根据主题更新QPlainTextEdit样式"""
        stylesheet = self._theme_manager.get_log_widget_stylesheet()
        self.text_edit.setStyleSheet(stylesheet)

    def add_log(self, message: str):
        color = "INFO"
        if message.startswith("[SUCCESS]"):
            color = "SUCCESS"
        elif message.startswith("[WARN]"):
            color = "WARNING"
        elif message.startswith("[ERROR]"):
            color = "ERROR"
        
        # 根据主题获取正确的颜色
        log_colors = self._theme_manager.get_log_colors()
        hex_color = log_colors.get(color, "#9CA3AF")
        self.text_edit.appendHtml(f'<span style="color:{hex_color}">{message}</span>')
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)

    def clear_log(self):
        self.text_edit.clear()

    def _copy_all(self):
        self.text_edit.selectAll()
        self.text_edit.copy()
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)

    def retranslateUi(self):
        self.title.setText(tr("log_title"))

    def _toggle_theme(self):
        if qconfig.theme == Theme.DARK:
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.DARK)

        self._theme_manager.update_theme(qconfig.theme)
        self._update_style()
