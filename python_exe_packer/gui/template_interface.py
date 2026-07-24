import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (
    BodyLabel, LineEdit, PushButton, ListWidget,
    MessageBox, TextEdit
)
from utils.i18n import tr


class TemplateInterface(QWidget):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setAutoFillBackground(False)
        self.setStyleSheet("background-color: transparent;")
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        self.left_title = BodyLabel(tr("template_list"))
        left.addWidget(self.left_title)
        self.template_list = ListWidget()
        self.template_list.currentRowChanged.connect(self._on_select)
        left.addWidget(self.template_list)

        btn_row = QHBoxLayout()
        self.delete_btn = PushButton(tr("delete"))
        self.delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(self.delete_btn)
        self.export_btn = PushButton(tr("export"))
        self.export_btn.clicked.connect(self._export)
        btn_row.addWidget(self.export_btn)
        self.import_btn = PushButton(tr("import"))
        self.import_btn.clicked.connect(self._import_template)
        btn_row.addWidget(self.import_btn)
        left.addLayout(btn_row)

        right = QVBoxLayout()
        self.right_title = BodyLabel(tr("template_detail"))
        right.addWidget(self.right_title)
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText(tr("template_name"))
        right.addWidget(self.name_edit)

        self.desc_edit = TextEdit()
        self.desc_edit.setPlaceholderText(tr("template_desc"))
        right.addWidget(self.desc_edit)

        self.save_btn = PushButton(tr("save_template"))
        self.save_btn.clicked.connect(self._save)
        right.addWidget(self.save_btn)

        layout.addLayout(left, 1)
        layout.addLayout(right, 1)

    def retranslateUi(self):
        self.left_title.setText(tr("template_list"))
        self.right_title.setText(tr("template_detail"))
        self.delete_btn.setText(tr("delete"))
        self.export_btn.setText(tr("export"))
        self.import_btn.setText(tr("import"))
        self.save_btn.setText(tr("save_template"))
        self.name_edit.setPlaceholderText(tr("template_name"))
        self.desc_edit.setPlaceholderText(tr("template_desc"))

    def _refresh(self):
        self.template_list.clear()
        names = self.config_manager.get_template_names()
        self.template_list.addItems(names)

    def _on_select(self, index):
        if index < 0:
            return
        name = self.template_list.item(index).text()
        template = self.config_manager.get_template(name)
        if template:
            self.name_edit.setText(template.get("name", ""))
            self.desc_edit.setPlainText(
                json.dumps(template.get("config", {}), indent=2)
            )

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            MessageBox.warning(tr("hint"), tr("enter_template_name"), self)
            return
        config = self.config_manager.load_config()
        self.config_manager.save_template(name, config)
        self._refresh()

    def _delete(self):
        row = self.template_list.currentRow()
        if row < 0:
            return
        name = self.template_list.item(row).text()
        self.config_manager.delete_template(name)
        self._refresh()

    def _export(self):
        row = self.template_list.currentRow()
        if row < 0:
            return
        name = self.template_list.item(row).text()
        template = self.config_manager.get_template(name)
        path, _ = QFileDialog.getSaveFileName(
            self, tr("export_template"), f"{name}.json", "JSON (*.json)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2, ensure_ascii=False)

    def _import_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("import_template"), "", "JSON (*.json)"
        )
        if path:
            with open(path, "r", encoding="utf-8") as f:
                template = json.load(f)
            self.config_manager.save_template(
                template.get("name", tr("imported_template")),
                template.get("config", {})
            )
            self._refresh()
