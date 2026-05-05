"""
results_table.py — Two-pane results display.
Top: Found addresses (scanner output, read-only, large) with Search Filter.
Bottom: Watchlist (user-added addresses with freeze toggle) with bulk ops.
"""
import json
import csv
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMenu, QLabel, QInputDialog,
    QCheckBox, QHBoxLayout, QPushButton, QLineEdit, QFileDialog, QMessageBox,
    QComboBox, QShortcut
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt5.QtGui import QColor, QFont, QKeySequence

from utils.converters import format_address, format_value
from utils.patterns import DataType
from utils.i18n import tr


MAX_DISPLAY_RESULTS = 2000


class WatchEntry:
    __slots__ = ("address", "description", "dtype", "frozen", "current_value", "module_name", "offsets")

    def __init__(self, address: int, dtype: DataType, description: str = "", module_name: str = None, offsets: list[int] = None) -> None:
        self.address       = address
        self.description   = description or format_address(address)
        self.dtype         = dtype
        self.frozen        = False
        self.current_value = None
        self.module_name   = module_name
        self.offsets       = offsets



class ResultsTable(QWidget):
    """
    Signals:
        sig_add_to_watchlist(address, dtype)
        sig_write_value(address, dtype, new_value_str)
        sig_freeze_toggled(address, dtype, freeze: bool)
    """
    sig_add_to_watchlist = pyqtSignal(object, object)
    sig_write_value      = pyqtSignal(object, object, str)
    sig_freeze_toggled   = pyqtSignal(object, object, bool)
    sig_browse_memory    = pyqtSignal(object)
    sig_request_page     = pyqtSignal(int, int) # start, count (these stay int as they are small indices)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._dtype      = DataType.INT32
        self._scan_results: list = []
        self._filtered_results: list = []
        self._total_count: int = 0
        self._page_size: int = MAX_DISPLAY_RESULTS
        self._current_page: int = 0
        self._watchlist:    list[WatchEntry] = []
        self._blink_timers: dict[int, int] = {}  # row -> ticks left
        
        self._build_ui()
        self._setup_shortcuts()

        # Timer for color blinking (10 ticks = 1 second if called every 100ms)
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._tick_blinks)
        self._fade_timer.start(100)

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # ── Top: Found Addresses ──
        top_container = QWidget()
        top_lay = QVBoxLayout(top_container)
        top_lay.setContentsMargins(4, 4, 4, 4)
        top_lay.setSpacing(4)

        top_header = QHBoxLayout()
        self._top_lbl = QLabel(tr("lbl_found_addresses"))
        self._top_lbl.setObjectName("section_label")
        top_header.addWidget(self._top_lbl)
        
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText(tr("placeholder_filter"))
        self._search_input.setFixedWidth(200)
        self._search_input.textChanged.connect(self._apply_filter)
        top_header.addWidget(self._search_input)
        
        top_header.addStretch()
        self._found_count_lbl = QLabel("")
        self._found_count_lbl.setObjectName("dim_label")
        top_header.addWidget(self._found_count_lbl)
        
        # Pagination buttons
        top_header.addSpacing(10)
        self._prev_page_btn = QPushButton("◀")
        self._prev_page_btn.setFixedWidth(30)
        self._prev_page_btn.setObjectName("small_btn")
        self._prev_page_btn.clicked.connect(self._on_prev_page)
        self._prev_page_btn.setEnabled(False)
        top_header.addWidget(self._prev_page_btn)
        
        self._page_lbl = QLabel("1")
        self._page_lbl.setObjectName("dim_label")
        top_header.addWidget(self._page_lbl)
        
        self._next_page_btn = QPushButton("▶")
        self._next_page_btn.setFixedWidth(30)
        self._next_page_btn.setObjectName("small_btn")
        self._next_page_btn.clicked.connect(self._on_next_page)
        self._next_page_btn.setEnabled(False)
        top_header.addWidget(self._next_page_btn)
        
        top_lay.addLayout(top_header)

        self._found_table = QTableWidget(0, 4)
        self._found_table_headers = [tr("col_address"), tr("col_value"), tr("col_prev"), tr("col_type")]
        self._found_table.setHorizontalHeaderLabels(self._found_table_headers)
        self._found_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._found_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._found_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._found_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._found_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._found_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._found_table.setAlternatingRowColors(True)
        self._found_table.verticalHeader().setVisible(False)
        self._found_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._found_table.customContextMenuRequested.connect(self._found_context_menu)
        self._found_table.doubleClicked.connect(self._on_found_double_click)
        top_lay.addWidget(self._found_table)

        splitter.addWidget(top_container)

        # ── Bottom: Watchlist ──
        bot_container = QWidget()
        bot_lay = QVBoxLayout(bot_container)
        bot_lay.setContentsMargins(4, 4, 4, 4)
        bot_lay.setSpacing(4)

        bot_header = QHBoxLayout()
        self._bot_lbl = QLabel(tr("lbl_watchlist"))
        self._bot_lbl.setObjectName("section_label")
        bot_header.addWidget(self._bot_lbl)
        
        self._watch_search_input = QLineEdit()
        self._watch_search_input.setPlaceholderText(tr("placeholder_filter"))
        self._watch_search_input.setFixedWidth(150)
        self._watch_search_input.textChanged.connect(self._apply_watch_filter)
        bot_header.addWidget(self._watch_search_input)
        
        self._show_frozen_only_chk = QCheckBox(tr("chk_frozen_only"))
        self._show_frozen_only_chk.setObjectName("dim_label")
        self._show_frozen_only_chk.stateChanged.connect(lambda: self._apply_watch_filter(self._watch_search_input.text()))
        bot_header.addWidget(self._show_frozen_only_chk)
        
        self._freeze_all_btn = QPushButton("❄ " + tr("btn_freeze_all"))
        self._freeze_all_btn.setFixedHeight(24)
        self._freeze_all_btn.setObjectName("small_btn")
        self._freeze_all_btn.clicked.connect(lambda: self.set_bulk_freeze(True))
        
        self._unfreeze_all_btn = QPushButton("🔥 " + tr("btn_unfreeze_all"))
        self._unfreeze_all_btn.setFixedHeight(24)
        self._unfreeze_all_btn.setObjectName("small_btn")
        self._unfreeze_all_btn.clicked.connect(lambda: self.set_bulk_freeze(False))

        self._export_btn = QPushButton("📤 " + tr("btn_export"))
        self._export_btn.setFixedHeight(24)
        self._export_btn.setObjectName("small_btn")
        self._export_btn.clicked.connect(self.export_watchlist)

        self._import_btn = QPushButton("📥 " + tr("btn_import"))
        self._import_btn.setFixedHeight(24)
        self._import_btn.setObjectName("small_btn")
        self._import_btn.clicked.connect(self.import_watchlist)

        self._clr_btn = QPushButton("🗑 " + tr("btn_clear"))
        self._clr_btn.setFixedHeight(24)
        self._clr_btn.setObjectName("small_btn")
        self._clr_btn.clicked.connect(self.clear_watchlist)
        
        bot_header.addWidget(self._freeze_all_btn)
        bot_header.addWidget(self._unfreeze_all_btn)
        bot_header.addStretch()
        bot_header.addWidget(self._export_btn)
        bot_header.addWidget(self._import_btn)
        bot_header.addWidget(self._clr_btn)
        bot_lay.addLayout(bot_header)

        self._watch_table = QTableWidget(0, 5)
        self._watch_table_headers = [tr("col_description"), tr("col_address"), tr("col_type"), tr("col_value"), tr("col_freeze")]
        self._watch_table.setHorizontalHeaderLabels(self._watch_table_headers)
        self._watch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._watch_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._watch_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._watch_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._watch_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._watch_table.setColumnWidth(4, 64)
        self._watch_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self._watch_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._watch_table.setAlternatingRowColors(True)
        self._watch_table.verticalHeader().setVisible(False)
        self._watch_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._watch_table.customContextMenuRequested.connect(self._watch_context_menu)
        self._watch_table.cellChanged.connect(self._on_watch_cell_changed)
        bot_lay.addWidget(self._watch_table)

        splitter.addWidget(bot_container)
        splitter.setSizes([400, 200])
        root.addWidget(splitter)

    def _setup_shortcuts(self) -> None:
        del_shortcut = QShortcut(QKeySequence("Delete"), self._watch_table)
        del_shortcut.activated.connect(self._delete_selected_watch)
        
        freeze_shortcut = QShortcut(QKeySequence("Ctrl+D"), self._watch_table)
        freeze_shortcut.activated.connect(self._toggle_freeze_selected_watch)
        
        copy_found = QShortcut(QKeySequence("Ctrl+C"), self._found_table)
        copy_found.activated.connect(self._copy_selected_found)
        
        copy_watch = QShortcut(QKeySequence("Ctrl+C"), self._watch_table)
        copy_watch.activated.connect(self._copy_selected_watch)
        
    def retranslate_ui(self) -> None:
        """Update all strings in the UI after a language change."""
        self._top_lbl.setText(tr("lbl_found_addresses"))
        self._search_input.setPlaceholderText(tr("placeholder_filter"))
        
        self._found_table_headers = [tr("col_address"), tr("col_value"), tr("col_prev"), tr("col_type")]
        self._found_table.setHorizontalHeaderLabels(self._found_table_headers)
        
        self._bot_lbl.setText(tr("lbl_watchlist"))
        self._watch_search_input.setPlaceholderText(tr("placeholder_filter"))
        self._show_frozen_only_chk.setText(tr("chk_frozen_only"))
        
        self._freeze_all_btn.setText("❄ " + tr("btn_freeze_all"))
        self._unfreeze_all_btn.setText("🔥 " + tr("btn_unfreeze_all"))
        self._export_btn.setText("📤 " + tr("btn_export"))
        self._import_btn.setText("📥 " + tr("btn_import"))
        self._clr_btn.setText("🗑 " + tr("btn_clear"))
        
        self._watch_table_headers = [tr("col_description"), tr("col_address"), tr("col_type"), tr("col_value"), tr("col_freeze")]
        self._watch_table.setHorizontalHeaderLabels(self._watch_table_headers)
        
        self._render_found()

    # ── Public API ────────────────────────────────────────────────────────────

    def reset_pagination(self) -> None:
        self._current_page = 0

    def set_dtype(self, dtype: DataType) -> None:
        """Update the data type and refresh displays."""
        self._dtype = dtype
        self._render_found()

    def populate_found(self, results: list, dtype: DataType, total_count: int = None) -> None:
        """Update found results with pagination support."""
        self._dtype        = dtype
        self._scan_results = results
        if total_count is not None:
            self._total_count = total_count
        
        self._apply_filter(self._search_input.text())

    def _apply_filter(self, text: str) -> None:
        text = text.lower().strip()
        if not text:
            self._filtered_results = self._scan_results
        else:
            self._filtered_results = []
            for r in self._scan_results:
                addr_str = format_address(r.address).lower()
                val_str  = format_value(r.current_value(self._dtype), self._dtype).lower()
                if text in addr_str or text in val_str:
                    self._filtered_results.append(r)
        
        self._render_found()

    def _render_found(self) -> None:
        display = self._filtered_results # These are already sliced if coming from a page request
        # But if they are NOT sliced (e.g. initial small scan), we should ensure we don't over-render
        if not self._search_input.text() and len(display) > self._page_size:
             display = display[:self._page_size]

        self._found_table.setRowCount(0)
        self._found_table.setRowCount(len(display))
        self._found_table.setSortingEnabled(False)

        for row, res in enumerate(display):
            addr_str = format_address(res.address)
            cur_str  = format_value(res.current_value(self._dtype), self._dtype)
            prev_str = format_value(res.previous_value(self._dtype), self._dtype)

            self._found_table.setItem(row, 0, _mk_item(addr_str, mono=True))
            self._found_table.setItem(row, 1, _mk_item(cur_str))
            self._found_table.setItem(row, 2, _mk_item(prev_str, dim=True))
            self._found_table.setItem(row, 3, _mk_item(self._dtype.name))
            self._found_table.setRowHeight(row, 22)

        total = self._total_count
        shown = len(display)
        
        # Update pagination state
        max_page = (total + self._page_size - 1) // self._page_size if total > 0 else 0
        self._page_lbl.setText(f"{self._current_page + 1} / {max(1, max_page)}")
        self._prev_page_btn.setEnabled(self._current_page > 0)
        self._next_page_btn.setEnabled(self._current_page + 1 < max_page)

        suffix = tr("msg_showing_count").format(f"{shown:,}") if total > shown else ""
        self._found_count_lbl.setText(tr("msg_found_count").format(f"{total:,}") + suffix)
        self._found_table.setSortingEnabled(True)

    def _on_next_page(self) -> None:
        self._current_page += 1
        self.sig_request_page.emit(self._current_page * self._page_size, self._page_size)

    def _on_prev_page(self) -> None:
        if self._current_page > 0:
            self._current_page -= 1
            self.sig_request_page.emit(self._current_page * self._page_size, self._page_size)

    def refresh_found(self, results: list) -> None:
        """Live-refresh values in the found table without rebuilding rows."""
        # Using self._filtered_results for correct indexing
        display = self._filtered_results[:MAX_DISPLAY_RESULTS]
        for row, res in enumerate(display):
            if row >= self._found_table.rowCount():
                break
            cur_str  = format_value(res.current_value(self._dtype), self._dtype)
            prev_str = format_value(res.previous_value(self._dtype), self._dtype)
            self._found_table.item(row, 1).setText(cur_str)
            self._found_table.item(row, 2).setText(prev_str)

    def add_to_watchlist(self, address: int, dtype: DataType, description: str = "") -> None:
        for e in self._watchlist:
            if e.address == address and not e.module_name:
                return
        entry = WatchEntry(address, dtype, description)
        self._watchlist.append(entry)
        self._rebuild_watch_row(len(self._watchlist) - 1)

    def add_pointer_to_watchlist(self, module_name: str, offsets: list[int], address: int, dtype: DataType, description: str = "") -> None:
        # Validate parameters
        if not module_name or not isinstance(offsets, list):
            return
        if address is None or address < 0x1000:
            return
        
        # Check for duplicates
        for e in self._watchlist:
            if e.module_name == module_name and e.offsets == offsets:
                return
        
        try:
            if not description:
                if not offsets:
                    description = f'"{module_name}"'
                else:
                    desc = f'"{module_name}"+{offsets[0]:X}'
                    for o in offsets[1:]:
                        desc = f'[{desc}]+{o:X}'
                    description = desc
            entry = WatchEntry(address, dtype, description, module_name, offsets)
            self._watchlist.append(entry)
            self._rebuild_watch_row(len(self._watchlist) - 1)
        except Exception:
            # Don't crash on watchlist add failure
            pass

    def _apply_watch_filter(self, text: str = None) -> None:
        if text is None:
            text = self._watch_search_input.text()
        text = text.lower().strip()
        show_frozen_only = self._show_frozen_only_chk.isChecked()
        
        for row in range(self._watch_table.rowCount()):
            entry = self._watchlist[row]
            
            if show_frozen_only and not entry.frozen:
                self._watch_table.setRowHidden(row, True)
                continue
                
            if not text:
                self._watch_table.setRowHidden(row, False)
                continue
                
            addr_str = format_address(entry.address).lower()
            val_str = ""
            if entry.current_value is not None:
                val_str = format_value(entry.current_value, entry.dtype).lower()
            desc_str = entry.description.lower()
            
            if text in addr_str or text in val_str or text in desc_str:
                self._watch_table.setRowHidden(row, False)
            else:
                self._watch_table.setRowHidden(row, True)


    def refresh_watchlist(self, results_map: dict) -> None:
        """Update value column in watchlist. Blinks red/green if changed."""
        for row, entry in enumerate(self._watchlist):
            # Update address column in case it was resolved to a new address
            addr_item = self._watch_table.item(row, 1)
            if addr_item:
                addr_text = format_address(entry.address)
                if entry.module_name:
                    addr_text = "⮡ " + addr_text
                addr_item.setText(addr_text)

            val = results_map.get(entry.address)
            if val is not None:
                old_val = entry.current_value
                entry.current_value = val
                
                val_item = self._watch_table.item(row, 3)
                if val_item:
                    val_item.setText(format_value(val, entry.dtype))
                    
                    if old_val is not None and old_val != val:
                        try:
                            # Try numeric comparison
                            if val > old_val:
                                val_item.setForeground(QColor("#4ade80")) # Green
                            else:
                                val_item.setForeground(QColor("#f87171")) # Red
                            self._blink_timers[row] = 10 # 10 ticks = 1 second
                        except TypeError:
                            val_item.setForeground(QColor("#60a5fa")) # Blue for non-numeric change
                            self._blink_timers[row] = 10
                
        self._tick_blinks()

    def _tick_blinks(self) -> None:
        expired = []
        for row, ticks in self._blink_timers.items():
            ticks -= 1
            if ticks <= 0:
                expired.append(row)
                item = self._watch_table.item(row, 3)
                if item:
                    item.setForeground(QColor("#c9d1d9")) # Default color
            else:
                self._blink_timers[row] = ticks
                
        for row in expired:
            del self._blink_timers[row]

    def set_bulk_freeze(self, freeze: bool) -> None:
        for row, entry in enumerate(self._watchlist):
            if self._watch_table.isRowHidden(row):
                continue  # Only apply bulk freeze to visible/filtered items
            entry.frozen = freeze
            chk = self._watch_table.cellWidget(row, 4).layout().itemAt(0).widget()
            chk.blockSignals(True)
            chk.setChecked(freeze)
            chk.blockSignals(False)
            self.sig_freeze_toggled.emit(entry.address, entry.dtype, freeze)
            
        self._apply_watch_filter(self._watch_search_input.text())

    def clear_watchlist(self) -> None:
        for e in self._watchlist:
            if e.frozen:
                self.sig_freeze_toggled.emit(e.address, e.dtype, False)
        self._watchlist.clear()
        self._watch_table.setRowCount(0)
        self._blink_timers.clear()

    def clear_found(self) -> None:
        self._scan_results.clear()
        self._filtered_results.clear()
        self._found_table.setRowCount(0)
        self._found_count_lbl.setText("")

    # ── Export / Import ───────────────────────────────────────────────────────

    def export_watchlist(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, tr("btn_export"), "", "JSON Files (*.json);;CSV Files (*.csv)")
        if not path:
            return
            
        data = []
        for e in self._watchlist:
            row_dict = {
                "description": e.description,
                "address": format_address(e.address),
                "dtype": e.dtype.name,
                "frozen": e.frozen
            }
            if e.module_name:
                row_dict["module_name"] = e.module_name
                row_dict["offsets"] = e.offsets
            data.append(row_dict)
            
        try:
            if path.endswith(".csv"):
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["description", "address", "dtype", "frozen", "module_name", "offsets"])
                    writer.writeheader()
                    writer.writerows(data)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            QMessageBox.information(self, tr("btn_export"), tr("msg_export_success"))
        except Exception as ex:
            QMessageBox.critical(self, tr("menu_help"), tr("msg_export_failed").format(str(ex)))

    def import_watchlist(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("btn_import"), "", "JSON Files (*.json)")
        if not path:
            return
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            for row in data:
                addr = int(row["address"], 16)
                dtype = DataType[row["dtype"]]
                desc = row.get("description", "")
                
                mod_name = row.get("module_name")
                if mod_name:
                    # JSON parses lists directly, CSV parses as string, but we only load JSON for imports right now based on format filter
                    offsets = row.get("offsets", [])
                    self.add_pointer_to_watchlist(mod_name, offsets, addr, dtype, desc)
                else:
                    self.add_to_watchlist(addr, dtype, desc)
                # Freeze state is handled manually to sync with Freezer
        except Exception as ex:
            QMessageBox.critical(self, tr("menu_help"), tr("msg_import_failed").format(str(ex)))

    # ── Context menus / Shortcuts ─────────────────────────────────────────────

    def _found_context_menu(self, pos: QPoint) -> None:
        row = self._found_table.rowAt(pos.y())
        if row < 0 or row >= len(self._filtered_results):
            return
        res  = self._filtered_results[row]
        menu = QMenu(self)

        act_add   = menu.addAction("➕ " + tr("menu_add_watchlist"))
        act_write = menu.addAction("✏️ " + tr("menu_edit_value"))
        act_browse = menu.addAction("🔍 " + tr("menu_browse_memory"))
        menu.addSeparator()
        act_copy  = menu.addAction("📋 " + tr("menu_copy_address"))

        chosen = menu.exec(self._found_table.viewport().mapToGlobal(pos))
        if chosen == act_add:
            self.add_to_watchlist(res.address, self._dtype)
            self.sig_add_to_watchlist.emit(res.address, self._dtype)
        elif chosen == act_write:
            self._prompt_write(res.address, self._dtype)
        elif chosen == act_browse:
            self.sig_browse_memory.emit(res.address)
        elif chosen == act_copy:
            self._copy_selected_found()

    def _watch_context_menu(self, pos: QPoint) -> None:
        row = self._watch_table.rowAt(pos.y())
        if row < 0 or row >= len(self._watchlist):
            return
        entry = self._watchlist[row]
        menu  = QMenu(self)

        act_write  = menu.addAction("✏️ " + tr("menu_edit_value"))
        act_browse = menu.addAction("🔍 " + tr("menu_browse_memory"))
        act_copy   = menu.addAction("📋 " + tr("menu_copy_address"))
        menu.addSeparator()
        act_remove = menu.addAction("🗑 " + tr("menu_remove"))

        chosen = menu.exec(self._watch_table.viewport().mapToGlobal(pos))
        if chosen == act_write:
            self._prompt_write(entry.address, entry.dtype)
        elif chosen == act_browse:
            self.sig_browse_memory.emit(entry.address)
        elif chosen == act_copy:
            self._copy_selected_watch()
        elif chosen == act_remove:
            self._delete_selected_watch()

    def _delete_selected_watch(self) -> None:
        rows = sorted([item.row() for item in self._watch_table.selectedItems()])
        if not rows:
            return
        # Unique rows
        unique_rows = sorted(list(set(rows)), reverse=True)
        for r in unique_rows:
            entry = self._watchlist[r]
            if entry.frozen:
                self.sig_freeze_toggled.emit(entry.address, entry.dtype, False)
            self._watchlist.pop(r)
            self._watch_table.removeRow(r)
            
    def _toggle_freeze_selected_watch(self) -> None:
        rows = sorted(list(set(item.row() for item in self._watch_table.selectedItems())))
        for row in rows:
            entry = self._watchlist[row]
            new_state = not entry.frozen
            entry.frozen = new_state
            chk = self._watch_table.cellWidget(row, 4).layout().itemAt(0).widget()
            chk.blockSignals(True)
            chk.setChecked(new_state)
            chk.blockSignals(False)
            self.sig_freeze_toggled.emit(entry.address, entry.dtype, new_state)

    def _copy_selected_found(self) -> None:
        rows = list(set([item.row() for item in self._found_table.selectedItems()]))
        if rows:
            res = self._filtered_results[rows[0]]
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(format_address(res.address))

    def _copy_selected_watch(self) -> None:
        rows = list(set([item.row() for item in self._watch_table.selectedItems()]))
        if rows:
            entry = self._watchlist[rows[0]]
            from PyQt5.QtWidgets import QApplication
            QApplication.clipboard().setText(format_address(entry.address))

    # ── Interactions ──────────────────────────────────────────────────────────

    def _on_found_double_click(self, idx) -> None:
        row = idx.row()
        if row < len(self._filtered_results):
            res = self._filtered_results[row]
            self.add_to_watchlist(res.address, self._dtype)
            self.sig_add_to_watchlist.emit(res.address, self._dtype)

    def _prompt_write(self, address: int, dtype: DataType) -> None:
        val, ok = QInputDialog.getText(
            self, "Edit Value",
            f"New value for {format_address(address)}:",
        )
        if ok and val.strip():
            self.sig_write_value.emit(address, dtype, val.strip())

    def _on_freeze_toggled(self, row: int, checked: bool) -> None:
        if row >= len(self._watchlist):
            return
        entry = self._watchlist[row]
        entry.frozen = checked
        self.sig_freeze_toggled.emit(entry.address, entry.dtype, checked)
        if self._show_frozen_only_chk.isChecked():
            self._apply_watch_filter(self._watch_search_input.text())

    def _on_watch_cell_changed(self, row: int, col: int) -> None:
        if col == 0 and row < len(self._watchlist):
            item = self._watch_table.item(row, 0)
            if item:
                self._watchlist[row].description = item.text()

    def _on_watch_type_changed(self, row: int, text: str) -> None:
        if row >= len(self._watchlist):
            return
        entry = self._watchlist[row]
        
        # Unfreeze first if frozen
        if entry.frozen:
            self.sig_freeze_toggled.emit(entry.address, entry.dtype, False)
            entry.frozen = False
            chk = self._watch_table.cellWidget(row, 4).layout().itemAt(0).widget()
            if chk:
                chk.blockSignals(True)
                chk.setChecked(False)
                chk.blockSignals(False)
                
        try:
            entry.dtype = DataType[text]
            entry.current_value = None # force refresh
            val_item = self._watch_table.item(row, 3)
            if val_item:
                val_item.setText("???")
        except KeyError:
            pass

    # ── Private helpers ───────────────────────────────────────────────────────

    def _rebuild_watch_row(self, row: int) -> None:
        entry = self._watchlist[row]
        self._watch_table.setRowCount(max(self._watch_table.rowCount(), row + 1))
        self._watch_table.blockSignals(True)

        desc_item = QTableWidgetItem(entry.description)
        
        addr_text = format_address(entry.address)
        if entry.module_name:
            addr_text = "⮡ " + addr_text
            
        addr_item = _mk_item(addr_text, mono=True)
        
        type_combo = QComboBox()
        for dt in DataType:
            type_combo.addItem(dt.name, dt)
        type_combo.setCurrentText(entry.dtype.name)
        type_combo.currentTextChanged.connect(lambda text, r=row: self._on_watch_type_changed(r, text))
        
        val_item  = _mk_item("???")

        self._watch_table.setItem(row, 0, desc_item)
        self._watch_table.setItem(row, 1, addr_item)
        self._watch_table.setCellWidget(row, 2, type_combo)
        self._watch_table.setItem(row, 3, val_item)

        chk_widget = QWidget()
        chk_lay    = QHBoxLayout(chk_widget)
        chk_lay.setContentsMargins(0, 0, 0, 0)
        chk_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chk = QCheckBox()
        chk.setChecked(entry.frozen)
        chk.stateChanged.connect(lambda state, r=row: self._on_freeze_toggled(r, bool(state)))
        chk_lay.addWidget(chk)
        self._watch_table.setCellWidget(row, 4, chk_widget)
        self._watch_table.setRowHeight(row, 24)

        self._watch_table.blockSignals(False)


def _mk_item(text: str, mono: bool = False, dim: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    if mono:
        item.setFont(QFont("Consolas", 9))
    if dim:
        item.setForeground(QColor("#8b949e"))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item
