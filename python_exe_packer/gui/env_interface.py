from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import (
    SimpleCardWidget, BodyLabel, PushButton, FluentIcon,
    InfoBadge, ScrollArea
)
from utils.env_checker import EnvChecker
from utils.i18n import tr


class CheckWorker(QObject):
    finished = Signal(dict)

    def run(self):
        checker = EnvChecker()
        results = checker.check_all()
        self.finished.emit(results)


class EnvInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title_row = QHBoxLayout()
        self.title_label = BodyLabel(tr("env_check"))
        title_row.addWidget(self.title_label)
        self.refresh_btn = PushButton(tr("recheck"))
        self.refresh_btn.clicked.connect(self._refresh)
        title_row.addWidget(self.refresh_btn)
        layout.addLayout(title_row)

        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent;")
        self.card_container = QWidget()
        self.card_container.setAutoFillBackground(False)
        self.card_container.setStyleSheet("background-color: transparent;")
        self.card_layout = QVBoxLayout(self.card_container)
        scroll.setWidget(self.card_container)
        layout.addWidget(scroll)

        self._refresh()

    def retranslateUi(self):
        self.title_label.setText(tr("env_check"))
        self.refresh_btn.setText(tr("recheck"))

    def _refresh(self):
        if self._thread and self._thread.isRunning():
            return

        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText(tr("checking"))

        self._thread = QThread(self)
        self._worker = CheckWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_results)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def _on_results(self, results):
        # 清空现有卡片和stretch
        for i in reversed(range(self.card_layout.count())):
            item = self.card_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()
            elif item and item.spacerItem():
                self.card_layout.removeItem(item)

        for key, result in results.items():
            card = SimpleCardWidget()
            card_layout = QVBoxLayout(card)

            status = result["status"]
            if status == "success":
                badge = InfoBadge.success(result["name"], parent=card)
            elif status == "warning":
                badge = InfoBadge.warning(result["name"], parent=card)
            elif status == "error":
                badge = InfoBadge.error(result["name"], parent=card)
            else:
                badge = InfoBadge.info(result["name"], parent=card)

            row = QHBoxLayout()
            row.addWidget(badge)
            value_label = BodyLabel(f"{result['value']} - {result['message']}")
            row.addWidget(value_label)
            row.addStretch()
            card_layout.addLayout(row)

            self.card_layout.addWidget(card)

        self.card_layout.addStretch()

        # 强制刷新布局
        self.card_container.adjustSize()
        self.update()

        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText(tr("recheck"))

    def _on_thread_finished(self):
        self._thread = None
