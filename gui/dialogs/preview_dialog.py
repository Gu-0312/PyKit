from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from qfluentwidgets import Dialog, PushButton, TextEdit, FluentIcon, MessageBox


class PreviewDialog(Dialog):
    def __init__(self, command_str: str, parent=None):
        super().__init__("命令预览", "", parent)
        self.command_str = command_str

        layout = self.vBoxLayout
        self.text_edit = TextEdit(self)
        self.text_edit.setPlainText(command_str)
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        btn_row = QHBoxLayout()
        copy_btn = PushButton("复制命令")
        copy_btn.clicked.connect(self._copy)
        btn_row.addWidget(copy_btn)
        close_btn = PushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _copy(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.command_str)
        MessageBox.show("成功", "命令已复制到剪贴板", self)
