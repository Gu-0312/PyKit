# QFluentWidgets 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) for syntax tracking.

**Goal:** 将 Python EXE Packer 从 ttkbootstrap/tkinter 迁移至 QFluentWidgets/PySide6

**Architecture:** 3 层架构——app 层管理生命周期，gui 层用 QFluentWidgets 实现 Fluent 导航界面，core/utils 层保持纯 Python 业务逻辑通过 Qt 信号与 GUI 通信

**Tech Stack:** PySide6, qfluentwidgets, PyInstaller

---

## 文件结构总览

### 新建文件
| 文件 | 说明 |
|------|------|
| `_metadata.py` | 应用元数据 |
| `app/__init__.py` | 包声明 |
| `app/application.py` | QApplication + 单例 + 主题 |
| `gui/__init__.py` | 包声明 |
| `gui/log_widget.py` | 日志组件 |
| `gui/pack_interface.py` | 打包页面 |
| `gui/template_interface.py` | 模板管理页面 |
| `gui/history_interface.py` | 历史统计页面 |
| `gui/env_interface.py` | 环境管理页面 |
| `gui/about_interface.py` | 关于页面 |
| `gui/dialogs/__init__.py` | 包声明 |
| `gui/dialogs/preview_dialog.py` | 命令预览 |
| `gui/dialogs/pyi_version_dialog.py` | PyInstaller 版本管理 |
| `resources/icons/` | 图标目录 |

### 修改文件
| 文件 | 说明 |
|------|------|
| `requirements.txt` | 替换依赖 |
| `utils/config_manager.py` | QStandardPaths 替代 platformdirs |
| `utils/log_utils.py` | 精简，移除 tkinter 回调 |
| `core/packer.py` | 改为 QObject + 信号 |
| `main.py` | 完全重写 |

### 删除文件
| 文件 | 说明 |
|------|------|
| `gui/main_window.py` | ttkbootstrap 实现 |
| `gui/config_panel.py` | ttkbootstrap 实现 |
| `gui/log_panel.py` | ttkbootstrap 实现 |
| `gui/template_manager.py` | ttkbootstrap 实现 |
| `gui/stats_dialog.py` | ttkbootstrap 实现 |
| `gui/env_setup_dialog.py` | ttkbootstrap 实现 |
| `gui/about_dialog.py` | ttkbootstrap 实现 |
| `gui/upx_download_dialog.py` | ttkbootstrap 实现 |
| `gui/pyi_version_dialog.py` | ttkbootstrap 实现 |
| `gui/style.py` | ttkbootstrap 样式 |
| `create_icon.py` | 不再需要 |
| `test_delete.py` | 测试文件 |
| `启动程序.bat` | 启动脚本 |
| `启动程序.vbs` | 启动脚本 |

---

## Phase 1: 基础架构

### Task 1: 更新 requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **替换依赖**

```
PySide6>=6.5.0
PySide6-Fluent-Widgets>=1.0.0
Pillow>=10.0.0
```

移除 `ttkbootstrap` 和 `platformdirs`。

### Task 2: 创建 _metadata.py

**Files:**
- Create: `_metadata.py`

- [ ] **写入元数据文件**

```python
APP_NAME = "Python一键打包EXE"
APP_AUTHOR = "PyPacker"
APP_VERSION = "1.1.0"
APP_DESCRIPTION = "基于 PyInstaller 的 Python 一键打包工具"
APP_HOMEPAGE = ""
APP_COPYRIGHT = f"Copyright (C) 2026 {APP_AUTHOR}"
```

### Task 3: 创建 app 包

**Files:**
- Create: `app/__init__.py`
- Create: `app/application.py`

- [ ] **创建 `app/__init__.py`**

空文件。

- [ ] **创建 `app/application.py`**

```python
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator, Theme, setTheme
from _metadata import APP_NAME


class Application(QApplication):
    def __init__(self, args=None):
        super().__init__(args or sys.argv)
        self.setApplicationName(APP_NAME)
        self.setOrganizationName("PyPacker")
        self.setQuitOnLastWindowClosed(True)
        setTheme(Theme.AUTO)

    @staticmethod
    def ensure_single_instance():
        from core.single_instance import SingleInstance
        instance = SingleInstance()
        if not instance.acquire():
            return False
        return instance
```

### Task 4: 创建 gui 包和目录结构

**Files:**
- Create: `gui/__init__.py`
- Create: `gui/dialogs/__init__.py`
- Create: `resources/icons/` 目录

- [ ] **创建包文件和目录**

```bash
mkdir -p gui/dialogs resources/icons
```

`gui/__init__.py`:
```python
from .main_window import MainWindow
```

`gui/dialogs/__init__.py`: 空文件。

---

## Phase 2: 核心层适配

### Task 5: 简化 utils/log_utils.py

**Files:**
- Modify: `utils/log_utils.py`

仅保留纯 Python logger，移除所有 tkinter 回调逻辑。适配 Packer 的信号模式后，日志回调不再需要。

```python
import logging


class Logger(logging.Logger):
    def __init__(self, name="PyPacker"):
        super().__init__(name)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
        ))
        self.addHandler(handler)
        self.setLevel(logging.INFO)
        self.gui_callback = None

    def set_gui_callback(self, callback):
        self.gui_callback = callback

    def _log_with_gui(self, level, msg, *args, **kwargs):
        super()._log(level, msg, args, **kwargs)
        if self.gui_callback:
            self.gui_callback(msg)

    def info(self, msg, *args, **kwargs):
        self._log_with_gui(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log_with_gui(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log_with_gui(logging.ERROR, msg, *args, **kwargs)


_logger = None


def get_logger():
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger
```

### Task 6: 重构 core/packer.py 为信号驱动

**Files:**
- Modify: `core/packer.py`

将 Packer 改为继承 QObject，使用 Signal 替代函数引用回调。只改动类定义和信号部分，业务逻辑不变。

- [ ] **修改 Packer 类定义**

在文件顶部增加导入：
```python
from PySide6.QtCore import QObject, Signal
```

将类定义和 `__init__` 改为：
```python
class Packer(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(int, str)
    finished_signal = Signal(bool, dict, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dependency_analyzer = DependencyAnalyzer()
        self.cache_cleaner = CacheCleaner()
        self.inno_setup = InnoSetup()
        self.upx_compressor = UPXCompressor()
```

移除旧的回调设置方法 `set_log_callback`、`set_progress_callback`，改为：
```python
def set_log_callback(self, callback):
    self.log_signal.connect(callback)

def set_progress_callback(self, callback):
    self.progress_signal.connect(callback)
```

将所有 `self._log(...)` 改为 `self.log_signal.emit(...)`。
将所有 `self._progress(...)` 改为 `self.progress_signal.emit(...)`。

在 `pack()` 方法的成功/失败路径末尾调用 `self.finished_signal.emit(success, config, duration)`，移除调用处的手动回调处理。

此改动不影响工具函数 `_find_pyinstaller_command`、`build_command`、`run_pyinstaller`、`validate_config` 等方法。InnoSetup 和 NSIS 的 log/progress 回调保留函数引用方式（它们不是 QObject）。

### Task 7: 适配 utils/config_manager.py

**Files:**
- Modify: `utils/config_manager.py`

- [ ] **替换 platformdirs 为 QStandardPaths**

```python
import os
import json
import tempfile
import logging
from PySide6.QtCore import QStandardPaths
from _version import get_version

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self):
        self.config_dir = QStandardPaths.writableLocation(
            QStandardPaths.AppLocalDataLocation
        )
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.history_file = os.path.join(self.config_dir, "history.json")
        self.templates_file = os.path.join(self.config_dir, "templates.json")
        # ... default_config 保持不变 ...
```

其余方法 `load_config`、`save_config`、`load_history`、`add_to_history`、`load_templates`、`save_template`、`delete_template`、`get_stats` 等保持原样不变。

---

## Phase 3: GUI 组件

### Task 8: 创建 gui/log_widget.py

**Files:**
- Create: `gui/log_widget.py`

- [ ] **写入日志组件**

```python
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import ListWidget, PushButton, BodyLabel, ToolButton, FluentIcon


class LogWidget(QWidget):
    LOG_COLORS = {
        "INFO": "#9CA3AF",
        "SUCCESS": "#10B981",
        "WARNING": "#F59E0B",
        "ERROR": "#EF4444",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        title = BodyLabel("运行日志")
        header.addWidget(title)
        header.addStretch()
        clear_btn = ToolButton(FluentIcon.DELETE)
        clear_btn.clicked.connect(self.clear_log)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self.list_widget = ListWidget(self)
        self.list_widget.setAlternatingRowColors(True)
        layout.addWidget(self.list_widget)

    def add_log(self, message: str):
        color = "INFO"
        if message.startswith("[SUCCESS]") or "成功" in message:
            color = "SUCCESS"
        elif message.startswith("[WARN]") or "WARN" in message or "警告" in message:
            color = "WARNING"
        elif message.startswith("[ERROR]") or "ERROR" in message or "失败" in message:
            color = "ERROR"
        self.list_widget.addItem(message)
        item = self.list_widget.item(self.list_widget.count() - 1)
        item.setForeground(QColor(self.LOG_COLORS.get(color, "#9CA3AF")))
        self.list_widget.scrollToBottom()

    def clear_log(self):
        self.list_widget.clear()
```

### Task 9: 创建 gui/pack_interface.py

**Files:**
- Create: `gui/pack_interface.py`

这是最大的组件。包含打包配置表单 + 日志面板 + 操作按钮。

- [ ] **写入打包页面**

```python
import os
import sys
import threading
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QInputDialog,
    QScrollArea, QFrame
)
from qfluentwidgets import (
    CardWidget, BodyLabel, LineEdit, PushButton, ProgressBar,
    CheckBox, RadioButton, ButtonGroup, ComboBox, ExpandSettingCard,
    HeaderCardWidget, FluentIcon, InfoBadge, InfoLevel, MessageBox,
    ListWidget, StateToolTip
)
from core.dependency import DependencyAnalyzer
from utils.venv_scanner import VenvScanner
from gui.log_widget import LogWidget


class PackInterface(QWidget):
    start_pack_signal = Signal(dict)
    stop_pack_signal = Signal()

    def __init__(self, packer, config_manager, parent=None):
        super().__init__(parent)
        self.packer = packer
        self.config_manager = config_manager
        self.is_packing = False
        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧配置区
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        # --- 基础信息卡片 ---
        basic_card = CardWidget()
        basic_layout = basic_card.vBoxLayout

        basic_layout.addWidget(BodyLabel("基础信息"))
        self.source_edit = LineEdit()
        self.source_edit.setPlaceholderText("选择 Python 源文件 (.py)")
        src_row = QHBoxLayout()
        src_row.addWidget(self.source_edit)
        src_btn = PushButton("浏览")
        src_btn.clicked.connect(self._browse_source)
        src_row.addWidget(src_btn)
        basic_layout.addLayout(src_row)

        self.output_edit = LineEdit()
        self.output_edit.setPlaceholderText("选择输出目录")
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_edit)
        out_btn = PushButton("浏览")
        out_btn.clicked.connect(self._browse_output)
        out_row.addWidget(out_btn)
        basic_layout.addLayout(out_row)

        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("输出文件名（不含扩展名）")
        basic_layout.addWidget(self.name_edit)

        config_layout.addWidget(basic_card)

        # --- 打包选项卡片 ---
        options_card = CardWidget()
        options_layout = options_card.vBoxLayout
        options_layout.addWidget(BodyLabel("打包选项"))

        self.single_file_cb = CheckBox("单文件模式 (-F)")
        self.single_file_cb.setChecked(True)
        options_layout.addWidget(self.single_file_cb)

        self.windowed_cb = CheckBox("隐藏控制台窗口 (-w)")
        self.windowed_cb.setChecked(True)
        options_layout.addWidget(self.windowed_cb)

        self.auto_clean_cb = CheckBox("自动清理缓存")
        self.auto_clean_cb.setChecked(True)
        options_layout.addWidget(self.auto_clean_cb)

        self.upx_cb = CheckBox("启用 UPX 压缩（如已安装）")
        options_layout.addWidget(self.upx_cb)

        self.installer_cb = CheckBox("生成 Windows 安装包")
        options_layout.addWidget(self.installer_cb)

        self.installer_type = ComboBox()
        self.installer_type.addItems(["Inno Setup", "NSIS"])
        options_layout.addWidget(self.installer_type)

        config_layout.addWidget(options_card)

        # --- 依赖管理卡片 ---
        deps_card = CardWidget()
        deps_layout = deps_card.vBoxLayout
        deps_layout.addWidget(BodyLabel("依赖管理"))

        detect_btn = PushButton("自动检测依赖")
        detect_btn.clicked.connect(self._detect_deps)
        deps_layout.addWidget(detect_btn)

        deps_label = BodyLabel("隐藏导入:")
        deps_layout.addWidget(deps_label)
        self.deps_list = ListWidget()
        deps_layout.addWidget(self.deps_list)

        excl_label = BodyLabel("排除模块:")
        deps_layout.addWidget(excl_label)
        self.excludes_list = ListWidget()
        deps_layout.addWidget(self.excludes_list)

        deps_btn_row = QHBoxLayout()
        add_dep_btn = PushButton("添加")
        add_dep_btn.clicked.connect(self._add_dep)
        deps_btn_row.addWidget(add_dep_btn)
        add_excl_btn = PushButton("添加排除")
        add_excl_btn.clicked.connect(self._add_exclude)
        deps_btn_row.addWidget(add_excl_btn)
        deps_layout.addLayout(deps_btn_row)

        config_layout.addWidget(deps_card)

        # --- 高级选项卡片 ---
        adv_card = CardWidget()
        adv_layout = adv_card.vBoxLayout
        adv_layout.addWidget(BodyLabel("高级选项"))

        icon_row = QHBoxLayout()
        self.icon_edit = LineEdit()
        self.icon_edit.setPlaceholderText("图标文件 (.ico)")
        icon_row.addWidget(self.icon_edit)
        icon_btn = PushButton("浏览")
        icon_btn.clicked.connect(self._browse_icon)
        icon_row.addWidget(icon_btn)
        adv_layout.addLayout(icon_row)

        self.version_edit = LineEdit()
        self.version_edit.setText("1.0.0")
        adv_layout.addWidget(BodyLabel("应用版本:"))
        adv_layout.addWidget(self.version_edit)

        self.custom_args_edit = LineEdit()
        self.custom_args_edit.setPlaceholderText("PyInstaller 额外参数（空格分隔）")
        adv_layout.addWidget(BodyLabel("自定义参数:"))
        adv_layout.addWidget(self.custom_args_edit)

        config_layout.addWidget(adv_card)
        config_layout.addStretch()

        scroll.setWidget(config_widget)

        # 右侧日志区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.log_widget = LogWidget()
        right_layout.addWidget(self.log_widget)

        # 底部操作栏（放在最外层）
        main_layout.addWidget(scroll, 2)
        main_layout.addWidget(right_panel, 1)

    def _connect_signals(self):
        self.packer.log_signal.connect(self.log_widget.add_log)

    def get_config(self):
        return {
            "source_file": self.source_edit.text().strip(),
            "output_dir": self.output_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "single_file": self.single_file_cb.isChecked(),
            "windowed": self.windowed_cb.isChecked(),
            "icon": self.icon_edit.text().strip(),
            "auto_clean": self.auto_clean_cb.isChecked(),
            "auto_detect_deps": False,
            "auto_open_output": True,
            "enable_upx": self.upx_cb.isChecked(),
            "create_installer": self.installer_cb.isChecked(),
            "installer_type": "inno" if self.installer_type.currentIndex() == 0 else "nsis",
            "app_version": self.version_edit.text().strip(),
            "custom_args": self.custom_args_edit.text().strip(),
            "hidden_imports": [self.deps_list.item(i).text() for i in range(self.deps_list.count())],
            "excludes": [self.excludes_list.item(i).text() for i in range(self.excludes_list.count())],
            "data_files": [],
            "python_interpreter": "",
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
            self.single_file_cb.setChecked(config["single_file"])
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

    def _browse_source(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择源文件", "", "Python (*.py *.pyw);;所有文件 (*.*)"
        )
        if path:
            self.source_edit.setText(path)

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_edit.setText(path)

    def _browse_icon(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图标", "", "图标 (*.ico);;所有文件 (*.*)"
        )
        if path:
            self.icon_edit.setText(path)

    def _detect_deps(self):
        source = self.source_edit.text().strip()
        if not source or not os.path.isfile(source):
            MessageBox.warning("提示", "请先选择有效的 Python 源文件", self)
            return
        self.deps_list.clear()
        analyzer = DependencyAnalyzer()
        deps = analyzer.get_hidden_imports(source)
        for d in deps:
            self.deps_list.addItem(d)

    def _add_dep(self):
        text, ok = QInputDialog.getText(self, "添加依赖", "模块名:")
        if ok and text.strip():
            self.deps_list.addItem(text.strip())

    def _add_exclude(self):
        text, ok = QInputDialog.getText(self, "添加排除", "模块名:")
        if ok and text.strip():
            self.excludes_list.addItem(text.strip())

    def clear_log(self):
        self.log_widget.clear_log()
```

### Task 10: 创建 gui/template_interface.py

**Files:**
- Create: `gui/template_interface.py`

```python
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import (
    CardWidget, BodyLabel, LineEdit, PushButton, ListWidget,
    MessageBox, FluentIcon, TextEdit
)


class TemplateInterface(QWidget):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        left.addWidget(BodyLabel("模板列表"))
        self.template_list = ListWidget()
        self.template_list.currentRowChanged.connect(self._on_select)
        left.addWidget(self.template_list)

        btn_row = QHBoxLayout()
        delete_btn = PushButton("删除")
        delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(delete_btn)
        export_btn = PushButton("导出")
        export_btn.clicked.connect(self._export)
        btn_row.addWidget(export_btn)
        import_btn = PushButton("导入")
        import_btn.clicked.connect(self._import_template)
        btn_row.addWidget(import_btn)
        left.addLayout(btn_row)

        right = QVBoxLayout()
        right.addWidget(BodyLabel("模板详情"))
        self.name_edit = LineEdit()
        self.name_edit.setPlaceholderText("模板名称")
        right.addWidget(self.name_edit)

        self.desc_edit = TextEdit()
        self.desc_edit.setPlaceholderText("模板描述（JSON 配置内容）")
        right.addWidget(self.desc_edit)

        save_btn = PushButton("保存模板")
        save_btn.clicked.connect(self._save)
        right.addWidget(save_btn)

        layout.addLayout(left, 1)
        layout.addLayout(right, 1)

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
            MessageBox.warning("提示", "请输入模板名称", self)
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
            self, "导出模板", f"{name}.json", "JSON (*.json)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2, ensure_ascii=False)

    def _import_template(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入模板", "", "JSON (*.json)"
        )
        if path:
            with open(path, "r", encoding="utf-8") as f:
                template = json.load(f)
            self.config_manager.save_template(
                template.get("name", "导入模板"),
                template.get("config", {})
            )
            self._refresh()
```

### Task 11: 创建 gui/history_interface.py

**Files:**
- Create: `gui/history_interface.py`

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
    QTableWidget, QTableWidgetItem
)
from qfluentwidgets import (
    CardWidget, BodyLabel, PushButton, FluentIcon, MessageBox
)


class HistoryInterface(QWidget):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # 统计卡片
        stats_card = CardWidget()
        stats_layout = stats_card.vBoxLayout
        self.stats_label = BodyLabel("统计信息加载中...")
        stats_layout.addWidget(self.stats_label)
        layout.addWidget(stats_card)

        # 表格
        self.table = QTableWidget(self)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        refresh_btn = PushButton("刷新")
        refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(refresh_btn)
        clear_btn = PushButton("清空历史")
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

    def _refresh(self):
        stats = self.config_manager.get_stats()
        self.stats_label.setText(
            f"总次数: {stats['total_count']}  |  "
            f"成功: {stats['success_count']}  |  "
            f"失败: {stats['fail_count']}  |  "
            f"成功率: {stats['success_rate']}%  |  "
            f"平均耗时: {stats['avg_duration_str']}  |  "
            f"最近: {stats['latest_time']}"
        )

        history = self.config_manager.load_history(max_count=50)
        self.table.setRowCount(len(history))
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["时间", "源文件", "模式", "结果", "耗时"])

        for i, h in enumerate(history):
            self.table.setItem(i, 0, QTableWidgetItem(h.get("timestamp", "")))
            self.table.setItem(i, 1, QTableWidgetItem(h.get("name", "")))
            self.table.setItem(i, 2, QTableWidgetItem(
                "单文件" if h.get("single_file") else "多文件"
            ))
            self.table.setItem(i, 3, QTableWidgetItem("成功" if h.get("success") else "失败"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{h.get('duration', 0)}s"))

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _clear(self):
        self.config_manager.clear_history()
        self._refresh()
```

### Task 12: 创建 gui/env_interface.py

**Files:**
- Create: `gui/env_interface.py`

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea
from qfluentwidgets import (
    CardWidget, BodyLabel, PushButton, FluentIcon,
    InfoLevel, InfoBadge
)
from utils.env_checker import EnvChecker


class EnvInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checker = EnvChecker()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title_row = QHBoxLayout()
        title_row.addWidget(BodyLabel("环境检测"))
        refresh_btn = PushButton("重新检测")
        refresh_btn.clicked.connect(self._refresh)
        title_row.addWidget(refresh_btn)
        layout.addLayout(title_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.card_container = QWidget()
        self.card_layout = QVBoxLayout(self.card_container)
        scroll.setWidget(self.card_container)
        layout.addWidget(scroll)

        self._refresh()

    def _refresh(self):
        for i in reversed(range(self.card_layout.count())):
            w = self.card_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        results = self.checker.check_all()
        for key, result in results.items():
            card = CardWidget()
            card_layout = card.vBoxLayout

            level = InfoLevel.INFO
            if result["status"] == "success":
                level = InfoLevel.SUCCESS
            elif result["status"] == "warning":
                level = InfoLevel.WARNING
            elif result["status"] == "error":
                level = InfoLevel.ERROR

            row = QHBoxLayout()
            badge = InfoBadge.custom(
                result["name"],
                level,
                parent=card
            )
            row.addWidget(badge)
            value_label = BodyLabel(f"{result['value']} - {result['message']}")
            row.addWidget(value_label)
            row.addStretch()
            card_layout.addLayout(row)

            self.card_layout.addWidget(card)

        self.card_layout.addStretch()
```

### Task 13: 创建 gui/about_interface.py

**Files:**
- Create: `gui/about_interface.py`

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import BodyLabel, TitleLabel, CaptionLabel
from _metadata import APP_NAME, APP_VERSION, APP_AUTHOR, APP_COPYRIGHT


class AboutInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        title = TitleLabel(APP_NAME)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        ver = BodyLabel(f"版本 {APP_VERSION}")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)

        author = CaptionLabel(f"作者: {APP_AUTHOR}")
        author.setAlignment(Qt.AlignCenter)
        layout.addWidget(author)

        copyright_label = CaptionLabel(APP_COPYRIGHT)
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)

        info = BodyLabel(
            "本工具基于 PyInstaller，可将 Python 脚本打包为 Windows 可执行文件。"
        )
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)
```

### Task 14: 创建对话框

**Files:**
- Create: `gui/dialogs/preview_dialog.py`
- Create: `gui/dialogs/pyi_version_dialog.py`

- [ ] **preview_dialog.py**

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    Dialog, PushButton, TextEdit, FluentIcon, MessageBox
)


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
```

- [ ] **pyi_version_dialog.py**

```python
import subprocess
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    Dialog, PushButton, ListWidget, InfoLevel, InfoBadge, BodyLabel
)


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
```

---

## Phase 4: 主窗口与入口

### Task 15: 创建 gui/main_window.py

**Files:**
- Create: `gui/main_window.py`

```python
import os
import sys
import threading
import time
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    MSFluentWindow, NavigationItemPosition, FluentIcon,
    ProgressBar, PushButton, ToolButton, MessageBox,
    StateToolTip, InfoLevel, BodyLabel, setTheme, Theme
)

from gui.pack_interface import PackInterface
from gui.template_interface import TemplateInterface
from gui.history_interface import HistoryInterface
from gui.env_interface import EnvInterface
from gui.about_interface import AboutInterface
from core.packer import Packer
from utils.config_manager import ConfigManager
from utils.env_checker import EnvChecker


class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()

        self.config_manager = ConfigManager()
        self.packer = Packer()

        self._create_sub_interfaces()
        self._setup_packer()
        self._init_window()
        self._check_environment()

    def _create_sub_interfaces(self):
        self.pack_interface = PackInterface(self.packer, self.config_manager)
        self.template_interface = TemplateInterface(self.config_manager)
        self.history_interface = HistoryInterface(self.config_manager)
        self.env_interface = EnvInterface()
        self.about_interface = AboutInterface()

        self.addSubInterface(
            self.pack_interface, FluentIcon.VIEW_LIST,
            "打包", position=NavigationItemPosition.TOP
        )
        self.addSubInterface(
            self.template_interface, FluentIcon.LIBRARY,
            "模板管理", position=NavigationItemPosition.TOP
        )
        self.addSubInterface(
            self.history_interface, FluentIcon.DATE_TIME,
            "历史统计", position=NavigationItemPosition.TOP
        )
        self.addSubInterface(
            self.env_interface, FluentIcon.SETTING,
            "环境管理", position=NavigationItemPosition.TOP
        )
        self.addSubInterface(
            self.about_interface, FluentIcon.INFO,
            "关于", position=NavigationItemPosition.BOTTOM
        )

    def _setup_packer(self):
        self.packer.finished_signal.connect(self._on_pack_finished)

        # 配置区打包按钮
        self.pack_interface.start_pack_signal.connect(self._start_pack)

    def _init_window(self):
        self.setWindowTitle("Python一键打包EXE")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _check_environment(self):
        checker = EnvChecker()
        results = checker.check_all()
        pack_iface = self.pack_interface
        for key, result in results.items():
            msg = f"[{result['status'].upper()}] {result['name']}: {result['value']} - {result['message']}"
            pack_iface.log_widget.add_log(msg)

        summary = checker.get_summary()
        if summary["has_error"]:
            pack_iface.log_widget.add_log(
                f"[ERROR] 检测完成: {summary['success']} 项通过, "
                f"{summary['warning']} 项警告, {summary['error']} 项错误"
            )
        elif summary["has_warning"]:
            pack_iface.log_widget.add_log(
                f"[WARNING] 检测完成: {summary['success']} 项通过, "
                f"{summary['warning']} 项警告"
            )
        else:
            pack_iface.log_widget.add_log(
                f"[SUCCESS] 检测完成: 全部 {summary['success']} 项通过"
            )

    def _start_pack(self, config):
        self._pack_thread = threading.Thread(
            target=self._run_pack, args=(config,), daemon=True
        )
        self._pack_thread.start()

    def _run_pack(self, config):
        try:
            success = self.packer.pack(config)
            self.packer.finished_signal.emit(success, config, 0)
        except Exception as e:
            self.packer.log_signal.emit(f"[ERROR] 打包失败: {str(e)}")
            self.packer.finished_signal.emit(False, config, 0)

    def _on_pack_finished(self, success, config, duration):
        if success:
            self.pack_interface.log_widget.add_log("[SUCCESS] 打包完成！")
            if config.get("auto_open_output", True) and config.get("output_dir"):
                try:
                    os.startfile(config["output_dir"])
                except Exception:
                    pass
        else:
            self.pack_interface.log_widget.add_log("[ERROR] 打包失败！")

        self.config_manager.add_to_history(config, success, int(duration))
```

### Task 16: 重写 main.py

**Files:**
- Modify: `main.py`

```python
import sys
import ctypes


def set_dpi_awareness():
    try:
        if sys.platform == "win32":
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def main():
    set_dpi_awareness()

    from core.single_instance import SingleInstance
    instance = SingleInstance()
    if not instance.acquire():
        sys.exit(1)

    try:
        from app.application import Application
        from gui.main_window import MainWindow

        app = Application()
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    finally:
        instance.release()


if __name__ == "__main__":
    main()
```

---

## Phase 5: 清理与验证

### Task 17: 删除旧的 ttkbootstrap GUI 文件

- [ ] **删除文件**

```bash
git rm gui/main_window.py gui/config_panel.py gui/log_panel.py
git rm gui/template_manager.py gui/stats_dialog.py gui/env_setup_dialog.py
git rm gui/about_dialog.py gui/upx_download_dialog.py gui/pyi_version_dialog.py
git rm gui/style.py create_icon.py test_delete.py 启动程序.bat 启动程序.vbs
```

### Task 18: 安装依赖并验证

- [ ] **安装依赖**

```bash
pip install PySide6 PySide6-Fluent-Widgets Pillow
```

- [ ] **运行验证**

```bash
python main.py
```

预期：QFluentWidgets Fluent 风格窗口启动，左侧有 5 个导航项，环境检测日志正常输出。
