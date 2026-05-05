"""
watchlist_tree.py — Tree-based hierarchical watchlist with groups.
Replaces/extends the flat watchlist table in results_table.py.
"""
from typing import Optional, List, Callable

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QCheckBox, QLabel, QHeaderView, QMenu,
    QComboBox, QInputDialog, QMessageBox, QColorDialog, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QBrush, QFont

from utils.patterns import DataType
from utils.converters import format_address, format_value
from utils.i18n import tr
from utils.logger import log
from utils.watchlist_groups import group_manager, WatchlistGroup, GroupColor


class WatchlistTree(QWidget):
    """
    Hierarchical watchlist with grouping support.
    
    Signals:
        sig_entry_clicked(address, dtype): Entry clicked/selected
        sig_freeze_toggled(address, dtype, freeze): Freeze state changed
        sig_value_changed(address, dtype, new_value): Value edited
        sig_entry_deleted(address): Entry deleted
        sig_entry_moved(entry_index, from_group, to_group): Entry moved between groups
    """
    sig_entry_clicked = pyqtSignal(int, object)  # address, DataType
    sig_freeze_toggled = pyqtSignal(int, object, bool)  # address, DataType, freeze
    sig_value_changed = pyqtSignal(int, object, str)  # address, DataType, new_value
    sig_entry_deleted = pyqtSignal(int)  # address
    sig_entry_moved = pyqtSignal(int, str, str)  # entry_index, from_group, to_group
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._watchlist_entries = []  # Reference to external watchlist
        self._entry_id_map = {}  # address -> entry reference mapping
        self._build_ui()
        self._load_groups()
    
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Controls header
        header = QHBoxLayout()
        
        # Group management buttons
        self._new_group_btn = QPushButton("📁 " + (tr("btn_new_group") if tr("btn_new_group") != "!btn_new_group!" else "Yeni Grup"))
        self._new_group_btn.setFixedHeight(26)
        self._new_group_btn.clicked.connect(self._on_new_group)
        header.addWidget(self._new_group_btn)
        
        self._expand_all_btn = QPushButton("📂 " + (tr("btn_expand") if tr("btn_expand") != "!btn_expand!" else "Aç"))
        self._expand_all_btn.setFixedHeight(26)
        self._expand_all_btn.clicked.connect(self._on_expand_all)
        header.addWidget(self._expand_all_btn)
        
        self._collapse_all_btn = QPushButton("📁 " + (tr("btn_collapse") if tr("btn_collapse") != "!btn_collapse!" else "Kapat"))
        self._collapse_all_btn.setFixedHeight(26)
        self._collapse_all_btn.clicked.connect(self._on_collapse_all)
        header.addWidget(self._collapse_all_btn)
        
        header.addStretch()
        
        # Filter
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText(tr("placeholder_filter") if tr("placeholder_filter") != "!placeholder_filter!" else "Filtrele...")
        self._filter_input.setFixedWidth(150)
        self._filter_input.textChanged.connect(self._on_filter_changed)
        header.addWidget(self._filter_input)
        
        # Frozen only checkbox
        self._frozen_only_chk = QCheckBox(tr("chk_frozen_only") if tr("chk_frozen_only") != "!chk_frozen_only!" else "Sadece Dondurulmuş")
        self._frozen_only_chk.stateChanged.connect(self._on_frozen_filter_changed)
        header.addWidget(self._frozen_only_chk)
        
        layout.addLayout(header)
        
        # Tree widget
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels([
            tr("col_description") if tr("col_description") != "!col_description!" else "Açıklama",
            tr("col_address") if tr("col_address") != "!col_address!" else "Adres",
            tr("col_value") if tr("col_value") != "!col_value!" else "Değer",
            tr("col_type") if tr("col_type") != "!col_type!" else "Tip",
            tr("col_frozen") if tr("col_frozen") != "!col_frozen!" else "Dondur"
        ])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setDragEnabled(True)
        self._tree.setAcceptDrops(True)
        self._tree.setDropIndicatorShown(True)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._tree.itemChanged.connect(self._on_item_changed)
        
        layout.addWidget(self._tree)
        
        # Bulk action buttons
        bulk_layout = QHBoxLayout()
        
        self._freeze_all_btn = QPushButton("❄️ " + (tr("btn_freeze_all") if tr("btn_freeze_all") != "!btn_freeze_all!" else "Tümünü Dondur"))
        self._freeze_all_btn.setFixedHeight(26)
        self._freeze_all_btn.clicked.connect(self._on_freeze_all)
        bulk_layout.addWidget(self._freeze_all_btn)
        
        self._unfreeze_all_btn = QPushButton("🔥 " + (tr("btn_unfreeze_all") if tr("btn_unfreeze_all") != "!btn_unfreeze_all!" else "Çöz"))
        self._unfreeze_all_btn.setFixedHeight(26)
        self._unfreeze_all_btn.clicked.connect(self._on_unfreeze_all)
        bulk_layout.addWidget(self._unfreeze_all_btn)
        
        self._delete_selected_btn = QPushButton("🗑️ " + (tr("btn_delete_selected") if tr("btn_delete_selected") != "!btn_delete_selected!" else "Seçiliyi Sil"))
        self._delete_selected_btn.setFixedHeight(26)
        self._delete_selected_btn.clicked.connect(self._on_delete_selected)
        bulk_layout.addWidget(self._delete_selected_btn)
        
        bulk_layout.addStretch()
        
        layout.addLayout(bulk_layout)
    
    def _load_groups(self) -> None:
        """Load saved groups."""
        group_manager.load_groups()
        self._rebuild_tree()
    
    def set_watchlist(self, entries: list) -> None:
        """Set the external watchlist reference."""
        self._watchlist_entries = entries
        self._rebuild_tree()
    
    def _rebuild_tree(self) -> None:
        """Rebuild the entire tree from groups and watchlist."""
        self._tree.clear()
        
        if not self._watchlist_entries:
            return
        
        # Create group items
        group_items = {}
        for group in group_manager.get_all_groups():
            item = QTreeWidgetItem(self._tree)
            item.setText(0, group.name)
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "group", "group": group})
            
            # Set group color
            color = QColor(group.color)
            for col in range(5):
                item.setForeground(col, QBrush(color))
            
            font = QFont()
            font.setBold(True)
            item.setFont(0, font)
            
            item.setExpanded(group.expanded)
            group_items[group.name] = item
        
        # Add entries to their groups
        filter_text = self._filter_input.text().lower()
        show_frozen_only = self._frozen_only_chk.isChecked()
        
        for idx, entry in enumerate(self._watchlist_entries):
            # Find which group this entry belongs to
            group = group_manager.get_entry_group(idx)
            parent_item = group_items.get(group.name)
            
            if not parent_item:
                parent_item = group_items.get(group_manager._default_group.name)
            
            # Create entry item
            item = QTreeWidgetItem(parent_item)
            
            # Description
            desc = entry.description or f"#{idx + 1}"
            item.setText(0, desc)
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "entry", "index": idx, "entry": entry})
            
            # Address
            if entry.module_name:
                addr_text = f"{entry.module_name}"
                if entry.offsets:
                    addr_text += " + " + ", ".join(f"0x{o:X}" for o in entry.offsets)
                item.setToolTip(1, f"0x{format_address(entry.address)}")
            else:
                addr_text = f"0x{format_address(entry.address)}"
            item.setText(1, addr_text)
            
            # Value (will be updated by refresh)
            item.setText(2, "-" if entry.current_value is None else format_value(entry.current_value, entry.dtype))
            
            # Type
            item.setText(3, entry.dtype.value)
            
            # Frozen checkbox
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(4, Qt.CheckState.Checked if entry.frozen else Qt.CheckState.Unchecked)
            
            # Filter visibility
            if show_frozen_only and not entry.frozen:
                item.setHidden(True)
            elif filter_text and filter_text not in desc.lower():
                item.setHidden(True)
        
        # Hide empty groups
        for group_name, group_item in group_items.items():
            has_visible_children = any(not group_item.child(i).isHidden() 
                                      for i in range(group_item.childCount()))
            if not has_visible_children and filter_text:
                group_item.setHidden(True)
    
    def refresh_values(self, results_map: dict) -> None:
        """Update displayed values from results map."""
        for i in range(self._tree.topLevelItemCount()):
            group_item = self._tree.topLevelItem(i)
            for j in range(group_item.childCount()):
                entry_item = group_item.child(j)
                data = entry_item.data(0, Qt.ItemDataRole.UserRole)
                
                if data and data.get("type") == "entry":
                    entry = data.get("entry")
                    if entry and entry.address in results_map:
                        new_value = results_map[entry.address]
                        entry.current_value = new_value
                        entry_item.setText(2, format_value(new_value, entry.dtype))
    
    def _on_context_menu(self, pos: QPoint) -> None:
        """Show context menu for tree items."""
        item = self._tree.itemAt(pos)
        if not item:
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        menu = QMenu(self)
        
        if data.get("type") == "entry":
            # Entry context menu
            entry = data.get("entry")
            
            act_edit = menu.addAction("✏️ " + (tr("menu_edit_value") if tr("menu_edit_value") != "!menu_edit_value!" else "Değeri Düzenle"))
            act_delete = menu.addAction("🗑️ " + (tr("menu_delete") if tr("menu_delete") != "!menu_delete!" else "Sil"))
            menu.addSeparator()
            
            # Move to group submenu
            move_menu = menu.addMenu("📁 " + (tr("menu_move_to_group") if tr("menu_move_to_group") != "!menu_move_to_group!" else "Gruba Taşı"))
            for group in group_manager.get_all_groups():
                act = move_menu.addAction(group.name)
                act.triggered.connect(lambda checked, g=group, e=entry: self._move_entry_to_group(e, g))
            
            chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if chosen == act_edit:
                self._edit_entry_value(entry)
            elif chosen == act_delete:
                self._delete_entry(entry)
                
        elif data.get("type") == "group":
            # Group context menu
            group = data.get("group")
            
            act_rename = menu.addAction("✏️ " + (tr("menu_rename") if tr("menu_rename") != "!menu_rename!" else "Yeniden Adlandır"))
            act_color = menu.addAction("🎨 " + (tr("menu_change_color") if tr("menu_change_color") != "!menu_change_color!" else "Renk Değiştir"))
            act_delete = menu.addAction("🗑️ " + (tr("menu_delete_group") if tr("menu_delete_group") != "!menu_delete_group!" else "Grubu Sil"))
            
            if group == group_manager._default_group:
                act_delete.setEnabled(False)  # Can't delete default group
            
            chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if chosen == act_rename:
                self._rename_group(group)
            elif chosen == act_color:
                self._change_group_color(group)
            elif chosen == act_delete:
                self._delete_group(group)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle double click on item."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "entry":
            return
        
        entry = data.get("entry")
        if column == 2:  # Value column
            self._edit_entry_value(entry)
        elif column == 0:  # Description column
            self._edit_description(item, entry)
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item changes (checkbox toggles)."""
        if column != 4:  # Not the freeze column
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "entry":
            return
        
        entry = data.get("entry")
        is_checked = item.checkState(4) == Qt.CheckState.Checked
        entry.frozen = is_checked
        self.sig_freeze_toggled.emit(entry.address, entry.dtype, is_checked)
    
    def _on_new_group(self) -> None:
        """Create a new group."""
        name, ok = QInputDialog.getText(
            self, 
            tr("dlg_new_group") if tr("dlg_new_group") != "!dlg_new_group!" else "Yeni Grup",
            tr("dlg_group_name") if tr("dlg_group_name") != "!dlg_group_name!" else "Grup adı:"
        )
        
        if ok and name.strip():
            # Check if name already exists
            if group_manager.get_group(name.strip()):
                QMessageBox.warning(self, "Hata", "Bu isimde bir grup zaten var.")
                return
            
            group_manager.create_group(name.strip())
            group_manager.save_groups()
            self._rebuild_tree()
    
    def _rename_group(self, group: WatchlistGroup) -> None:
        """Rename a group."""
        if group == group_manager._default_group:
            QMessageBox.information(self, "Bilgi", "Varsayılan grup yeniden adlandırılamaz.")
            return
        
        name, ok = QInputDialog.getText(
            self,
            tr("dlg_rename") if tr("dlg_rename") != "!dlg_rename!" else "Yeniden Adlandır",
            tr("dlg_new_name") if tr("dlg_new_name") != "!dlg_new_name!" else "Yeni ad:",
            text=group.name
        )
        
        if ok and name.strip() and name.strip() != group.name:
            # Check for duplicates
            if group_manager.get_group(name.strip()):
                QMessageBox.warning(self, "Hata", "Bu isimde bir grup zaten var.")
                return
            
            group.name = name.strip()
            group_manager.save_groups()
            self._rebuild_tree()
    
    def _change_group_color(self, group: WatchlistGroup) -> None:
        """Change group color."""
        color = QColorDialog.getColor(QColor(group.color), self)
        if color.isValid():
            group.color = color.name()
            group_manager.save_groups()
            self._rebuild_tree()
    
    def _delete_group(self, group: WatchlistGroup) -> None:
        """Delete a group."""
        if group == group_manager._default_group:
            return
        
        reply = QMessageBox.question(
            self,
            tr("dlg_confirm") if tr("dlg_confirm") != "!dlg_confirm!" else "Onay",
            f"'{group.name}' grubu silinsin mi?\nGirişler 'Genel' grubuna taşınacak.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            group_manager.remove_group(group, move_to_default=True)
            group_manager.save_groups()
            self._rebuild_tree()
    
    def _move_entry_to_group(self, entry, target_group: WatchlistGroup) -> None:
        """Move an entry to a different group."""
        # Find entry index
        for idx, e in enumerate(self._watchlist_entries):
            if e is entry:
                old_group = group_manager.get_entry_group(idx)
                group_manager.add_entry_to_group(idx, target_group)
                group_manager.save_groups()
                self.sig_entry_moved.emit(idx, old_group.name, target_group.name)
                self._rebuild_tree()
                break
    
    def _edit_entry_value(self, entry) -> None:
        """Edit an entry's value."""
        from PyQt5.QtWidgets import QInputDialog
        current = format_value(entry.current_value, entry.dtype) if entry.current_value else "0"
        
        new_val, ok = QInputDialog.getText(
            self,
            tr("dlg_edit_value") if tr("dlg_edit_value") != "!dlg_edit_value!" else "Değeri Düzenle",
            tr("dlg_new_value") if tr("dlg_new_value") != "!dlg_new_value!" else "Yeni değer:",
            text=current
        )
        
        if ok:
            self.sig_value_changed.emit(entry.address, entry.dtype, new_val)
    
    def _edit_description(self, item: QTreeWidgetItem, entry) -> None:
        """Edit entry description."""
        new_desc, ok = QInputDialog.getText(
            self,
            tr("dlg_edit_desc") if tr("dlg_edit_desc") != "!dlg_edit_desc!" else "Açıklama Düzenle",
            tr("dlg_description") if tr("dlg_description") != "!dlg_description!" else "Açıklama:",
            text=entry.description or ""
        )
        
        if ok:
            entry.description = new_desc.strip()
            item.setText(0, entry.description or f"#{self._watchlist_entries.index(entry) + 1}")
    
    def _delete_entry(self, entry) -> None:
        """Delete an entry from watchlist."""
        reply = QMessageBox.question(
            self,
            tr("dlg_confirm") if tr("dlg_confirm") != "!dlg_confirm!" else "Onay",
            "Bu giriş silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.sig_entry_deleted.emit(entry.address)
    
    def _on_filter_changed(self, text: str) -> None:
        """Handle filter text change."""
        self._rebuild_tree()
    
    def _on_frozen_filter_changed(self, state: int) -> None:
        """Handle frozen-only filter change."""
        self._rebuild_tree()
    
    def _on_expand_all(self) -> None:
        """Expand all groups."""
        self._tree.expandAll()
    
    def _on_collapse_all(self) -> None:
        """Collapse all groups."""
        self._tree.collapseAll()
    
    def _on_freeze_all(self) -> None:
        """Freeze all visible entries."""
        for i in range(self._tree.topLevelItemCount()):
            group_item = self._tree.topLevelItem(i)
            for j in range(group_item.childCount()):
                entry_item = group_item.child(j)
                if not entry_item.isHidden():
                    entry_item.setCheckState(4, Qt.CheckState.Checked)
    
    def _on_unfreeze_all(self) -> None:
        """Unfreeze all entries."""
        for i in range(self._tree.topLevelItemCount()):
            group_item = self._tree.topLevelItem(i)
            for j in range(group_item.childCount()):
                entry_item = group_item.child(j)
                entry_item.setCheckState(4, Qt.CheckState.Unchecked)
    
    def _on_delete_selected(self) -> None:
        """Delete selected entries."""
        selected = self._tree.selectedItems()
        if not selected:
            QMessageBox.information(self, "Bilgi", "Lütfen silinecek girişleri seçin.")
            return
        
        reply = QMessageBox.question(
            self,
            tr("dlg_confirm") if tr("dlg_confirm") != "!dlg_confirm!" else "Onay",
            f"{len(selected)} giriş silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for item in selected:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("type") == "entry":
                    entry = data.get("entry")
                    if entry:
                        self.sig_entry_deleted.emit(entry.address)
    
    def get_all_groups(self) -> List[WatchlistGroup]:
        """Get all groups."""
        return group_manager.get_all_groups()
    
    def save_state(self) -> None:
        """Save group expansion state."""
        for i in range(self._tree.topLevelItemCount()):
            group_item = self._tree.topLevelItem(i)
            data = group_item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "group":
                group = data.get("group")
                if group:
                    group.expanded = group_item.isExpanded()
        
        group_manager.save_groups()
