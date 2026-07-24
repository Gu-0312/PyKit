from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QHeaderView,
    QAbstractItemView
)
from qfluentwidgets import (
    SimpleCardWidget, BodyLabel, PushButton, FluentIcon, MessageBox,
    TableView, qconfig, Theme
)
from utils.i18n import tr


class HistoryInterface(QWidget):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setAutoFillBackground(False)
        self.setStyleSheet("background-color: transparent;")
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        stats_card = SimpleCardWidget()
        stats_layout = QVBoxLayout(stats_card)
        self.stats_label = BodyLabel(tr("stats_loading"))
        stats_layout.addWidget(self.stats_label)
        layout.addWidget(stats_card)

        # 使用qfluentwidgets的TableView，自动跟随主题
        self.table = TableView(self)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.refresh_btn = PushButton(tr("refresh"))
        self.refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(self.refresh_btn)
        self.clear_btn = PushButton(tr("clear_history"))
        self.clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(self.clear_btn)
        layout.addLayout(btn_row)

    def retranslateUi(self):
        self.refresh_btn.setText(tr("refresh"))
        self.clear_btn.setText(tr("clear_history"))
        self._refresh()

    def _refresh(self):
        stats = self.config_manager.get_stats()
        self.stats_label.setText(
            f"{tr('total_count')}: {stats['total_count']}  |  "
            f"{tr('success')}: {stats['success_count']}  |  "
            f"{tr('fail')}: {stats['fail_count']}  |  "
            f"{tr('success_rate')}: {stats['success_rate']}%  |  "
            f"{tr('avg_duration')}: {stats['avg_duration_str']}  |  "
            f"{tr('latest_time')}: {stats['latest_time']}"
        )

        history = self.config_manager.load_history(max_count=50)
        # 创建QStandardItemModel
        model = QStandardItemModel(len(history), 5)
        model.setHorizontalHeaderLabels([
            tr("col_time"), tr("col_source"), tr("col_mode"), tr("col_result"), tr("col_duration")
        ])

        for i, h in enumerate(history):
            model.setItem(i, 0, QStandardItem(h.get("timestamp", "")))
            model.setItem(i, 1, QStandardItem(h.get("name", "")))
            model.setItem(i, 2, QStandardItem(
                tr("single_mode") if h.get("single_file") else tr("multi_mode")
            ))
            model.setItem(i, 3, QStandardItem(tr("success") if h.get("success") else tr("fail")))
            model.setItem(i, 4, QStandardItem(f"{h.get('duration', 0)}s"))

        self.table.setModel(model)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def _clear(self):
        self.config_manager.clear_history()
        self._refresh()
