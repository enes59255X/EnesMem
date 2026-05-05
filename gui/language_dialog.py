"""
language_dialog.py — Enhanced language selection dialog.
Provides language switching functionality with improved UI.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QListWidget, QListWidgetItem, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
from utils.i18n_enhanced import get_i18n_manager
import os


class LanguageDialog(QDialog):
    """Enhanced language selection dialog."""
    language_changed = pyqtSignal(str, str)  # lang_code, lang_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dil Seçimi / Language Selection")
        self.setFixedSize(400, 300)
        self.setModal(True)
        
        self._setup_ui()
        self._populate_languages()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("🌍 Dil Seçimi / Language Selection")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(14)
        title.setFont(title_font)
        layout.addWidget(title)

        # Language list
        self._lang_list = QListWidget()
        self._lang_list.setFont(QFont("Arial", 10))
        layout.addWidget(self._lang_list)

        # Buttons
        button_layout = QHBoxLayout()
        
        self._apply_btn = QPushButton("✓ Uygula / Apply")
        self._apply_btn.setObjectName("primary_btn")
        self._apply_btn.setFixedHeight(35)
        
        self._cancel_btn = QPushButton("✕ İptal / Cancel")
        self._cancel_btn.setFixedHeight(35)
        
        button_layout.addWidget(self._apply_btn)
        button_layout.addWidget(self._cancel_btn)
        layout.addLayout(button_layout)

        # Connect signals
        self._apply_btn.clicked.connect(self._apply_language)
        self._cancel_btn.clicked.connect(self.reject)
        self._lang_list.itemDoubleClicked.connect(self.accept)

    def _populate_languages(self):
        """Populate the language list."""
        i18n_manager = get_i18n_manager()
        available_languages = i18n_manager.get_available_languages()
        current_lang = i18n_manager.get_current_language()

        for lang_code, lang_info in available_languages.items():
            item = QListWidgetItem()
            
            # Display name with current indicator
            display_name = lang_info['name']
            if lang_code == current_lang:
                display_name = f"✓ {display_name}"
            
            item.setText(display_name)
            item.setData(Qt.ItemDataRole.UserRole, lang_code)
            
            # Set as current item
            if lang_code == current_lang:
                self._lang_list.setCurrentItem(item)
            
            self._lang_list.addItem(item)

    def _apply_language(self):
        """Apply the selected language."""
        current_item = self._lang_list.currentItem()
        if current_item:
            lang_code = current_item.data(Qt.ItemDataRole.UserRole)
            lang_name = current_item.text().replace("✓ ", "")
            
            if get_i18n_manager().switch_language(lang_code):
                self.language_changed.emit(lang_code, lang_name)
                self.accept()

    def get_selected_language(self) -> str:
        """Get the selected language code."""
        current_item = self._lang_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None
