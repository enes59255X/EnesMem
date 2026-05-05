"""
process_selector.py — Modal dialog for selecting a target process.
Features: live search, sortable table, auto-refresh.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLabel, QAbstractItemView,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

from core.process_manager import ProcessManager, ProcessInfo
from utils.i18n import tr


class ProcessSelectorDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("proc_title"))
        self.setMinimumSize(640, 480)
        self.setModal(True)

        self._selected: ProcessInfo | None = None
        self._all_procs: list[ProcessInfo] = []

        self._build_ui()
        self.retranslate_ui()
        self._refresh()

        # Auto-refresh every 3 seconds
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(3000)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Search bar
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.textChanged.connect(self._filter)
        self._search.setFixedHeight(36)
        search_row.addWidget(self._search)

        self._refresh_btn = QPushButton()
        self._refresh_btn.setFixedHeight(36)
        self._refresh_btn.setFixedWidth(90)
        self._refresh_btn.clicked.connect(self._refresh)
        search_row.addWidget(self._refresh_btn)
        root.addLayout(search_row)

        # Table
        self._table = QTableWidget(0, 3)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSortingEnabled(True)
        self._table.doubleClicked.connect(self._accept)
        root.addWidget(self._table)

        # Status + buttons
        bottom = QHBoxLayout()
        self._status_lbl = QLabel("")
        bottom.addWidget(self._status_lbl)
        bottom.addStretch()

        self._cancel_btn = QPushButton()
        self._cancel_btn.setFixedWidth(90)
        self._cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(self._cancel_btn)

        self._ok_btn = QPushButton()
        self._ok_btn.setFixedWidth(90)
        self._ok_btn.setObjectName("primary_btn")
        self._ok_btn.clicked.connect(self._accept)
        bottom.addWidget(self._ok_btn)
        root.addLayout(bottom)

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("proc_title"))
        self._search.setPlaceholderText("🔍  " + tr("proc_filter_placeholder"))
        self._refresh_btn.setText("⟳ " + tr("btn_refresh"))
        self._table.setHorizontalHeaderLabels([
            tr("proc_col_name"),
            tr("proc_col_pid"),
            tr("proc_col_threads")
        ])
        self._cancel_btn.setText(tr("btn_cancel"))
        self._ok_btn.setText(tr("btn_attach"))
        self._update_status_lbl()

    def _refresh(self) -> None:
        self._all_procs = ProcessManager.list_processes()
        self._filter(self._search.text())
        self._update_status_lbl()

    def _update_status_lbl(self) -> None:
        self._status_lbl.setText(tr("proc_count").format(len(self._all_procs)))

    def _filter(self, text: str) -> None:
        text = text.strip().lower()
        filtered = [
            p for p in self._all_procs
            if text in p.name.lower() or text in str(p.pid)
        ] if text else self._all_procs

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(filtered))
        for row, proc in enumerate(filtered):
            name_item = QTableWidgetItem(proc.name)
            pid_item  = QTableWidgetItem(str(proc.pid))
            thr_item  = QTableWidgetItem(str(proc.threads))
            pid_item.setData(Qt.ItemDataRole.UserRole, proc.pid)
            for item in (name_item, pid_item, thr_item):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, pid_item)
            self._table.setItem(row, 2, thr_item)
        self._table.setSortingEnabled(True)

    def _accept(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        pid_item = self._table.item(row, 1)
        name_item = self._table.item(row, 0)
        if pid_item and name_item:
            pid = int(pid_item.text())
            for p in self._all_procs:
                if p.pid == pid:
                    self._selected = p
                    break
        self.accept()

    @property
    def selected_process(self) -> ProcessInfo | None:
        return self._selected

