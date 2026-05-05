"""
aob_dialog.py — AOB Pattern Generator and Scanner dialog.
"""
from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QSpinBox, QDoubleSpinBox, QCheckBox, QGroupBox, QFormLayout,
    QProgressBar, QFileDialog, QSplitter, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QBrush

from core.aob_scanner import (
    parse_aob_pattern, generate_pattern_from_address, 
    AOBPattern, AOBPatternLibrary, scan_aob_simple
)
from core.memory_io import MemoryIO
from utils.i18n import tr
from utils.logger import log


class AOBScanWorker(QThread):
    """Background worker for AOB scanning."""
    sig_progress = pyqtSignal(int)
    sig_result = pyqtSignal(list)  # List of addresses
    sig_error = pyqtSignal(str)
    
    def __init__(self, mem: MemoryIO, pattern: AOBPattern, parent=None):
        super().__init__(parent)
        self._mem = mem
        self._pattern = pattern
        self._cancelled = False
    
    def run(self):
        try:
            results = scan_aob_simple(
                self._mem,
                self._pattern.to_display_string(),
                self._on_progress
            )
            
            if self._cancelled:
                return
            
            self.sig_result.emit(results)
            
        except Exception as e:
            self.sig_error.emit(str(e))
    
    def _on_progress(self, pct: int):
        self.sig_progress.emit(pct)
    
    def cancel(self):
        self._cancelled = True


class AOBDialog(QDialog):
    """Dialog for AOB pattern generation and scanning."""
    
    sig_pattern_selected = pyqtSignal(str)  # Pattern string for scan
    sig_address_selected = pyqtSignal(int)  # Address to browse/jump to
    
    def __init__(self, mem: Optional[MemoryIO] = None, parent=None) -> None:
        super().__init__(parent)
        self._mem = mem
        self._pattern_lib = AOBPatternLibrary()
        self._scan_worker: Optional[AOBScanWorker] = None
        
        self.setWindowTitle(tr("aob_title") if tr("aob_title") != "!aob_title!" else "🔥 AOB Tarayıcı")
        self.setMinimumSize(700, 550)
        self.resize(800, 600)
        
        self._build_ui()
    
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Tabs
        tabs = QTabWidget()
        
        # Tab 1: Manual Pattern Entry
        tab_manual = self._build_manual_tab()
        tabs.addTab(tab_manual, tr("tab_manual_aob") if tr("tab_manual_aob") != "!tab_manual_aob!" else "✏️ Manuel Desen")
        
        # Tab 2: Pattern Generator
        tab_generator = self._build_generator_tab()
        tabs.addTab(tab_generator, tr("tab_generator") if tr("tab_generator") != "!tab_generator!" else "⚡ Oluşturucu")
        
        # Tab 3: Pattern Library
        tab_library = self._build_library_tab()
        tabs.addTab(tab_library, tr("tab_library") if tr("tab_library") != "!tab_library!" else "📚 Hazır Desenler")
        
        layout.addWidget(tabs)
        
        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self._close_btn = QPushButton(tr("btn_close") if tr("btn_close") != "!btn_close!" else "Kapat")
        self._close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self._close_btn)
        
        layout.addLayout(btn_layout)
    
    def _build_manual_tab(self) -> QWidget:
        """Build manual pattern entry tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Info
        info = QLabel(tr("aob_manual_info") if tr("aob_manual_info") != "!aob_manual_info!" 
                     else "AOB (Array of Bytes) deseni girin. ?? joker karakteridir.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #888;")
        layout.addWidget(info)
        
        # Pattern input
        pattern_layout = QHBoxLayout()
        pattern_layout.addWidget(QLabel(tr("lbl_pattern") if tr("lbl_pattern") != "!lbl_pattern!" else "Desen:"))
        
        self._manual_pattern_input = QLineEdit()
        self._manual_pattern_input.setPlaceholderText("FF 00 ?? A1 90")
        self._manual_pattern_input.setFont(QFont("Consolas", 11))
        self._manual_pattern_input.textChanged.connect(self._on_manual_pattern_changed)
        pattern_layout.addWidget(self._manual_pattern_input, stretch=1)
        
        self._parse_btn = QPushButton(tr("btn_parse") if tr("btn_parse") != "!btn_parse!" else "✓ Parse")
        self._parse_btn.clicked.connect(self._on_parse_pattern)
        pattern_layout.addWidget(self._parse_btn)
        
        layout.addLayout(pattern_layout)
        
        # Parsed preview
        preview_group = QGroupBox(tr("grp_preview") if tr("grp_preview") != "!grp_preview!" else "Önizleme")
        preview_layout = QVBoxLayout(preview_group)
        
        self._parsed_preview = QTextEdit()
        self._parsed_preview.setReadOnly(True)
        self._parsed_preview.setMaximumHeight(80)
        self._parsed_preview.setPlaceholderText(tr("parsed_placeholder") if tr("parsed_placeholder") != "!parsed_placeholder!" else "Parse edilmiş desen burada görünecek...")
        preview_layout.addWidget(self._parsed_preview)
        
        layout.addWidget(preview_group)
        
        # Scan button
        scan_layout = QHBoxLayout()
        scan_layout.addStretch()
        
        self._manual_scan_btn = QPushButton("🔍 " + (tr("btn_scan") if tr("btn_scan") != "!btn_scan!" else "Tara"))
        self._manual_scan_btn.setObjectName("primary_btn")
        self._manual_scan_btn.setEnabled(False)
        self._manual_scan_btn.clicked.connect(self._on_manual_scan)
        scan_layout.addWidget(self._manual_scan_btn)
        
        layout.addLayout(scan_layout)
        
        # Results
        results_group = QGroupBox(tr("grp_results") if tr("grp_results") != "!grp_results!" else "Sonuçlar")
        results_layout = QVBoxLayout(results_group)
        
        self._manual_results_table = QTableWidget(0, 3)
        self._manual_results_table.setHorizontalHeaderLabels([
            tr("col_address") if tr("col_address") != "!col_address!" else "Adres",
            tr("col_preview") if tr("col_preview") != "!col_preview!" else "Önizleme",
            tr("col_actions") if tr("col_actions") != "!col_actions!" else "İşlemler"
        ])
        self._manual_results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._manual_results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._manual_results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        results_layout.addWidget(self._manual_results_table)
        
        # Progress bar
        self._manual_progress = QProgressBar()
        self._manual_progress.setVisible(False)
        results_layout.addWidget(self._manual_progress)
        
        layout.addWidget(results_group)
        layout.addStretch()
        
        return widget
    
    def _build_generator_tab(self) -> QWidget:
        """Build pattern generator tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Info
        info = QLabel(tr("aob_gen_info") if tr("aob_gen_info") != "!aob_gen_info!" 
                     else "Bir adresten desen oluşturun. İşaretçiler otomatik olarak ?? ile değiştirilir.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #888;")
        layout.addWidget(info)
        
        # Address input
        addr_layout = QHBoxLayout()
        addr_layout.addWidget(QLabel(tr("lbl_address") if tr("lbl_address") != "!lbl_address!" else "Adres:"))
        
        self._gen_address_input = QLineEdit()
        self._gen_address_input.setPlaceholderText("0x7FF...")
        addr_layout.addWidget(self._gen_address_input, stretch=1)
        
        self._gen_read_btn = QPushButton(tr("btn_read") if tr("btn_read") != "!btn_read!" else "📖 Oku")
        self._gen_read_btn.clicked.connect(self._on_read_address)
        addr_layout.addWidget(self._gen_read_btn)
        
        layout.addLayout(addr_layout)
        
        # Options
        options_layout = QHBoxLayout()
        
        options_layout.addWidget(QLabel(tr("lbl_length") if tr("lbl_length") != "!lbl_length!" else "Uzunluk:"))
        self._gen_length_spin = QSpinBox()
        self._gen_length_spin.setRange(8, 64)
        self._gen_length_spin.setValue(16)
        options_layout.addWidget(self._gen_length_spin)
        
        self._gen_pointer_chk = QCheckBox(tr("chk_pointer_tol") if tr("chk_pointer_tol") != "!chk_pointer_tol!" else "İşaretçi toleransı")
        self._gen_pointer_chk.setChecked(True)
        options_layout.addWidget(self._gen_pointer_chk)
        
        options_layout.addStretch()
        
        layout.addLayout(options_layout)
        
        # Generated pattern
        pattern_group = QGroupBox(tr("grp_generated") if tr("grp_generated") != "!grp_generated!" else "Oluşturulan Desen")
        pattern_layout = QVBoxLayout(pattern_group)
        
        self._generated_pattern = QTextEdit()
        self._generated_pattern.setReadOnly(True)
        self._generated_pattern.setMaximumHeight(100)
        self._generated_pattern.setFont(QFont("Consolas", 10))
        pattern_layout.addWidget(self._generated_pattern)
        
        btn_layout = QHBoxLayout()
        self._gen_use_btn = QPushButton(tr("btn_use_pattern") if tr("btn_use_pattern") != "!btn_use_pattern!" else "✓ Bu Deseni Kullan")
        self._gen_use_btn.setEnabled(False)
        self._gen_use_btn.clicked.connect(self._on_use_generated_pattern)
        btn_layout.addWidget(self._gen_use_btn)
        
        self._gen_save_btn = QPushButton(tr("btn_save_pattern") if tr("btn_save_pattern") != "!btn_save_pattern!" else "💾 Kaydet")
        self._gen_save_btn.setEnabled(False)
        self._gen_save_btn.clicked.connect(self._on_save_generated_pattern)
        btn_layout.addWidget(self._gen_save_btn)
        
        btn_layout.addStretch()
        pattern_layout.addLayout(btn_layout)
        
        layout.addWidget(pattern_group)
        
        # Raw bytes preview
        raw_group = QGroupBox(tr("grp_raw") if tr("grp_raw") != "!grp_raw!" else "Ham Bayt Verisi")
        raw_layout = QVBoxLayout(raw_group)
        
        self._raw_bytes_preview = QTextEdit()
        self._raw_bytes_preview.setReadOnly(True)
        self._raw_bytes_preview.setMaximumHeight(80)
        self._raw_bytes_preview.setFont(QFont("Consolas", 9))
        raw_layout.addWidget(self._raw_bytes_preview)
        
        layout.addWidget(raw_group)
        layout.addStretch()
        
        return widget
    
    def _build_library_tab(self) -> QWidget:
        """Build pattern library tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        
        # Pattern list
        self._lib_table = QTableWidget(0, 3)
        self._lib_table.setHorizontalHeaderLabels([
            tr("col_name") if tr("col_name") != "!col_name!" else "İsim",
            tr("col_pattern") if tr("col_pattern") != "!col_pattern!" else "Desen",
            tr("col_desc") if tr("col_desc") != "!col_desc!" else "Açıklama"
        ])
        self._lib_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._lib_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._lib_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._lib_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._lib_table.doubleClicked.connect(self._on_lib_pattern_selected)
        layout.addWidget(self._lib_table)
        
        # Load library
        self._load_library()
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._lib_use_btn = QPushButton(tr("btn_use_selected") if tr("btn_use_selected") != "!btn_use_selected!" else "✓ Seçileni Kullan")
        self._lib_use_btn.clicked.connect(self._on_lib_pattern_selected)
        btn_layout.addWidget(self._lib_use_btn)
        
        btn_layout.addStretch()
        
        self._lib_import_btn = QPushButton(tr("btn_import_lib") if tr("btn_import_lib") != "!btn_import_lib!" else "📥 İçe Aktar")
        self._lib_import_btn.clicked.connect(self._on_import_library)
        btn_layout.addWidget(self._lib_import_btn)
        
        layout.addLayout(btn_layout)
        
        return widget
    
    def _load_library(self) -> None:
        """Load pattern library into table."""
        patterns = self._pattern_lib.list_patterns()
        self._lib_table.setRowCount(len(patterns))
        
        for row, (name, desc) in enumerate(patterns):
            pat = self._pattern_lib.get_pattern(name)
            
            self._lib_table.setItem(row, 0, QTableWidgetItem(name))
            self._lib_table.setItem(row, 1, QTableWidgetItem(pat.to_display_string() if pat else ""))
            self._lib_table.setItem(row, 2, QTableWidgetItem(desc))
            
            # Store pattern name in first column
            self._lib_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, name)
    
    def _on_manual_pattern_changed(self, text: str) -> None:
        """Handle pattern input change."""
        self._manual_scan_btn.setEnabled(bool(text.strip()))
    
    def _on_parse_pattern(self) -> None:
        """Parse and validate the manual pattern."""
        text = self._manual_pattern_input.text().strip()
        if not text:
            return
        
        try:
            pattern = parse_aob_pattern(text)
            
            preview = f"✓ Geçerli desen\n"
            preview += f"Uzunluk: {pattern.length} bayt\n"
            preview += f"Joker: {pattern.mask.count('?')} / {pattern.length}\n"
            preview += f"Desen: {pattern.to_display_string()}"
            
            self._parsed_preview.setText(preview)
            self._parsed_preview.setStyleSheet("color: #3fb950;")
            
        except ValueError as e:
            self._parsed_preview.setText(f"✗ Hata: {e}")
            self._parsed_preview.setStyleSheet("color: #e94560;")
    
    def _on_manual_scan(self) -> None:
        """Start AOB scan with manual pattern."""
        if not self._mem:
            QMessageBox.warning(self, "Hata", "Önce bir işleme bağlanmalısınız.")
            return
        
        text = self._manual_pattern_input.text().strip()
        if not text:
            return
        
        try:
            pattern = parse_aob_pattern(text)
        except ValueError as e:
            QMessageBox.warning(self, "Geçersiz Desen", str(e))
            return
        
        # Clear previous results
        self._manual_results_table.setRowCount(0)
        self._manual_progress.setValue(0)
        self._manual_progress.setVisible(True)
        
        # Start scan in background
        self._scan_worker = AOBScanWorker(self._mem, pattern)
        self._scan_worker.sig_progress.connect(self._on_scan_progress)
        self._scan_worker.sig_result.connect(self._on_scan_result)
        self._scan_worker.sig_error.connect(self._on_scan_error)
        self._scan_worker.start()
    
    def _on_scan_progress(self, pct: int) -> None:
        """Update scan progress."""
        self._manual_progress.setValue(pct)
    
    def _on_scan_result(self, addresses: List[int]) -> None:
        """Handle scan results."""
        self._manual_progress.setVisible(False)
        
        self._manual_results_table.setRowCount(len(addresses))
        
        for row, addr in enumerate(addresses[:1000]):  # Limit to 1000 results
            self._manual_results_table.setItem(row, 0, QTableWidgetItem(f"0x{addr:016X}"))
            self._manual_results_table.setItem(row, 1, QTableWidgetItem("..."))
            
            # Add browse button
            btn = QPushButton("🔍")
            btn.setFixedSize(30, 24)
            btn.clicked.connect(lambda checked, a=addr: self._on_browse_address(a))
            self._manual_results_table.setCellWidget(row, 2, btn)
            
            # Store address
            self._manual_results_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, addr)
        
        if len(addresses) > 1000:
            QMessageBox.information(self, "Sonuç", f"{len(addresses)} sonuç bulundu. İlk 1000 gösteriliyor.")
        else:
            QMessageBox.information(self, "Sonuç", f"{len(addresses)} adres bulundu.")
    
    def _on_scan_error(self, msg: str) -> None:
        """Handle scan error."""
        self._manual_progress.setVisible(False)
        QMessageBox.critical(self, "Tarama Hatası", msg)
    
    def _on_read_address(self) -> None:
        """Read memory and generate pattern from address."""
        if not self._mem:
            QMessageBox.warning(self, "Hata", "Önce bir işleme bağlanmalısınız.")
            return
        
        addr_text = self._gen_address_input.text().strip()
        if not addr_text:
            return
        
        try:
            if addr_text.startswith("0x"):
                address = int(addr_text, 16)
            else:
                address = int(addr_text)
        except ValueError:
            QMessageBox.warning(self, "Geçersiz Adres", "Adres formatı hatalı.")
            return
        
        length = self._gen_length_spin.value()
        pointer_tol = self._gen_pointer_chk.isChecked()
        
        pattern = generate_pattern_from_address(self._mem, address, length, pointer_tol)
        
        if not pattern:
            QMessageBox.warning(self, "Okuma Hatası", "Adresten okuma başarısız.")
            return
        
        # Display generated pattern
        self._generated_pattern.setText(pattern.to_display_string())
        self._generated_pattern.setStyleSheet("color: #58a6ff;")
        
        # Display raw bytes
        raw_hex = ' '.join(f'{b:02X}' for b in pattern.bytes_pattern)
        raw_ascii = ''.join(chr(b) if 32 <= b < 127 else '.' for b in pattern.bytes_pattern)
        self._raw_bytes_preview.setText(f"HEX:  {raw_hex}\nASCII: {raw_ascii}")
        
        self._gen_use_btn.setEnabled(True)
        self._gen_save_btn.setEnabled(True)
        
        self._last_generated_pattern = pattern
    
    def _on_use_generated_pattern(self) -> None:
        """Use generated pattern in manual tab."""
        if hasattr(self, '_last_generated_pattern'):
            self._manual_pattern_input.setText(self._last_generated_pattern.to_display_string())
            # Switch to first tab
            self.parent().findChild(QTabWidget).setCurrentIndex(0)
    
    def _on_save_generated_pattern(self) -> None:
        """Save generated pattern to library."""
        if not hasattr(self, '_last_generated_pattern'):
            return
        
        name, ok = QInputDialog.getText(self, "Desen Kaydet", "Desen adı:")
        if ok and name.strip():
            self._pattern_lib.add_pattern(name.strip(), self._last_generated_pattern)
            self._load_library()
            QMessageBox.information(self, "Başarılı", "Desen kütüphaneye eklendi.")
    
    def _on_lib_pattern_selected(self) -> None:
        """Use selected library pattern."""
        row = self._lib_table.currentRow()
        if row < 0:
            return
        
        name = self._lib_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        pattern = self._pattern_lib.get_pattern(name)
        
        if pattern:
            self._manual_pattern_input.setText(pattern.to_display_string())
            self.parent().findChild(QTabWidget).setCurrentIndex(0)
    
    def _on_import_library(self) -> None:
        """Import pattern library from file."""
        # TODO: Implement library import
        QMessageBox.information(self, "Bilgi", "Bu özellik yakında eklenecek.")
    
    def _on_browse_address(self, address: int) -> None:
        """Emit signal to browse address."""
        self.sig_address_selected.emit(address)
    
    def set_memory(self, mem: MemoryIO) -> None:
        """Set memory IO for scanning."""
        self._mem = mem
    
    def closeEvent(self, event) -> None:
        """Clean up on close."""
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.cancel()
            self._scan_worker.wait(1000)
        event.accept()


def show_aob_dialog(mem: Optional[MemoryIO] = None, parent=None) -> Optional[str]:
    """
    Show AOB dialog.
    
    Returns:
        Selected pattern string or None
    """
    dialog = AOBDialog(mem, parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        # Return pattern if user clicked OK
        return dialog._manual_pattern_input.text().strip()
    return None
