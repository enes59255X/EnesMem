"""
hotkey_dialog.py — Hotkey configuration dialog.
"""
from typing import Optional, Callable

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QLineEdit, QLabel, QHeaderView, QMessageBox,
    QCheckBox, QKeySequenceEdit, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence

from core.hotkey_manager import hotkey_manager, HotkeyAction, HotkeyConfig
from utils.i18n import tr
from utils.logger import log


class HotkeyDialog(QDialog):
    """Dialog for configuring global hotkeys."""
    
    sig_hotkeys_changed = pyqtSignal()
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("hotkey_title") if tr("hotkey_title") != "!hotkey_title!" else "⌨️ Global Kısayollar")
        self.setMinimumSize(650, 450)
        self.resize(700, 500)
        
        self._recording_combo = None  # Currently recording hotkey
        self._build_ui()
        self._load_hotkeys()
    
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Info label
        info = QLabel(tr("hotkey_info") if tr("hotkey_info") != "!hotkey_info!" 
                     else "Global kısayollar oyun içindeyken bile çalışır. Ctrl/Alt/Shift + Fonksiyon tuşları önerilir.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(info)
        
        # Hotkey table
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            tr("col_hotkey") if tr("col_hotkey") != "!col_hotkey!" else "Kısayol",
            tr("col_action") if tr("col_action") != "!col_action!" else "İşlem",
            tr("col_desc") if tr("col_desc") != "!col_desc!" else "Açıklama",
            tr("col_enabled") if tr("col_enabled") != "!col_enabled!" else "Aktif"
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)
        
        # Add new hotkey section
        add_group = QGroupBox(tr("hotkey_add_new") if tr("hotkey_add_new") != "!hotkey_add_new!" else "Yeni Kısayol Ekle")
        add_layout = QFormLayout(add_group)
        
        # Action combo
        self._action_combo = QComboBox()
        self._action_combo.setMinimumWidth(200)
        self._populate_actions()
        add_layout.addRow(tr("lbl_action") if tr("lbl_action") != "!lbl_action!" else "İşlem:", self._action_combo)
        
        # Key combination
        key_layout = QHBoxLayout()
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText(tr("hotkey_placeholder") if tr("hotkey_placeholder") != "!hotkey_placeholder!" else "<ctrl>+f1")
        self._key_input.setReadOnly(True)
        key_layout.addWidget(self._key_input, stretch=1)
        
        self._record_btn = QPushButton(tr("btn_record") if tr("btn_record") != "!btn_record!" else "🎙️ Kaydet")
        self._record_btn.setCheckable(True)
        self._record_btn.toggled.connect(self._on_record_toggle)
        key_layout.addWidget(self._record_btn)
        
        add_layout.addRow(tr("lbl_keys") if tr("lbl_keys") != "!lbl_keys!" else "Tuşlar:", key_layout)
        
        # Description
        self._desc_input = QLineEdit()
        self._desc_input.setPlaceholderText(tr("desc_placeholder") if tr("desc_placeholder") != "!desc_placeholder!" else "İsteğe bağlı açıklama...")
        add_layout.addRow(tr("lbl_description") if tr("lbl_description") != "!lbl_description!" else "Açıklama:", self._desc_input)
        
        layout.addWidget(add_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self._add_btn = QPushButton(tr("btn_add_hotkey") if tr("btn_add_hotkey") != "!btn_add_hotkey!" else "➕ Ekle")
        self._add_btn.clicked.connect(self._on_add)
        self._add_btn.setEnabled(False)  # Enable when key recorded
        btn_layout.addWidget(self._add_btn)
        
        btn_layout.addStretch()
        
        self._remove_btn = QPushButton(tr("btn_remove") if tr("btn_remove") != "!btn_remove!" else "🗑️ Seçiliyi Sil")
        self._remove_btn.clicked.connect(self._on_remove)
        btn_layout.addWidget(self._remove_btn)
        
        self._defaults_btn = QPushButton(tr("btn_defaults") if tr("btn_defaults") != "!btn_defaults!" else "🔄 Varsayılanlar")
        self._defaults_btn.clicked.connect(self._on_restore_defaults)
        btn_layout.addWidget(self._defaults_btn)
        
        layout.addLayout(btn_layout)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        self._save_btn = QPushButton(tr("btn_save") if tr("btn_save") != "!btn_save!" else "💾 Kaydet")
        self._save_btn.setObjectName("primary_btn")
        self._save_btn.clicked.connect(self._on_save)
        bottom_layout.addWidget(self._save_btn)
        
        self._cancel_btn = QPushButton(tr("btn_cancel") if tr("btn_cancel") != "!btn_cancel!" else "❌ İptal")
        self._cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(bottom_layout)
    
    def _populate_actions(self) -> None:
        """Populate action combo box with descriptions."""
        action_descriptions = {
            HotkeyAction.TOGGLE_FREEZE_ALL: "Tümünü Dondur/Aç",
            HotkeyAction.UNFREEZE_ALL: "Tüm Dondurmaları Kaldır",
            HotkeyAction.INCREASE_VALUE: "Değeri Arttır",
            HotkeyAction.DECREASE_VALUE: "Değeri Azalt",
            HotkeyAction.TOGGLE_WINDOW: "Pencereyi Göster/Gizle",
            HotkeyAction.RUN_SCRIPT: "Script Çalıştır",
            HotkeyAction.ATTACH_PROCESS: "İşleme Bağlan",
            HotkeyAction.DETACH_PROCESS: "Bağlantıyı Kes",
            HotkeyAction.NEXT_SCAN: "Sonraki Tarama",
            HotkeyAction.RESET_SCAN: "Taramayı Sıfırla",
        }
        
        for action, desc in action_descriptions.items():
            self._action_combo.addItem(f"{desc}", action)
    
    def _load_hotkeys(self) -> None:
        """Load existing hotkeys into table."""
        self._table.setRowCount(0)
        
        hotkeys = hotkey_manager.get_all_hotkeys()
        
        for row, hk in enumerate(hotkeys):
            self._table.insertRow(row)
            
            # Key combination
            key_display = self._format_key_display(hk.key_combination)
            self._table.setItem(row, 0, QTableWidgetItem(key_display))
            
            # Action
            action_text = self._get_action_display(hk.action)
            self._table.setItem(row, 1, QTableWidgetItem(action_text))
            
            # Description
            self._table.setItem(row, 2, QTableWidgetItem(hk.description))
            
            # Enabled checkbox
            chk = QCheckBox()
            chk.setChecked(hk.enabled)
            chk.stateChanged.connect(lambda state, r=row: self._on_enabled_changed(r, state))
            self._table.setCellWidget(row, 3, chk)
            
            # Store key combo in item data for reference
            self._table.item(row, 0).setData(Qt.ItemDataRole.UserRole, hk.key_combination)
    
    def _format_key_display(self, key_combo: str) -> str:
        """Format key combination for display."""
        # Convert <ctrl>+f1 to Ctrl+F1
        display = key_combo.replace("<", "").replace(">", "").replace("ctrl", "Ctrl").replace("alt", "Alt").replace("shift", "Shift")
        display = display.replace("cmd", "Win").replace("+", " + ")
        return display
    
    def _get_action_display(self, action: HotkeyAction) -> str:
        """Get display text for action."""
        action_map = {
            HotkeyAction.TOGGLE_FREEZE_ALL: "Tümünü Dondur/Aç",
            HotkeyAction.UNFREEZE_ALL: "Tüm Dondurmaları Kaldır",
            HotkeyAction.INCREASE_VALUE: "Değeri Arttır",
            HotkeyAction.DECREASE_VALUE: "Değeri Azalt",
            HotkeyAction.TOGGLE_WINDOW: "Pencereyi Göster/Gizle",
            HotkeyAction.RUN_SCRIPT: "Script Çalıştır",
            HotkeyAction.ATTACH_PROCESS: "İşleme Bağlan",
            HotkeyAction.DETACH_PROCESS: "Bağlantıyı Kes",
            HotkeyAction.NEXT_SCAN: "Sonraki Tarama",
            HotkeyAction.RESET_SCAN: "Taramayı Sıfırla",
        }
        return action_map.get(action, action.name)
    
    def _on_record_toggle(self, checked: bool) -> None:
        """Start or stop recording a hotkey."""
        if checked:
            self._record_btn.setText(tr("recording") if tr("recording") != "!recording!" else "🔴 Kaydediyor...")
            self._key_input.setPlaceholderText(tr("press_keys") if tr("press_keys") != "!press_keys!" else "Kısayol tuşlarına basın...")
            self._key_input.clear()
            self._recording_combo = None
        else:
            self._record_btn.setText(tr("btn_record") if tr("btn_record") != "!btn_record!" else "🎙️ Kaydet")
            self._key_input.setPlaceholderText(tr("hotkey_placeholder") if tr("hotkey_placeholder") != "!hotkey_placeholder!" else "<ctrl>+f1")
    
    def keyPressEvent(self, event) -> None:
        """Capture key combinations when recording."""
        if self._record_btn.isChecked():
            # Build key combination string
            modifiers = []
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                modifiers.append("<ctrl>")
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                modifiers.append("<alt>")
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                modifiers.append("<shift>")
            
            key = event.key()
            if key not in [Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta]:
                # Get key name
                key_name = self._qt_key_to_name(key)
                if key_name:
                    combo = "+".join(modifiers + [key_name])
                    self._key_input.setText(combo)
                    self._record_btn.setChecked(False)
                    self._add_btn.setEnabled(True)
        
        super().keyPressEvent(event)
    
    def _qt_key_to_name(self, key: Qt.Key) -> Optional[str]:
        """Convert Qt key to pynput format."""
        # Function keys
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
            return f"f{key - Qt.Key.Key_F1 + 1}"
        
        # Special keys
        key_map = {
            Qt.Key.Key_Space: "space",
            Qt.Key.Key_Return: "return",
            Qt.Key.Key_Enter: "enter",
            Qt.Key.Key_Tab: "tab",
            Qt.Key.Key_Escape: "esc",
            Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Backspace: "backspace",
            Qt.Key.Key_Insert: "insert",
            Qt.Key.Key_Home: "home",
            Qt.Key.Key_End: "end",
            Qt.Key.Key_PageUp: "pageup",
            Qt.Key.Key_PageDown: "pagedown",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_Up: "up",
            Qt.Key.Key.Down: "down",
        }
        
        if key in key_map:
            return key_map[key]
        
        # Letter keys
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(ord('a') + (key - Qt.Key.Key_A))
        
        # Number keys
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            return str(key - Qt.Key.Key_0)
        
        return None
    
    def _on_add(self) -> None:
        """Add new hotkey."""
        key_combo = self._key_input.text().strip()
        if not key_combo:
            QMessageBox.warning(self, "Hata", "Lütfen bir kısayol kaydedin.")
            return
        
        action = self._action_combo.currentData()
        description = self._desc_input.text().strip()
        
        # Check for conflicts
        existing = hotkey_manager.get_hotkey(key_combo)
        if existing:
            reply = QMessageBox.question(
                self, "Kısayol Çakışması",
                f"'{key_combo}' zaten mevcut. Üzerine yazılsın mı?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Add to manager
        if hotkey_manager.add_hotkey(key_combo, action, description):
            self._load_hotkeys()
            self._key_input.clear()
            self._desc_input.clear()
            self._add_btn.setEnabled(False)
            log.info("HotkeyDialog: Added %s", key_combo)
        else:
            QMessageBox.warning(self, "Hata", "Kısayol eklenemedi. Formatı kontrol edin.")
    
    def _on_remove(self) -> None:
        """Remove selected hotkey."""
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Bilgi", "Lütfen silinecek kısayolu seçin.")
            return
        
        key_combo = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self, "Onay",
            f"'{key_combo}' kısayolu silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if hotkey_manager.remove_hotkey(key_combo):
                self._load_hotkeys()
                log.info("HotkeyDialog: Removed %s", key_combo)
    
    def _on_enabled_changed(self, row: int, state: int) -> None:
        """Handle checkbox state change."""
        key_combo = self._table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        enabled = state == Qt.CheckState.Checked.value
        hotkey_manager.set_enabled(key_combo, enabled)
    
    def _on_restore_defaults(self) -> None:
        """Restore default hotkeys."""
        reply = QMessageBox.question(
            self, "Varsayılanlar",
            "Tüm kısayollar varsayılanlara sıfırlansın mı?\nMevcut ayarlarınız kaybolacak.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            hotkey_manager._hotkeys.clear()
            hotkey_manager._load_defaults()
            self._load_hotkeys()
            log.info("HotkeyDialog: Restored defaults")
    
    def _on_save(self) -> None:
        """Save configuration and close."""
        if hotkey_manager.save_config():
            self.sig_hotkeys_changed.emit()
            self.accept()
        else:
            QMessageBox.warning(self, "Hata", "Ayarlar kaydedilemedi.")


def show_hotkey_dialog(parent=None) -> bool:
    """Show hotkey configuration dialog."""
    dialog = HotkeyDialog(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted
