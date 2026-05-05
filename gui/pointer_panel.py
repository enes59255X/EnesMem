"""
pointer_panel.py — Pointer chain resolution panel (dockable window).
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox,
    QAbstractItemView, QFormLayout, QMessageBox, QMenu,
    QFileDialog, QApplication, QTabWidget,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QKeyEvent, QKeySequence, QShortcut

from utils.converters import format_address, format_value
from utils.patterns import DataType
from utils.i18n import tr


class PointerPanel(QWidget):
    """
    Signals:
        sig_resolve(module_name, offsets_str, dtype) -> result address
    """
    sig_resolve = pyqtSignal(str, str, object, int, int)   # module, offsets_csv, DataType, depth, max_offset
    sig_add_chain = pyqtSignal(str, list, object, object) # module_name, offsets_list, DataType, final_addr
    sig_filter = pyqtSignal(object, object)              # expected_value, DataType
    sig_save = pyqtSignal()
    sig_load = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("ptr_title"))
        self.setMinimumSize(480, 350)
        self.resize(550, 400)
        self._is_attached = False
        self._status_lbl = None
        self._build_ui()
        self.retranslate_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Tab widget for clean separation
        self._tabs = QTabWidget()
        
        # === TAB 1: Manual Resolve ===
        tab_manual = QWidget()
        manual_lay = QVBoxLayout(tab_manual)
        manual_lay.setContentsMargins(8, 8, 8, 8)
        manual_lay.setSpacing(8)
        
        # Modül seçimi
        row1 = QHBoxLayout()
        self._module_combo = QComboBox()
        self._module_combo.setEditable(True)
        self._module_combo.addItem("__scan__")
        self._module_combo.setFixedWidth(180)
        row1.addWidget(QLabel("Modül:"))
        row1.addWidget(self._module_combo, stretch=1)
        manual_lay.addLayout(row1)
        
        # Offset'ler
        row2 = QHBoxLayout()
        self._offsets_input = QLineEdit()
        self._offsets_input.setPlaceholderText(tr("ptr_offset_hint") if tr("ptr_offset_hint") != "!ptr_offset_hint!" else "Örn: 0x10, 0x20, 0x30")
        self._offsets_input.returnPressed.connect(self._on_resolve)
        row2.addWidget(QLabel("Offsetler:"))
        row2.addWidget(self._offsets_input, stretch=1)
        manual_lay.addLayout(row2)
        
        # Veri tipi + Çözümle butonu
        row3 = QHBoxLayout()
        self._dtype_combo = QComboBox()
        for dt in DataType:
            self._dtype_combo.addItem(dt.value, userData=dt)
        self._dtype_combo.setCurrentIndex(2)
        self._dtype_combo.setFixedWidth(100)
        row3.addWidget(QLabel("Veri Tipi:"))
        row3.addWidget(self._dtype_combo)
        
        self._resolve_btn = QPushButton("⚡ Çözümle")
        self._resolve_btn.setObjectName("primary_btn")
        self._resolve_btn.setFixedHeight(28)
        self._resolve_btn.setToolTip("Pointer zincirini çöz ve adresi bul")
        self._resolve_btn.clicked.connect(self._on_resolve)
        row3.addWidget(self._resolve_btn)
        row3.addStretch()
        manual_lay.addLayout(row3)
        
        # Durum çubuğu (işlem bağlantı durumu)
        self._status_lbl = QLabel("⚠️ İşleme bağlanmadı — Lütfen önce bir işlem seçin")
        self._status_lbl.setObjectName("status_label")
        self._status_lbl.setStyleSheet("color: #e94560; font-size: 11px; padding: 4px;")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        manual_lay.addWidget(self._status_lbl)
        
        # Sonuç gösterimi
        self._result_lbl = QLabel(tr("ptr_result_waiting") if tr("ptr_result_waiting") != "!ptr_result_waiting!" else "Hazır — Offsetleri gir ve Çözümle'ye tıkla")
        self._result_lbl.setObjectName("pointer_result_lbl")
        self._result_lbl.setFont(QFont("Consolas", 9))
        self._result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_lbl.setWordWrap(True)
        manual_lay.addWidget(self._result_lbl)
        manual_lay.addStretch()
        
        self._tabs.addTab(tab_manual, "⚡ Elle Çözümle")
        
        # === TAB 2: Chain Scanner ===
        tab_scanner = QWidget()
        scan_lay = QVBoxLayout(tab_scanner)
        scan_lay.setContentsMargins(8, 8, 8, 8)
        scan_lay.setSpacing(6)
        
        # Hedef adres satırı
        target_row = QHBoxLayout()
        self._target_input = QLineEdit()
        self._target_input.setPlaceholderText(tr("ptr_target_hint") if tr("ptr_target_hint") != "!ptr_target_hint!" else "Örn: 0x29DEE4A6980 (bulunacak adres)")
        target_row.addWidget(QLabel("Hedef:"))
        target_row.addWidget(self._target_input, stretch=1)
        
        self._scan_btn = QPushButton("🔍 Tara")
        self._scan_btn.setFixedHeight(26)
        self._scan_btn.setFixedWidth(70)
        self._scan_btn.setToolTip("Bu adrese giden pointer zincirlerini tara")
        self._scan_btn.clicked.connect(self._on_chain_scan)
        target_row.addWidget(self._scan_btn)
        scan_lay.addLayout(target_row)
        
        # Ayarlar satırı
        opts_row = QHBoxLayout()
        opts_row.setSpacing(8)
        
        self._lbl_depth = QLabel("Derinlik:")
        self._depth_spin = QComboBox()
        for i in range(2, 8):
            self._depth_spin.addItem(str(i), i)
        self._depth_spin.setCurrentIndex(2)
        self._depth_spin.setFixedWidth(50)
        self._depth_spin.setToolTip("Pointer zincirinin maksimum derinliği (seviye sayısı)")
        
        self._lbl_max_offset = QLabel("Max Offset:")
        self._offset_input = QLineEdit("2048")
        self._offset_input.setFixedWidth(60)
        self._offset_input.setToolTip("Her seviyede taranacak maksimum offset değeri")
        
        self._chain_dtype_combo = QComboBox()
        for dt in DataType:
            self._chain_dtype_combo.addItem(dt.value, userData=dt)
        self._chain_dtype_combo.setCurrentIndex(2)
        self._chain_dtype_combo.setFixedWidth(80)
        
        opts_row.addWidget(self._lbl_depth)
        opts_row.addWidget(self._depth_spin)
        opts_row.addWidget(self._lbl_max_offset)
        opts_row.addWidget(self._offset_input)
        opts_row.addWidget(QLabel("Değer:"))
        opts_row.addWidget(self._chain_dtype_combo)
        opts_row.addStretch()
        
        self._filter_btn = QPushButton("🎯 Filtrele")
        self._filter_btn.setFixedHeight(24)
        self._filter_btn.setToolTip("Bulunan zincirleri değere göre filtrele")
        self._filter_btn.clicked.connect(self._on_chain_filter)
        opts_row.addWidget(self._filter_btn)
        
        self._save_btn = QPushButton("💾")
        self._save_btn.setFixedHeight(24)
        self._save_btn.setFixedWidth(30)
        self._save_btn.setToolTip("Zincirleri kaydet")
        self._save_btn.clicked.connect(self.sig_save.emit)
        opts_row.addWidget(self._save_btn)

        self._load_btn = QPushButton("📁")
        self._load_btn.setFixedHeight(24)
        self._load_btn.setFixedWidth(30)
        self._load_btn.setToolTip("Zincirleri yükle")
        self._load_btn.clicked.connect(self.sig_load.emit)
        opts_row.addWidget(self._load_btn)
        scan_lay.addLayout(opts_row)
        
        # Table
        self._chain_table = QTableWidget(0, 4)
        self._chain_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._chain_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._chain_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._chain_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._chain_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._chain_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._chain_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._chain_table.setAlternatingRowColors(True)
        self._chain_table.verticalHeader().setVisible(False)
        self._chain_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._chain_table.customContextMenuRequested.connect(self._on_chain_context_menu)
        self._chain_table.doubleClicked.connect(self._on_chain_double_click)
        scan_lay.addWidget(self._chain_table, stretch=1)
        
        # Ctrl+C shortcut
        self._copy_shortcut = QShortcut(QKeySequence("Ctrl+C"), self._chain_table)
        self._copy_shortcut.activated.connect(self._copy_selected_offsets)
        
        self._tabs.addTab(tab_scanner, "🔍 Otomatik Bul")
        root.addWidget(self._tabs, stretch=1)

    def retranslate_ui(self) -> None:
        self.setWindowTitle(tr("ptr_title") if tr("ptr_title") != "!ptr_title!" else "Pointer Scanner")
        
        # Tab labels
        self._tabs.setTabText(0, tr("ptr_tab_manual") if tr("ptr_tab_manual") != "!ptr_tab_manual!" else "⚡ Elle Çözümle")
        self._tabs.setTabText(1, tr("ptr_tab_scanner") if tr("ptr_tab_scanner") != "!ptr_tab_scanner!" else "🔍 Otomatik Bul")
        
        # Table headers
        self._chain_table.setHorizontalHeaderLabels([
            tr("ptr_col_module") if tr("ptr_col_module") != "!ptr_col_module!" else "Modül",
            tr("ptr_col_offsets") if tr("ptr_col_offsets") != "!ptr_col_offsets!" else "Offsetler",
            tr("ptr_col_address") if tr("ptr_col_address") != "!ptr_col_address!" else "Adres",
            tr("ptr_col_value") if tr("ptr_col_value") != "!ptr_col_value!" else "Değer"
        ])
        
        # Reset result label if it was default
        if not hasattr(self, "_last_address") or self._last_address is None:
            self._result_lbl.setText("—")

    def _check_attached(self) -> bool:
        """İşlem bağlantısını kontrol et, bağlı değilse uyarı göster."""
        if not self._is_attached:
            title = tr("msg_no_process") if tr("msg_no_process") != "!msg_no_process!" else "İşlem Seçilmemiş"
            msg = tr("msg_attach_first") if tr("msg_attach_first") != "!msg_attach_first!" else "Pointer işlemleri için önce bir işleme bağlanmalısınız.\n\nAna pencereden '⚙ İşlem Seç' butonunu kullanarak bir işlem seçin."
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(title)
            msg_box.setText("⚠️ İşlem Bağlantısı Gerekli")
            msg_box.setInformativeText(msg)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return False
        return True

    def set_attached(self, attached: bool) -> None:
        """İşlem bağlantı durumunu güncelle."""
        self._is_attached = attached
        if self._status_lbl:
            if attached:
                self._status_lbl.setText("✅ İşleme bağlandı — Pointer işlemleri hazır")
                self._status_lbl.setStyleSheet("color: #3fb950; font-size: 11px; padding: 4px;")
                self._resolve_btn.setEnabled(True)
                self._scan_btn.setEnabled(True)
                self._filter_btn.setEnabled(True)
            else:
                self._status_lbl.setText("⚠️ İşleme bağlanmadı — Lütfen önce bir işlem seçin")
                self._status_lbl.setStyleSheet("color: #e94560; font-size: 11px; padding: 4px;")
                self._resolve_btn.setEnabled(False)
                self._scan_btn.setEnabled(False)
                self._filter_btn.setEnabled(False)

    def _on_resolve(self) -> None:
        if not self._check_attached():
            return
        module  = self._module_combo.currentText().strip()
        offsets = self._offsets_input.text().strip()
        dtype   = self._dtype_combo.currentData()
        if not module or not offsets:
            QMessageBox.warning(self, tr("msg_no_scan") if tr("msg_no_scan") != "!msg_no_scan!" else "Eksik Bilgi", 
                              tr("msg_bad_offsets") if tr("msg_bad_offsets") != "!msg_bad_offsets!" else "Lütfen modül ve offset değerlerini girin.")
            return
        # Depth/Offset don't matter for manual resolve but we send defaults to keep sig happy
        self.sig_resolve.emit(module, offsets, dtype, 3, 2048)

    def _on_chain_scan(self) -> None:
        if not self._check_attached():
            return
        # Trigger via main_window
        target = self._target_input.text().strip()
        if not target:
            QMessageBox.warning(self, tr("msg_no_target") if tr("msg_no_target") != "!msg_no_target!" else "Hedef Adres Gerekli", 
                              tr("msg_enter_target") if tr("msg_enter_target") != "!msg_enter_target!" else "Lütfen taranacak hedef adresi girin.")
            return
        depth = int(self._depth_spin.currentText())
        try:
            offset_str = self._offset_input.text().strip().lower()
            if offset_str.startswith("0x"):
                offset = int(offset_str, 16)
            else:
                offset = int(offset_str)
        except ValueError:
            offset = 2048
        self.sig_resolve.emit("__scan__", target, self._chain_dtype_combo.currentData(), depth, offset)

    def _on_chain_filter(self) -> None:
        if not self._check_attached():
            return
        target_str = self._target_input.text().strip()
        if not target_str:
            QMessageBox.warning(self, tr("msg_no_filter") if tr("msg_no_filter") != "!msg_no_filter!" else "Filtre Değeri Gerekli", 
                              tr("msg_enter_filter") if tr("msg_enter_filter") != "!msg_enter_filter!" else "Lütfen filtrelemek için bir değer girin.")
            return
        dtype = self._chain_dtype_combo.currentData()
        from utils.converters import parse_user_input
        val = parse_user_input(target_str, dtype)
        if val is None:
            QMessageBox.warning(self, "Bad Value", f"Cannot parse '{target_str}' as {dtype.name}. Enter the NEW value to filter.")
            return
        self.sig_filter.emit(val, dtype)

    def _on_chain_dtype_changed(self) -> None:
        dtype = self._chain_dtype_combo.currentData()
        self.sig_filter.emit(None, dtype)

    def _on_chain_double_click(self, idx) -> None:
        row = idx.row()
        mod_item = self._chain_table.item(row, 0)
        off_item = self._chain_table.item(row, 1)
        if mod_item and off_item:
            self._module_combo.setCurrentText(mod_item.text())
            self._offsets_input.setText(off_item.text())

    def _on_chain_context_menu(self, pos) -> None:
        selected_rows = set()
        for item in self._chain_table.selectedItems():
            selected_rows.add(item.row())
        
        row = self._chain_table.rowAt(pos.y())
        if row < 0 and not selected_rows:
            return
        if row >= 0 and row not in selected_rows:
            self._chain_table.selectRow(row)
            selected_rows = {row}
        
        menu = QMenu(self)
        
        if len(selected_rows) == 1:
            item = self._chain_table.item(row, 0)
            chain = item.data(Qt.ItemDataRole.UserRole) if item else None
            if chain:
                act_add = menu.addAction("➕ " + ((tr("menu_add_watchlist") if tr("menu_add_watchlist") != "!menu_add_watchlist!" else "İzleme Listesine Ekle")))
                act_copy = menu.addAction("📋 Kopyala (Modül + Offset)")
                act_copy_raw = menu.addAction("📋 Sadece Offsetleri Kopyala")
                
                action = menu.exec(self._chain_table.viewport().mapToGlobal(pos))
                if action == act_add:
                    self.sig_add_chain.emit(chain.module_name, chain.offsets, self._dtype_combo.currentData(), chain.final_addr)
                elif action == act_copy:
                    offsets_str = f"{chain.module_name} + " + " + ".join(f"0x{o:X}" for o in chain.offsets)
                    QApplication.clipboard().setText(offsets_str)
                elif action == act_copy_raw:
                    offsets_str = ", ".join(f"0x{o:X}" for o in chain.offsets)
                    QApplication.clipboard().setText(offsets_str)
        else:
            act_copy_all = menu.addAction(f"📋 {len(selected_rows)} Zinciri Kopyala")
            action = menu.exec(self._chain_table.viewport().mapToGlobal(pos))
            if action == act_copy_all:
                lines = []
                for r in sorted(selected_rows):
                    item = self._chain_table.item(r, 0)
                    chain = item.data(Qt.ItemDataRole.UserRole) if item else None
                    if chain:
                        offsets_str = f"{chain.module_name} + " + " + ".join(f"0x{o:X}" for o in chain.offsets)
                        lines.append(offsets_str)
                QApplication.clipboard().setText("\n".join(lines))

    def _copy_selected_offsets(self) -> None:
        selected_rows = set()
        for item in self._chain_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        lines = []
        for r in sorted(selected_rows):
            item = self._chain_table.item(r, 0)
            chain = item.data(Qt.ItemDataRole.UserRole) if item else None
            if chain:
                offsets_str = f"{chain.module_name} + " + " + ".join(f"0x{o:X}" for o in chain.offsets)
                lines.append(offsets_str)
        
        if lines:
            QApplication.clipboard().setText("\n".join(lines))

    def set_result(self, address: int | None, value_str: str = "") -> None:
        self._last_address = address
        if address is None:
            self._result_lbl.setText(tr("ptr_result").format(tr("ptr_failed")))
            self._result_lbl.setStyleSheet("color: #e94560;")
        else:
            res_text = format_address(address)
            if value_str:
                res_text += f"  =  {value_str}"
            self._result_lbl.setText(tr("ptr_result").format(res_text))
            self._result_lbl.setStyleSheet("color: #3fb950;")

    def set_scanning(self, active: bool) -> None:
        self._scan_btn.setEnabled(not active)
        self._resolve_btn.setEnabled(not active)
        if active:
            self._scan_btn.setText("⏳ " + tr("msg_scanning"))
        else:
            self._scan_btn.setText("🔍 Tara")

    def populate_chains(self, chains: list) -> None:
        self._chain_table.setRowCount(len(chains))
        for row, chain in enumerate(chains):
            offsets_str = ", ".join(f"0x{o:X}" for o in chain.offsets)
            
            item_mod = QTableWidgetItem(chain.module_name)
            item_mod.setData(Qt.ItemDataRole.UserRole, chain)
            
            self._chain_table.setItem(row, 0, item_mod)
            self._chain_table.setItem(row, 1, QTableWidgetItem(offsets_str))
            self._chain_table.setItem(row, 2, QTableWidgetItem(format_address(chain.final_addr)))
            
            # 4th Column: Value (resolved if possible)
            val_str = str(chain.value) if chain.value is not None else "???"
            item_val = QTableWidgetItem(val_str)
            item_val.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._chain_table.setItem(row, 3, item_val)
            
            self._chain_table.setRowHeight(row, 22)

    def refresh_live_values(self, ptr_sc, mem) -> None:
        if not ptr_sc or not mem:
            return
        
        # Validate memory handle
        if not getattr(mem, '_handle', None):
            return
        
        try:
            # Only update visible rows to prevent lag
            rect = self._chain_table.viewport().rect()
            top_row = self._chain_table.rowAt(rect.top())
            bottom_row = self._chain_table.rowAt(rect.bottom())
            
            if top_row == -1: top_row = 0
            if bottom_row == -1: bottom_row = self._chain_table.rowCount() - 1
            if bottom_row >= self._chain_table.rowCount(): bottom_row = self._chain_table.rowCount() - 1
            
            dtype = self._chain_dtype_combo.currentData()
            if not dtype:
                return
        except Exception:
            return
        
        for row in range(top_row, bottom_row + 1):
            try:
                item_mod = self._chain_table.item(row, 0)
                if not item_mod: 
                    continue
                
                chain = item_mod.data(Qt.ItemDataRole.UserRole)
                if not chain: 
                    continue
                
                # Validate handle before each read
                if not getattr(mem, '_handle', None):
                    return
                
                # Resolve live
                addr = ptr_sc.resolve_from_module(chain.module_name, chain.offsets)
                if addr is not None:
                    chain.final_addr = addr
                    addr_item = self._chain_table.item(row, 2)
                    if addr_item:
                        addr_item.setText(format_address(addr))
                    
                    val = mem.read_value(addr, dtype)
                    val_item = self._chain_table.item(row, 3)
                    if val_item:
                        if val is not None:
                            from utils.converters import format_value
                            chain.value = format_value(val, dtype)
                            val_item.setText(chain.value)
                        else:
                            val_item.setText("???")
                else:
                    addr_item = self._chain_table.item(row, 2)
                    val_item = self._chain_table.item(row, 3)
                    if addr_item:
                        addr_item.setText("???")
                    if val_item:
                        val_item.setText("???")
            except Exception:
                # Skip problematic rows, don't crash
                continue
