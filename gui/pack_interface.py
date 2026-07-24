import os
import sys
import subprocess
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QInputDialog,
    QButtonGroup
)
from qfluentwidgets import (
    SimpleCardWidget, BodyLabel, LineEdit, PushButton,
    PrimaryPushButton, CheckBox, RadioButton, ComboBox,
    MessageBox, ProgressBar, ListWidget, ScrollArea
)
from core.dependency import DependencyAnalyzer
from gui.log_widget import LogWidget
from gui.dialogs.preview_dialog import PreviewDialog
from gui.dialogs.analyzer_dialog import AnalyzerDialog
from gui.dialogs.batch_pack_dialog import BatchPackDialog
from utils.venv_scanner import VenvScanner
from utils.i18n import tr
from _version import get_version


class PackInterface(QWidget):
    start_pack_signal = Signal(dict)
    stop_pack_signal = Signal()
    clean_build_signal = Signal(str)

    PRESETS = {
        "default": {
            "label_zh": "默认",
            "label_en": "Default",
            "config": {},
        },
        "min_size": {
            "label_zh": "最小体积",
            "label_en": "Minimal Size",
            "config": {
                "single_file": True,
                "windowed": True,
                "enable_upx": True,
                "auto_exclude": True,
                "custom_args": "--strip",
            },
        },
        "fast_debug": {
            "label_zh": "快速调试",
            "label_en": "Fast Debug",
            "config": {
                "single_file": False,
                "windowed": False,
                "enable_upx": False,
                "auto_exclude": False,
                "custom_args": "--debug all",
            },
        },
        "compat": {
            "label_zh": "兼容模式",
            "label_en": "Compatibility",
            "config": {
                "single_file": False,
                "windowed": True,
                "enable_upx": False,
                "auto_exclude": True,
                "custom_args": "",
            },
        },
    }

    def __init__(self, packer, config_manager, parent=None):
        super().__init__(parent)
        self.packer = packer
        self.config_manager = config_manager
        self.is_packing = False
        self._build_ui()
        self._connect_signals()
        # 加载保存的配置
        self._load_config()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        content = QHBoxLayout()

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent;")
        config_widget = QWidget()
        config_widget.setAutoFillBackground(False)
        config_widget.setStyleSheet("background-color: transparent;")
        config_layout = QVBoxLayout(config_widget)

        basic_card = SimpleCardWidget()
        basic_layout = QVBoxLayout(basic_card)
        self.basic_info_label = BodyLabel(tr("basic_info"))
        basic_layout.addWidget(self.basic_info_label)

        self.source_edit = LineEdit()
        self.source_edit.setPlaceholderText(tr("source_file"))
        src_row = QHBoxLayout()
        src_row.addWidget(self.source_edit)
        self.src_btn = PushButton(tr("source_file"))
        self.src_btn.clicked.connect(self._browse_source)
        src_row.addWidget(self.src_btn)
        basic_layout.addLayout(src_row)

        self.output_edit = LineEdit()
        self.output_edit.setPlaceholderText(tr("output_dir"))
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_edit)
        self.out_btn = PushButton(tr("output_dir"))
        self.out_btn.clicked.connect(self._browse_output)
        out_row.addWidget(self.out_btn)
        basic_layout.addLayout(out_row)

        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText(tr("output_name"))
        basic_layout.addWidget(self.name_edit)
        config_layout.addWidget(basic_card)

        options_card = SimpleCardWidget()
        options_layout = QVBoxLayout(options_card)
        self.options_label = BodyLabel(tr("pack_options"))
        options_layout.addWidget(self.options_label)

        mode_group = QButtonGroup(self)
        self.single_file_rb = RadioButton(tr("single_mode"))
        self.single_file_rb.setChecked(True)
        self.multi_file_rb = RadioButton(tr("multi_mode"))
        mode_group.addButton(self.single_file_rb)
        mode_group.addButton(self.multi_file_rb)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.single_file_rb)
        mode_row.addWidget(self.multi_file_rb)
        options_layout.addLayout(mode_row)

        self.windowed_cb = CheckBox(tr("hide_console"))
        self.windowed_cb.setChecked(True)
        options_layout.addWidget(self.windowed_cb)

        self.auto_clean_cb = CheckBox(tr("auto_clean"))
        self.auto_clean_cb.setChecked(True)
        options_layout.addWidget(self.auto_clean_cb)

        self.upx_cb = CheckBox(tr("enable_upx"))
        options_layout.addWidget(self.upx_cb)

        self.installer_cb = CheckBox(tr("create_installer"))
        options_layout.addWidget(self.installer_cb)

        self.auto_exclude_cb = CheckBox(tr("auto_exclude"))
        self.auto_exclude_cb.setChecked(True)
        options_layout.addWidget(self.auto_exclude_cb)

        self.auto_detect_deps_cb = CheckBox(tr("auto_detect_deps"))
        self.auto_detect_deps_cb.setChecked(True)
        options_layout.addWidget(self.auto_detect_deps_cb)

        self.auto_open_output_cb = CheckBox(tr("auto_open_output"))
        self.auto_open_output_cb.setChecked(True)
        options_layout.addWidget(self.auto_open_output_cb)

        config_layout.addWidget(options_card)

        preset_card = SimpleCardWidget()
        preset_layout = QVBoxLayout(preset_card)
        self.preset_label = BodyLabel(tr("preset"))
        preset_layout.addWidget(self.preset_label)
        self.preset_combo = ComboBox()
        self._rebuild_preset_combo()
        self.preset_combo.currentIndexChanged.connect(self._apply_preset)
        preset_layout.addWidget(self.preset_combo)
        config_layout.addWidget(preset_card)

        deps_card = SimpleCardWidget()
        deps_layout = QVBoxLayout(deps_card)
        self.deps_card_label = BodyLabel(tr("dep_management"))
        deps_layout.addWidget(self.deps_card_label)

        self.detect_btn = PushButton(tr("auto_detect"))
        self.detect_btn.clicked.connect(self._detect_deps)
        deps_layout.addWidget(self.detect_btn)

        self.deps_label = BodyLabel(tr("hidden_imports"))
        deps_layout.addWidget(self.deps_label)
        self.deps_list = ListWidget()
        deps_layout.addWidget(self.deps_list)
        dep_btn_row = QHBoxLayout()
        self.add_dep_btn = PushButton(tr("add"))
        self.add_dep_btn.clicked.connect(self._add_dep)
        dep_btn_row.addWidget(self.add_dep_btn)
        self.remove_dep_btn = PushButton(tr("remove_selected"))
        self.remove_dep_btn.clicked.connect(lambda: self._remove_selected(self.deps_list))
        dep_btn_row.addWidget(self.remove_dep_btn)
        deps_layout.addLayout(dep_btn_row)

        self.excl_label = BodyLabel(tr("exclude_modules"))
        deps_layout.addWidget(self.excl_label)
        self.excludes_list = ListWidget()
        deps_layout.addWidget(self.excludes_list)
        excl_btn_row = QHBoxLayout()
        self.add_excl_btn = PushButton(tr("add_exclude"))
        self.add_excl_btn.clicked.connect(self._add_exclude)
        excl_btn_row.addWidget(self.add_excl_btn)
        self.remove_excl_btn = PushButton(tr("remove_selected"))
        self.remove_excl_btn.clicked.connect(lambda: self._remove_selected(self.excludes_list))
        excl_btn_row.addWidget(self.remove_excl_btn)
        deps_layout.addLayout(excl_btn_row)
        config_layout.addWidget(deps_card)

        data_card = SimpleCardWidget()
        data_layout = QVBoxLayout(data_card)
        self.data_label = BodyLabel(tr("data_files"))
        data_layout.addWidget(self.data_label)
        self.data_list = ListWidget()
        data_layout.addWidget(self.data_list)
        data_btn_row = QHBoxLayout()
        self.add_data_btn = PushButton(tr("add_file"))
        self.add_data_btn.clicked.connect(self._add_data_file)
        data_btn_row.addWidget(self.add_data_btn)
        self.remove_data_btn = PushButton(tr("remove_selected"))
        self.remove_data_btn.clicked.connect(lambda: self._remove_selected(self.data_list))
        data_btn_row.addWidget(self.remove_data_btn)
        data_layout.addLayout(data_btn_row)
        config_layout.addWidget(data_card)

        adv_card = SimpleCardWidget()
        adv_layout = QVBoxLayout(adv_card)
        self.adv_label = BodyLabel(tr("advanced"))
        adv_layout.addWidget(self.adv_label)

        icon_row = QHBoxLayout()
        self.icon_edit = LineEdit()
        self.icon_edit.setPlaceholderText(tr("icon_file"))
        icon_row.addWidget(self.icon_edit)
        self.icon_btn = PushButton(tr("icon_file"))
        self.icon_btn.clicked.connect(self._browse_icon)
        icon_row.addWidget(self.icon_btn)
        adv_layout.addLayout(icon_row)

        self.version_edit = LineEdit()
        self.version_edit.setText(get_version())
        self.version_label = BodyLabel(tr("app_version"))
        adv_layout.addWidget(self.version_label)
        adv_layout.addWidget(self.version_edit)

        self.custom_args_edit = LineEdit()
        self.custom_args_edit.setPlaceholderText(tr("custom_args"))
        self.args_label = BodyLabel(tr("custom_args"))
        adv_layout.addWidget(self.args_label)
        adv_layout.addWidget(self.custom_args_edit)

        self.clean_btn = PushButton(tr("clean_build"))
        self.clean_btn.clicked.connect(self._on_clean_build)
        adv_layout.addWidget(self.clean_btn)

        self.upx_path_edit = LineEdit()
        self.upx_path_edit.setPlaceholderText(tr("upx_path"))
        upx_row = QHBoxLayout()
        upx_row.addWidget(self.upx_path_edit)
        self.upx_path_btn = PushButton(tr("browse"))
        self.upx_path_btn.clicked.connect(self._browse_upx)
        upx_row.addWidget(self.upx_path_btn)
        adv_layout.addLayout(upx_row)
        config_layout.addWidget(adv_card)

        py_card = SimpleCardWidget()
        py_layout = QVBoxLayout(py_card)
        self.py_label = BodyLabel(tr("python_interpreter"))
        py_layout.addWidget(self.py_label)
        py_row = QHBoxLayout()
        self.py_edit = LineEdit()
        self.py_edit.setPlaceholderText(tr("python_auto"))
        py_row.addWidget(self.py_edit)
        self.py_btn = PushButton(tr("browse"))
        self.py_btn.clicked.connect(self._browse_python)
        py_row.addWidget(self.py_btn)
        py_layout.addLayout(py_row)

        venv_btn_row = QHBoxLayout()
        self.scan_venv_btn = PushButton(tr("scan_venv"))
        self.scan_venv_btn.clicked.connect(self._scan_venv)
        venv_btn_row.addWidget(self.scan_venv_btn)
        self.create_venv_btn = PushButton(tr("create_venv"))
        self.create_venv_btn.clicked.connect(self._create_venv)
        venv_btn_row.addWidget(self.create_venv_btn)
        py_layout.addLayout(venv_btn_row)

        config_layout.addWidget(py_card)

        config_layout.addStretch()
        scroll.setWidget(config_widget)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.log_widget = LogWidget()
        right_layout.addWidget(self.log_widget)

        content.addWidget(scroll, 2)
        content.addWidget(right_panel, 1)
        main_layout.addLayout(content)

        bottom_bar = QHBoxLayout()
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        bottom_bar.addWidget(self.progress_bar)

        self.status_label = BodyLabel(tr("ready"))
        bottom_bar.addWidget(self.status_label)

        self.preview_btn = PushButton(tr("preview_cmd"))
        self.preview_btn.clicked.connect(self._preview_command)
        bottom_bar.addWidget(self.preview_btn)

        self.stop_btn = PushButton(tr("stop"))
        self.stop_btn.clicked.connect(self._stop_pack)
        self.stop_btn.setEnabled(False)
        bottom_bar.addWidget(self.stop_btn)

        self.pack_btn = PrimaryPushButton(tr("start_pack"))
        self.pack_btn.clicked.connect(self._start_pack)
        bottom_bar.addWidget(self.pack_btn)

        main_layout.addLayout(bottom_bar)

    def _apply_preset(self, index):
        key = self.preset_combo.itemData(index)
        if not key or key == "default":
            return
        preset = self.PRESETS.get(key, {})
        cfg = preset.get("config", {})
        for k, v in cfg.items():
            if k == "single_file":
                self.single_file_rb.setChecked(v)
                self.multi_file_rb.setChecked(not v)
            elif k == "windowed":
                self.windowed_cb.setChecked(v)
            elif k == "enable_upx":
                self.upx_cb.setChecked(v)
            elif k == "custom_args":
                self.custom_args_edit.setText(v)

    def _rebuild_preset_combo(self):
        current_key = self.preset_combo.itemData(self.preset_combo.currentIndex())
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        for key, p in self.PRESETS.items():
            label_key = f"preset_{key}"
            label = tr(label_key)
            self.preset_combo.addItem(label, userData=key)
        if current_key is not None:
            idx = self.preset_combo.findData(current_key)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.blockSignals(False)

    def retranslateUi(self):
        self.basic_info_label.setText(tr("basic_info"))
        self.source_edit.setPlaceholderText(tr("source_file"))
        self.src_btn.setText(tr("source_file"))
        self.output_edit.setPlaceholderText(tr("output_dir"))
        self.out_btn.setText(tr("output_dir"))
        self.name_edit.setPlaceholderText(tr("output_name"))
        self.options_label.setText(tr("pack_options"))
        self.single_file_rb.setText(tr("single_mode"))
        self.multi_file_rb.setText(tr("multi_mode"))
        self.windowed_cb.setText(tr("hide_console"))
        self.auto_clean_cb.setText(tr("auto_clean"))
        self.upx_cb.setText(tr("enable_upx"))
        self.installer_cb.setText(tr("create_installer"))
        self.auto_exclude_cb.setText(tr("auto_exclude"))
        self.auto_detect_deps_cb.setText(tr("auto_detect_deps"))
        self.auto_open_output_cb.setText(tr("auto_open_output"))
        self.preset_label.setText(tr("preset"))
        self._rebuild_preset_combo()
        self.deps_card_label.setText(tr("dep_management"))
        self.detect_btn.setText(tr("auto_detect"))
        self.deps_label.setText(tr("hidden_imports"))
        self.excl_label.setText(tr("exclude_modules"))
        self.add_dep_btn.setText(tr("add"))
        self.remove_dep_btn.setText(tr("remove_selected"))
        self.add_excl_btn.setText(tr("add_exclude"))
        self.remove_excl_btn.setText(tr("remove_selected"))
        self.data_label.setText(tr("data_files"))
        self.add_data_btn.setText(tr("add_file"))
        self.remove_data_btn.setText(tr("remove_selected"))
        self.adv_label.setText(tr("advanced"))
        self.icon_edit.setPlaceholderText(tr("icon_file"))
        self.icon_btn.setText(tr("icon_file"))
        self.version_label.setText(tr("app_version"))
        self.args_label.setText(tr("custom_args"))
        self.custom_args_edit.setPlaceholderText(tr("custom_args"))
        self.clean_btn.setText(tr("clean_build"))
        self.upx_path_edit.setPlaceholderText(tr("upx_path"))
        self.upx_path_btn.setText(tr("browse"))
        self.py_label.setText(tr("python_interpreter"))
        self.py_edit.setPlaceholderText(tr("python_auto"))
        self.py_btn.setText(tr("browse"))
        self.scan_venv_btn.setText(tr("scan_venv"))
        self.create_venv_btn.setText(tr("create_venv"))
        self.status_label.setText(tr("ready"))
        self.preview_btn.setText(tr("preview_cmd"))
        self.analyze_btn.setText(tr("analyze_btn"))
        self.batch_btn.setText(tr("batch_btn"))
        self.stop_btn.setText(tr("stop"))
        self.pack_btn.setText(tr("start_pack"))
        self.log_widget.retranslateUi()

    def _set_all_enabled(self, enabled):
        """设置所有控件的启用状态"""
        # 文件选择相关控件
        self.source_edit.setEnabled(enabled)
        self.src_btn.setEnabled(enabled)
        self.output_edit.setEnabled(enabled)
        self.out_btn.setEnabled(enabled)
        self.name_edit.setEnabled(enabled)
        
        # 打包选项相关控件
        self.single_file_rb.setEnabled(enabled)
        self.multi_file_rb.setEnabled(enabled)
        self.windowed_cb.setEnabled(enabled)
        self.auto_clean_cb.setEnabled(enabled)
        self.upx_cb.setEnabled(enabled)
        self.installer_cb.setEnabled(enabled)
        self.auto_exclude_cb.setEnabled(enabled)
        self.auto_detect_deps_cb.setEnabled(enabled)
        self.auto_open_output_cb.setEnabled(enabled)
        
        # 预设选择
        self.preset_combo.setEnabled(enabled)
        
        # 依赖管理相关控件
        self.detect_btn.setEnabled(enabled)
        self.deps_list.setEnabled(enabled)
        self.add_dep_btn.setEnabled(enabled)
        self.remove_dep_btn.setEnabled(enabled)
        self.excludes_list.setEnabled(enabled)
        self.add_excl_btn.setEnabled(enabled)
        self.remove_excl_btn.setEnabled(enabled)
        
        # 数据文件相关控件
        self.data_list.setEnabled(enabled)
        self.add_data_btn.setEnabled(enabled)
        self.remove_data_btn.setEnabled(enabled)
        
        # 高级选项相关控件
        self.icon_edit.setEnabled(enabled)
        self.icon_btn.setEnabled(enabled)
        self.custom_args_edit.setEnabled(enabled)
        self.upx_path_edit.setEnabled(enabled)
        self.upx_path_btn.setEnabled(enabled)
        self.py_edit.setEnabled(enabled)
        self.py_btn.setEnabled(enabled)
        self.scan_venv_btn.setEnabled(enabled)
        self.clean_btn.setEnabled(enabled)
        
        # 预览按钮
        self.preview_btn.setEnabled(enabled)

    def _connect_signals(self):
        self.packer.log_signal.connect(self.log_widget.add_log)
        self.packer.progress_signal.connect(self._on_progress)
        self.packer.finished_signal.connect(self._on_pack_finished)

    def _on_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)

    def _on_pack_finished(self, success, config, duration):
        self.is_packing = False
        self.pack_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 重新启用所有控件
        self._set_all_enabled(True)
        
        # 保存配置（记忆功能）
        self._save_config()

    def _browse_python(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("python_interpreter"), "", "Python (*.exe);;All Files (*)")
        if path:
            self.py_edit.setText(path)

    def _browse_upx(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("upx_path"), "", "UPX (upx.exe);;All Files (*)")
        if path:
            self.upx_path_edit.setText(path)

    def _scan_venv(self):
        source = self.source_edit.text().strip()
        start_dir = os.path.dirname(source) if source else None

        scanner = VenvScanner()
        results = scanner.scan_all(start_dir)

        if not results:
            MessageBox.information(self, tr("venv_dialog_title"), tr("venv_no_found"))
            return

        items = [f"[{name}] {path}" for name, path in results]
        item, ok = QInputDialog.getItem(self, tr("venv_dialog_title"), tr("venv_scan_hint"), items, 0, False)
        if ok and item:
            idx = items.index(item)
            self.py_edit.setText(results[idx][1])

    def _create_venv(self):
        source = self.source_edit.text().strip()
        project_dir = os.path.dirname(source) if source else os.getcwd()

        name, ok = QInputDialog.getText(self, tr("create_venv"), tr("venv_name"), text="venv")
        if not ok or not name.strip():
            return

        venv_path = os.path.join(project_dir, name.strip())
        if os.path.exists(venv_path):
            MessageBox.warning(self, tr("create_venv"), tr("venv_exists"))
            return

        reply = MessageBox(
            tr("create_venv"),
            f"{tr('venv_creating')}\n{venv_path}",
            self
        )
        reply.cancelButton.setText(tr("cancel"))
        reply.yesButton.setText(tr("ok"))
        if not reply.exec():
            return

        self.log_widget.add_log(f"[INFO] {tr('venv_creating')}: {venv_path}")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "venv", venv_path],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                python_exe = os.path.join(venv_path, "Scripts", "python.exe")
                if os.path.exists(python_exe):
                    self.py_edit.setText(python_exe)
                self.log_widget.add_log(f"[SUCCESS] {tr('venv_created')}: {venv_path}")
            else:
                self.log_widget.add_log(f"[ERROR] {tr('venv_creating')}: {result.stderr}")
        except Exception as e:
            self.log_widget.add_log(f"[ERROR] {tr('venv_creating')}: {e}")

    def _open_analyzer(self):
        dialog = AnalyzerDialog(self)
        dialog.retranslateUi()
        dialog.exec()

    def _open_batch(self):
        dialog = BatchPackDialog(self.packer, self.config_manager, self)
        dialog.retranslateUi()
        dialog.exec()

    def _preview_command(self):
        config = self.get_config()
        try:
            cmd, _ = self.packer.build_command(config)
            cmd_str = " ".join(cmd)
            dialog = PreviewDialog(cmd_str, self)
            dialog.exec()
        except Exception as e:
            MessageBox.warning(tr("advanced"), f"生成命令失败: {str(e)}", self)

    def _start_pack(self):
        if self.is_packing:
            return
        config = self.get_config()
        errors = self.packer.validate_config(config)
        if errors:
            MessageBox.warning(tr("pack_options"), "\n".join(errors), self)
            return

        self.is_packing = True
        self.pack_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_widget.clear_log()
        self.progress_bar.setValue(0)
        
        # 禁用其他所有控件
        self._set_all_enabled(False)
        
        self.start_pack_signal.emit(config)

    def _stop_pack(self):
        self.stop_pack_signal.emit()
        self.is_packing = False
        self.pack_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # 重新启用所有控件
        self._set_all_enabled(True)
        
        self.log_widget.add_log(f"[WARN] {tr('pack_cancelled')}")

    def _get_data_files(self):
        result = []
        for i in range(self.data_list.count()):
            text = self.data_list.item(i).text()
            if " -> " in text:
                src, dst = text.split(" -> ", 1)
                result.append((src.strip(), dst.strip()))
        return result

    def get_config(self):
        return {
            "source_file": self.source_edit.text().strip(),
            "output_dir": self.output_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "single_file": self.single_file_rb.isChecked(),
            "windowed": self.windowed_cb.isChecked(),
            "icon": self.icon_edit.text().strip(),
            "auto_clean": self.auto_clean_cb.isChecked(),
            "auto_exclude": self.auto_exclude_cb.isChecked(),
            "auto_detect_deps": self.auto_detect_deps_cb.isChecked(),
            "auto_open_output": self.auto_open_output_cb.isChecked(),
            "enable_upx": self.upx_cb.isChecked(),
            "create_installer": self.installer_cb.isChecked(),
            "app_version": self.version_edit.text().strip(),
            "custom_args": self.custom_args_edit.text().strip(),
            "hidden_imports": [self.deps_list.item(i).text() for i in range(self.deps_list.count())],
            "excludes": [self.excludes_list.item(i).text() for i in range(self.excludes_list.count())],
            "data_files": self._get_data_files(),
            "upx_path": self.upx_path_edit.text().strip(),
            "python_interpreter": self.py_edit.text().strip(),
            "auto_detect_venv": True,
        }

    def set_config(self, config):
        if config.get("source_file"):
            self.source_edit.setText(config["source_file"])
        if config.get("output_dir"):
            self.output_edit.setText(config["output_dir"])
        if config.get("name"):
            self.name_edit.setText(config["name"])
        if config.get("single_file") is not None:
            self.single_file_rb.setChecked(config["single_file"])
            self.multi_file_rb.setChecked(not config["single_file"])
        if config.get("windowed") is not None:
            self.windowed_cb.setChecked(config["windowed"])
        if config.get("icon"):
            self.icon_edit.setText(config["icon"])
        if config.get("auto_clean") is not None:
            self.auto_clean_cb.setChecked(config["auto_clean"])
        if config.get("enable_upx") is not None:
            self.upx_cb.setChecked(config["enable_upx"])
        if config.get("create_installer") is not None:
            self.installer_cb.setChecked(config["create_installer"])
        if config.get("app_version"):
            self.version_edit.setText(config["app_version"])
        if config.get("custom_args"):
            self.custom_args_edit.setText(config["custom_args"])
        if config.get("hidden_imports"):
            self.deps_list.clear()
            for dep in config["hidden_imports"]:
                self.deps_list.addItem(dep)
        if config.get("excludes"):
            self.excludes_list.clear()
            for exc in config["excludes"]:
                self.excludes_list.addItem(exc)
        if config.get("data_files"):
            self.data_list.clear()
            for src, dst in config["data_files"]:
                self.data_list.addItem(f"{src} -> {dst}")
        if config.get("python_interpreter"):
            self.py_edit.setText(config["python_interpreter"])
        if config.get("auto_exclude") is not None:
            self.auto_exclude_cb.setChecked(config["auto_exclude"])
        if config.get("auto_detect_deps") is not None:
            self.auto_detect_deps_cb.setChecked(config["auto_detect_deps"])
        if config.get("auto_open_output") is not None:
            self.auto_open_output_cb.setChecked(config["auto_open_output"])
        if config.get("upx_path"):
            self.upx_path_edit.setText(config["upx_path"])

    def _load_config(self):
        """加载保存的配置"""
        config = self.config_manager.load_config()
        self.set_config(config)

    def _save_config(self):
        """保存当前配置"""
        config = self.get_config()
        self.config_manager.save_config(config)

    def _on_clean_build(self):
        source = self.source_edit.text().strip()
        project_dir = os.path.dirname(source) if source else os.getcwd()
        reply = MessageBox(tr("clean_build"), tr("clean_confirm"), self)
        if reply.exec():
            self.clean_build_signal.emit(project_dir)

    def _browse_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("source_file"), "", "Python (*.py *.pyw);;所有文件 (*.*)"
        )
        if path:
            self.source_edit.setText(path)
            name = os.path.splitext(os.path.basename(path))[0]
            if not self.name_edit.text():
                self.name_edit.setText(name)

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, tr("output_dir"))
        if path:
            self.output_edit.setText(path)

    def _browse_icon(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("icon_file"), "", "图标 (*.ico);;所有文件 (*.*)"
        )
        if path:
            self.icon_edit.setText(path)

    def _detect_deps(self):
        source = self.source_edit.text().strip()
        if not source or not os.path.isfile(source):
            MessageBox.warning(tr("pack_options"), tr("no_source"), self)
            return
        self.deps_list.clear()
        analyzer = DependencyAnalyzer()
        deps = analyzer.get_hidden_imports(source)
        for d in deps:
            self.deps_list.addItem(d)

    def _add_dep(self):
        text, ok = QInputDialog.getText(self, tr("add"), tr("hidden_imports"))
        if ok and text.strip():
            self.deps_list.addItem(text.strip())

    def _add_exclude(self):
        text, ok = QInputDialog.getText(self, tr("add_exclude"), tr("exclude_modules"))
        if ok and text.strip():
            self.excludes_list.addItem(text.strip())

    def _remove_selected(self, lst):
        row = lst.currentRow()
        if row >= 0:
            lst.takeItem(row)

    def _add_data_file(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("data_file_source"))
        if not path:
            return
        dest, ok = QInputDialog.getText(self, tr("data_file_dest"), tr("data_file_dest"), text=".")
        if ok and dest.strip():
            self.data_list.addItem(f"{path} -> {dest.strip()}")
