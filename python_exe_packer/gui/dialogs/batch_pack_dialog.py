import os
import threading
import time
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QFileDialog
from qfluentwidgets import Dialog, PushButton, ListWidget, CheckBox, ProgressBar, BodyLabel
from gui.log_widget import LogWidget


class BatchPackDialog(Dialog):
    def __init__(self, packer, config_manager, parent=None):
        super().__init__("", "", parent)
        self.packer = packer
        self.config_manager = config_manager
        self._stop_event = threading.Event()
        self._is_running = False

        layout = self.vBoxLayout

        self.file_list = ListWidget()
        layout.addWidget(self.file_list)

        btn_row = QHBoxLayout()
        self.add_btn = PushButton()
        self.add_btn.clicked.connect(self._add_files)
        btn_row.addWidget(self.add_btn)
        self.remove_btn = PushButton()
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(self.remove_btn)
        layout.addLayout(btn_row)

        opts_row = QHBoxLayout()
        self.single_cb = CheckBox()
        self.single_cb.setChecked(True)
        opts_row.addWidget(self.single_cb)
        self.windowed_cb = CheckBox()
        self.windowed_cb.setChecked(True)
        opts_row.addWidget(self.windowed_cb)
        layout.addLayout(opts_row)

        self.overall_progress = ProgressBar()
        layout.addWidget(self.overall_progress)
        self.file_progress = ProgressBar()
        layout.addWidget(self.file_progress)

        self.status_label = BodyLabel()
        layout.addWidget(self.status_label)

        self.log_widget = LogWidget()
        layout.addWidget(self.log_widget)

        action_row = QHBoxLayout()
        self.start_btn = PushButton()
        self.start_btn.clicked.connect(self._start_batch)
        action_row.addWidget(self.start_btn)
        self.stop_btn = PushButton()
        self.stop_btn.clicked.connect(self._stop_batch)
        self.stop_btn.setEnabled(False)
        action_row.addWidget(self.stop_btn)
        layout.addLayout(action_row)

        close_btn = PushButton()
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def retranslateUi(self):
        from utils.i18n import tr
        self.setTitle(tr("batch_title"))
        self.add_btn.setText(tr("add_file"))
        self.remove_btn.setText(tr("remove_selected"))
        self.single_cb.setText(tr("single_mode"))
        self.windowed_cb.setText(tr("hide_console"))
        self.start_btn.setText(tr("batch_start"))
        self.stop_btn.setText(tr("stop"))
        close_btn = self.vBoxLayout.itemAt(self.vBoxLayout.count() - 1).widget()
        close_btn.setText(tr("close"))
        self.log_widget.retranslateUi()

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "", "", "Python (*.py *.pyw);;All Files (*)")
        for f in files:
            if self.file_list.findText(f) < 0:
                self.file_list.addItem(f)

    def _remove_selected(self):
        row = self.file_list.currentRow()
        if row >= 0:
            self.file_list.takeItem(row)

    def _start_batch(self):
        if self._is_running:
            return
        if self.file_list.count() == 0:
            return

        self._is_running = True
        self._stop_event.clear()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_widget.clear_log()
        self.overall_progress.setValue(0)
        self.file_progress.setValue(0)

        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]
        single = self.single_cb.isChecked()
        windowed = self.windowed_cb.isChecked()

        thread = threading.Thread(target=self._run_batch, args=(files, single, windowed), daemon=True)
        thread.start()

    def _stop_batch(self):
        self._stop_event.set()
        self.log_widget.add_log("[WARN] Batch cancelled by user")

    def _run_batch(self, files, single, windowed):
        total = len(files)
        success_count = 0

        for i, src in enumerate(files):
            if self._stop_event.is_set():
                break

            self.log_widget.add_log(f"[INFO] [{i+1}/{total}] {os.path.basename(src)}")
            self.overall_progress.setValue(int((i / total) * 100))
            self.status_label.setText(f"[{i+1}/{total}] {os.path.basename(src)}")
            self.file_progress.setValue(0)

            from utils.i18n import tr
            name = os.path.splitext(os.path.basename(src))[0]
            config = {
                "source_file": src,
                "output_dir": os.path.dirname(src),
                "name": name,
                "single_file": single,
                "windowed": windowed,
                "icon": "",
                "auto_clean": True,
                "auto_detect_deps": True,
                "auto_open_output": False,
                "enable_upx": False,
                "create_installer": False,
                "app_version": "1.0.0",
                "custom_args": "",
                "hidden_imports": [],
                "excludes": [],
                "data_files": [],
                "python_interpreter": "",
                "auto_exclude": True,
            }

            start = time.time()
            try:
                ok = self.packer.pack(config, stop_event=self._stop_event)
                duration = int(time.time() - start)
                self.config_manager.add_to_history(config, ok, duration)
                if ok:
                    success_count += 1
                    self.log_widget.add_log(f"[SUCCESS] [{i+1}/{total}] {name}")
                else:
                    self.log_widget.add_log(f"[ERROR] [{i+1}/{total}] {name}")
            except Exception as e:
                self.log_widget.add_log(f"[ERROR] [{i+1}/{total}] {name}: {e}")

            self.file_progress.setValue(100)

        self.overall_progress.setValue(100)
        self.status_label.setText(f"{success_count}/{total} {('succeeded' if success_count == total else 'failed') if not self._stop_event.is_set() else 'cancelled'}")
        self._is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
