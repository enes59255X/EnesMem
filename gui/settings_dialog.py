from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QFormLayout, QCheckBox,
    QSpinBox, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt
from utils.settings import SettingsManager
from utils.i18n import tr, i18n

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = SettingsManager()
        self._init_ui()
        self._apply_styles()

    def _init_ui(self):
        self.setWindowTitle(tr("settings_title"))
        self.setMinimumSize(500, 380)
        self.setObjectName("SettingsDialog")
        # Remove standard window borders for a custom premium look if desired,
        # but let's stick to standard dialog frame for now for OS consistency,
        # just with a better layout and internal styling.
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # Title Label
        title_lbl = QLabel("⚙️ " + tr("settings_title"))
        title_lbl.setObjectName("SettingsTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_lbl)

        # ── General Settings Group ──
        gen_grp = QFrame()
        gen_grp.setObjectName("PremiumCard")
        gen_layout = QVBoxLayout(gen_grp)
        gen_layout.setContentsMargins(20, 20, 20, 20)
        
        gen_lbl = QLabel(tr("general_settings"))
        gen_lbl.setObjectName("GroupTitle")
        gen_layout.addWidget(gen_lbl)

        gen_form = QFormLayout()
        gen_form.setSpacing(15)

        # Language selection
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("English 🇺🇸", "en")
        self.lang_combo.addItem("Türkçe 🇹🇷", "tr")
        self.lang_combo.setCurrentIndex(self.lang_combo.findData(self.settings.get_language()))
        gen_form.addRow(tr("settings_lang") + ":", self.lang_combo)

        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("🌙 " + tr("theme_dark"), "dark")
        self.theme_combo.addItem("☀️ " + tr("theme_light"), "light")
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(self.settings.theme))
        gen_form.addRow(tr("theme_label") + ":", self.theme_combo)

        gen_layout.addLayout(gen_form)
        main_layout.addWidget(gen_grp)

        # ── Performance & Safety Group ──
        perf_grp = QFrame()
        perf_grp.setObjectName("PremiumCard")
        perf_layout = QVBoxLayout(perf_grp)
        perf_layout.setContentsMargins(20, 20, 20, 20)

        perf_lbl = QLabel(tr("performance_settings"))
        perf_lbl.setObjectName("GroupTitle")
        perf_layout.addWidget(perf_lbl)

        perf_form = QFormLayout()
        perf_form.setSpacing(15)

        # Safe Scan
        self.safe_scan_check = QCheckBox(tr("safe_scan_desc"))
        self.safe_scan_check.setChecked(self.settings.safe_scan)
        self.safe_scan_check.setToolTip("Adds small delays during memory scanning to prevent high CPU usage.")
        perf_form.addRow(tr("safe_scan_label") + ":", self.safe_scan_check)

        # Refresh Interval
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(50, 5000)
        self.refresh_spin.setSingleStep(50)
        self.refresh_spin.setSuffix(" ms")
        self.refresh_spin.setValue(self.settings.refresh_interval)
        perf_form.addRow(tr("refresh_interval_label") + ":", self.refresh_spin)

        perf_layout.addLayout(perf_form)
        main_layout.addWidget(perf_grp)

        main_layout.addStretch()

        # ── Footer Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.save_btn = QPushButton(tr("settings_save"))
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setFixedWidth(140)
        
        self.cancel_btn = QPushButton(tr("settings_cancel"))
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setFixedWidth(120)
        
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        
        main_layout.addLayout(btn_layout)

    def _apply_styles(self):
        is_dark = self.settings.theme == 'dark'
        bg = "#1e1e2e" if is_dark else "#f4f5f7"
        card_bg = "#27293d" if is_dark else "#ffffff"
        text = "#cdd6f4" if is_dark else "#4a4a55"
        title_text = "#f38ba8" if is_dark else "#d20f39"
        border = "#313244" if is_dark else "#e5e7eb"
        btn_hover = "#45475a" if is_dark else "#f3f4f6"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {text};
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }}
            QLabel#SettingsTitle {{
                font-size: 22px;
                font-weight: 700;
                color: {title_text};
                margin-bottom: 10px;
            }}
            QFrame#PremiumCard {{
                background-color: {card_bg};
                border-radius: 12px;
                border: 1px solid {border};
            }}
            QLabel#GroupTitle {{
                font-size: 14px;
                font-weight: 600;
                color: {title_text};
                margin-bottom: 8px;
            }}
            QComboBox, QSpinBox {{
                padding: 6px 10px;
                border: 1px solid {border};
                border-radius: 6px;
                background-color: {bg};
                color: {text};
                font-size: 13px;
                min-width: 150px;
            }}
            QComboBox:focus, QSpinBox:focus {{
                border: 1px solid {title_text};
            }}
            QPushButton#PrimaryButton {{
                background-color: {title_text};
                color: white;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton#PrimaryButton:hover {{
                background-color: #ff5a75;
            }}
            QPushButton#SecondaryButton {{
                background-color: transparent;
                color: {text};
                border: 1px solid {border};
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton#SecondaryButton:hover {{
                background-color: {btn_hover};
            }}
            QCheckBox {{
                font-size: 13px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {border};
                background-color: {bg};
            }}
            QCheckBox::indicator:checked {{
                background-color: {title_text};
                border-color: {title_text};
            }}
        """)

    def save_settings(self):
        self.settings.set_language(self.lang_combo.currentData())
        self.settings.theme = self.theme_combo.currentData()
        self.settings.safe_scan = self.safe_scan_check.isChecked()
        self.settings.refresh_interval = self.refresh_spin.value()

    def retranslate_ui(self):
        """Not strictly needed for the dialog itself if recreated, but good for consistency."""
        self.setWindowTitle(tr("settings_title"))
        # Groups would need titles updated if we weren't just closing and reopening.
        # But for live updates, we recreate or call this.

    @staticmethod
    def show_settings(parent=None):
        dialog = SettingsDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.save_settings()
            new_lang = dialog.settings.get_language()
            i18n.load_language(new_lang)
            return True
        return False
