"""
memory_map_dialog.py — Memory map viewer dialog.
Displays process memory layout with filtering and details.
"""
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QSplitter,
    QCheckBox, QComboBox, QSpinBox, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from core.memory_map import MemoryMap, MemoryRegion, MemoryState
from utils.i18n import tr
from utils.logger import log


class MemoryMapDialog(QDialog):
    """Dialog for viewing process memory map."""
    
    region_selected = pyqtSignal(int)  # Emits address when region selected
    
    def __init__(self, process_handle: int, parent=None):
        super().__init__(parent)
        self._handle = process_handle
        self._memory_map = MemoryMap(process_handle)
        self._regions: list[MemoryRegion] = []
        
        self.setWindowTitle(tr("memmap_title") if tr("memmap_title") != "!memmap_title!" else "🔬 Bellek Haritası")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        
        self._build_ui()
        self._refresh_map()
    
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Controls
        controls = QHBoxLayout()
        
        # Refresh button
        self._refresh_btn = QPushButton("🔄 " + (tr("btn_refresh") if tr("btn_refresh") != "!btn_refresh!" else "Yenile"))
        self._refresh_btn.clicked.connect(self._refresh_map)
        controls.addWidget(self._refresh_btn)
        
        # Export button
        self._export_btn = QPushButton("📤 " + (tr("btn_export") if tr("btn_export") != "!btn_export!" else "Dışa Aktar"))
        self._export_btn.clicked.connect(self._on_export)
        controls.addWidget(self._export_btn)
        
        controls.addStretch()
        
        # Stats label
        self._stats_lbl = QLabel("...")
        controls.addWidget(self._stats_lbl)
        
        layout.addLayout(controls)
        
        # Filter controls
        filter_group = QGroupBox(tr("grp_filters") if tr("grp_filters") != "!grp_filters!" else "Filtreler")
        filter_layout = QHBoxLayout(filter_group)
        
        self._readable_chk = QCheckBox(tr("chk_readable") if tr("chk_readable") != "!chk_readable!" else "Okunabilir")
        self._readable_chk.setChecked(True)
        self._readable_chk.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._readable_chk)
        
        self._writable_chk = QCheckBox(tr("chk_writable") if tr("chk_writable") != "!chk_writable!" else "Yazılabilir")
        self._writable_chk.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._writable_chk)
        
        self._executable_chk = QCheckBox(tr("chk_executable") if tr("chk_executable") != "!chk_executable!" else "Çalıştırılabilir")
        self._executable_chk.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._executable_chk)
        
        self._commit_chk = QCheckBox(tr("chk_committed") if tr("chk_committed") != "!chk_committed!" else "Commit")
        self._commit_chk.setChecked(True)
        self._commit_chk.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._commit_chk)
        
        filter_layout.addStretch()
        
        # Min size filter
        filter_layout.addWidget(QLabel(tr("lbl_min_size") if tr("lbl_min_size") != "!lbl_min_size!" else "Min Boyut (KB):"))
        self._min_size_spin = QSpinBox()
        self._min_size_spin.setRange(0, 1000000)
        self._min_size_spin.setSingleStep(4)
        self._min_size_spin.valueChanged.connect(self._apply_filters)
        filter_layout.addWidget(self._min_size_spin)
        
        layout.addWidget(filter_group)
        
        # Splitter for table and details
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Memory regions table
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels([
            tr("col_address") if tr("col_address") != "!col_address!" else "Adres",
            tr("col_size") if tr("col_size") != "!col_size!" else "Boyut",
            tr("mem_col_state") if tr("mem_col_state") != "!mem_col_state!" else "Durum",
            tr("mem_col_type") if tr("mem_col_type") != "!mem_col_type!" else "Tip",
            tr("mem_col_protection") if tr("mem_col_protection") != "!mem_col_protection!" else "Koruma",
            tr("mem_col_flags") if tr("mem_col_flags") != "!mem_col_flags!" else "Bayraklar",
            tr("mem_col_details") if tr("mem_col_details") != "!mem_col_details!" else "Detaylar"
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        splitter.addWidget(self._table)
        
        # Details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        details_layout.addWidget(QLabel(tr("lbl_region_details") if tr("lbl_region_details") != "!lbl_region_details!" else "Bölge Detayları:"))
        
        self._details_text = QTextEdit()
        self._details_text.setReadOnly(True)
        self._details_text.setMaximumHeight(150)
        details_layout.addWidget(self._details_text)
        
        splitter.addWidget(details_widget)
        splitter.setSizes([500, 150])
        
        layout.addWidget(splitter)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton(tr("btn_close") if tr("btn_close") != "!btn_close!" else "Kapat")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _refresh_map(self) -> None:
        """Refresh memory map."""
        if not self._handle:
            QMessageBox.warning(self, "Hata", "İşlem bağlı değil!")
            return
        
        self._regions = self._memory_map.scan()
        self._apply_filters()
        self._update_stats()
    
    def _apply_filters(self) -> None:
        """Apply filters to region list."""
        filtered = self._regions.copy()
        
        # Filter by protection
        if self._readable_chk.isChecked():
            filtered = [r for r in filtered if r.is_readable]
        
        if self._writable_chk.isChecked():
            filtered = [r for r in filtered if r.is_writable]
        
        if self._executable_chk.isChecked():
            filtered = [r for r in filtered if r.is_executable]
        
        if self._commit_chk.isChecked():
            filtered = [r for r in filtered if r.state == MemoryState.MEM_COMMIT.value]
        
        # Filter by size
        min_size = self._min_size_spin.value() * 1024  # KB to bytes
        if min_size > 0:
            filtered = [r for r in filtered if r.region_size >= min_size]
        
        self._populate_table(filtered)
    
    def _populate_table(self, regions: list[MemoryRegion]) -> None:
        """Populate table with regions."""
        self._table.setRowCount(len(regions))
        
        for row, region in enumerate(regions):
            # Address
            addr_item = QTableWidgetItem(f"0x{region.base_address:08X} - 0x{region.end_address:08X}")
            addr_item.setData(Qt.ItemDataRole.UserRole, region.base_address)
            self._table.setItem(row, 0, addr_item)
            
            # Size
            size_item = QTableWidgetItem(region.format_size(region.region_size))
            self._table.setItem(row, 1, size_item)
            
            # State
            state_item = QTableWidgetItem(region.state_name)
            self._set_state_color(state_item, region.state)
            self._table.setItem(row, 2, state_item)
            
            # Type
            type_item = QTableWidgetItem(region.type_name)
            self._table.setItem(row, 3, type_item)
            
            # Protection
            prot_item = QTableWidgetItem(region.protection_name)
            self._table.setItem(row, 4, prot_item)
            
            # Flags (R/W/X)
            flags = []
            if region.is_readable:
                flags.append("R")
            if region.is_writable:
                flags.append("W")
            if region.is_executable:
                flags.append("X")
            flags_item = QTableWidgetItem(" | ".join(flags) if flags else "-")
            self._table.setItem(row, 5, flags_item)
            
            # Details button
            details_btn = QPushButton(tr("btn_view") if tr("btn_view") != "!btn_view!" else "Gör")
            details_btn.setProperty("address", region.base_address)
            details_btn.clicked.connect(lambda checked, r=region: self._show_region_details(r))
            self._table.setCellWidget(row, 6, details_btn)
    
    def _set_state_color(self, item: QTableWidgetItem, state: int) -> None:
        """Set color based on memory state."""
        from core.memory_map import MemoryState
        
        colors = {
            MemoryState.MEM_COMMIT.value: QColor("#3fb950"),   # Green
            MemoryState.MEM_RESERVE.value: QColor("#d29922"),  # Yellow
            MemoryState.MEM_FREE.value: QColor("#8b949e"),     # Gray
        }
        
        if state in colors:
            brush = QBrush(colors[state])
            item.setForeground(brush)
    
    def _update_stats(self) -> None:
        """Update statistics label."""
        stats = self._memory_map.get_statistics()
        if stats:
            text = (f"Toplam: {stats['total_regions']} bölge | "
                   f"Commit: {stats['committed_size_human']} | "
                   f"Reserve: {stats['reserved_size_human']} | "
                   f"R:{stats['readable_regions']} W:{stats['writable_regions']} X:{stats['executable_regions']}")
        else:
            text = tr("no_data") if tr("no_data") != "!no_data!" else "Veri yok"
        
        self._stats_lbl.setText(text)
    
    def _on_selection_changed(self) -> None:
        """Handle table selection change."""
        selected = self._table.selectedItems()
        if selected:
            row = selected[0].row()
            address = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            region = self._memory_map.find_region(address)
            if region:
                self._show_region_details(region)
    
    def _on_cell_double_clicked(self, row: int, column: int) -> None:
        """Handle double click on table."""
        address = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.region_selected.emit(address)
    
    def _show_region_details(self, region: MemoryRegion) -> None:
        """Show region details in text panel."""
        details = f"""Bölge Detayları:
─────────────────────────
Başlangıç:     0x{region.base_address:08X}
Bitiş:         0x{region.end_address:08X}
Boyut:         {region.format_size(region.region_size)} ({region.region_size:,} bayt)

Durum:         {region.state_name}
Tip:           {region.type_name}
Koruma:        {region.protection_name}

Bayraklar:
  Okunabilir:  {'Evet' if region.is_readable else 'Hayır'}
  Yazılabilir: {'Evet' if region.is_writable else 'Hayır'}
  Çalıştırılabilir: {'Evet' if region.is_executable else 'Hayır'}

Allocation Base:    0x{region.allocation_base:08X}
Allocation Protect: 0x{region.allocation_protect:08X}
"""
        self._details_text.setText(details)
    
    def _on_export(self) -> None:
        """Export memory map to JSON."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("btn_export") if tr("btn_export") != "!btn_export!" else "Dışa Aktar",
            "memory_map.json",
            "JSON Files (*.json)"
        )
        
        if path:
            if self._memory_map.export_to_json(path):
                QMessageBox.information(self, "Başarılı", f"Bellek haritası kaydedildi:\n{path}")
            else:
                QMessageBox.critical(self, "Hata", "Dışa aktarma başarısız.")


def show_memory_map_dialog(process_handle: int, parent=None) -> None:
    """Show the memory map dialog."""
    if not process_handle:
        QMessageBox.warning(parent, "Hata", "İşlem bağlı değil!")
        return
    
    dialog = MemoryMapDialog(process_handle, parent)
    dialog.exec()
