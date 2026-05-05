"""
scan_panel.py — Left-side scan control panel.
Emits signals to main_window for scan actions.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QLineEdit, QPushButton, QProgressBar,
    QGroupBox, QFormLayout, QSizePolicy, QDoubleSpinBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QShortcut, QKeySequence

from utils.patterns import DataType, ScanMode, VALUE_INPUT_MODES, FLOAT_TYPES
from utils.i18n import tr


class ScanPanel(QWidget):
    """
    Signals:
        sig_first_scan(dtype, mode, value_str, tolerance)
        sig_next_scan(mode, value_str, tolerance)
        sig_reset()
    """
    sig_first_scan = pyqtSignal(object, object, str, float)
    sig_next_scan  = pyqtSignal(object, str, float)
    sig_reset      = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._is_attached = False
        self.setFixedWidth(240)
        self._build_ui()
        self._update_ui_state()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # ── Scan Settings ──
        self._settings_grp = QGroupBox(tr("scan_settings_title"))
        self._settings_form = QFormLayout(self._settings_grp)
        self._settings_form.setSpacing(4)
        self._settings_form.setContentsMargins(6, 6, 6, 6)

        self._dtype_combo = QComboBox()
        for dt in DataType:
            self._dtype_combo.addItem(dt.value, userData=dt)
        self._dtype_combo.setCurrentIndex(2)  # INT32
        self._dtype_combo.currentIndexChanged.connect(self._on_dtype_changed)
        self._dtype_label = QLabel(tr("scan_type") + ":")
        self._settings_form.addRow(self._dtype_label, self._dtype_combo)

        self._mode_combo = QComboBox()
        for sm in ScanMode:
            self._mode_combo.addItem(sm.value, userData=sm)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._mode_label = QLabel(tr("scan_mode") + ":")
        self._settings_form.addRow(self._mode_label, self._mode_combo)

        root.addWidget(self._settings_grp)

        # ── Value Input ──
        self._val_grp = QGroupBox(tr("col_value"))
        val_lay = QVBoxLayout(self._val_grp)
        
        self._value_input = QLineEdit()
        self._value_input.setPlaceholderText(tr("placeholder_value"))
        self._value_input.setFixedHeight(26)
        self._value_input.returnPressed.connect(self._on_first_scan)
        val_lay.addWidget(self._value_input)
        
        # Float Tolerance (Hidden by default)
        self._tol_widget = QWidget()
        tol_lay = QHBoxLayout(self._tol_widget)
        tol_lay.setContentsMargins(0, 0, 0, 0)
        self._tol_label = QLabel(tr("lbl_tolerance"))
        tol_lay.addWidget(self._tol_label)
        self._tol_input = QDoubleSpinBox()
        self._tol_input.setDecimals(4)
        self._tol_input.setRange(0.0, 1000.0)
        self._tol_input.setValue(0.1)
        self._tol_input.setSingleStep(0.01)
        tol_lay.addWidget(self._tol_input)
        val_lay.addWidget(self._tol_widget)
        
        # AOB Hint (Hidden by default)
        self._aob_hint = QLabel("Format: FF 00 ? A1 x")
        self._aob_hint.setObjectName("dim_label")
        self._aob_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lay.addWidget(self._aob_hint)
        
        root.addWidget(self._val_grp)

        # ── Buttons ──
        self._first_btn = QPushButton("⚡ " + tr("btn_first_scan"))
        self._first_btn.setObjectName("primary_btn")
        self._first_btn.setFixedHeight(28)
        self._first_btn.clicked.connect(self._on_first_scan)

        self._next_btn = QPushButton("▶ " + tr("btn_next_scan"))
        self._next_btn.setFixedHeight(28)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._on_next_scan)

        self._reset_btn = QPushButton("✕ " + tr("btn_reset_scan"))
        self._reset_btn.setFixedHeight(28)
        self._reset_btn.setObjectName("danger_btn")
        self._reset_btn.setEnabled(False)
        self._reset_btn.clicked.connect(self._on_reset)

        root.addWidget(self._first_btn)
        root.addWidget(self._next_btn)
        root.addWidget(self._reset_btn)

        # ── Progress ──
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(8)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # ── Result count ──
        self._result_lbl = QLabel(tr("lbl_none"))
        self._result_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_lbl.setObjectName("result_count_lbl")
        root.addWidget(self._result_lbl)

        root.addStretch()
        
        # ── Shortcuts ──
        QShortcut(QKeySequence("F5"), self).activated.connect(self._on_first_scan)
        QShortcut(QKeySequence("F6"), self).activated.connect(self._on_next_scan)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self._on_reset)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_dtype_changed(self) -> None:
        self._update_ui_state()

    def _on_mode_changed(self) -> None:
        self._update_ui_state()

    def _check_attached(self) -> bool:
        if not self._is_attached:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, tr("settings_title") if tr("settings_title") != "!settings_title!" else "Warning", 
                                tr("msg_no_scan") if tr("msg_no_scan") != "!msg_no_scan!" else "Lütfen önce bir işleme (process) bağlanın!")
            return False
        return True

    def _on_first_scan(self) -> None:
        if not self._check_attached(): return
        if not self._first_btn.isEnabled(): return
        dtype = self._dtype_combo.currentData()
        mode  = self._mode_combo.currentData()
        val   = self._value_input.text().strip()
        tol   = self._tol_input.value()
        self.sig_first_scan.emit(dtype, mode, val, tol)

    def _on_next_scan(self) -> None:
        if not self._check_attached(): return
        if not self._next_btn.isEnabled(): return
        mode = self._mode_combo.currentData()
        val  = self._value_input.text().strip()
        tol   = self._tol_input.value()
        self.sig_next_scan.emit(mode, val, tol)

    def _on_reset(self) -> None:
        if not self._check_attached(): return
        if not self._reset_btn.isEnabled(): return
        self.sig_reset.emit()

    # ── Public interface ──────────────────────────────────────────────────────

    def set_scanning(self, scanning: bool) -> None:
        self._first_btn.setEnabled(not scanning)
        self._next_btn.setEnabled(not scanning)
        self._reset_btn.setEnabled(not scanning)
        self._progress.setVisible(scanning)
        if scanning:
            self._progress.setValue(0)

    def set_progress(self, pct: int) -> None:
        self._progress.setValue(pct)

    def set_result_count(self, count: int, scan_num: int) -> None:
        self._last_count = count
        self._last_scan_num = scan_num
        if scan_num == 0:
            self._result_lbl.setText(tr("lbl_none"))
            self._next_btn.setEnabled(False)
            self._reset_btn.setEnabled(False)
        else:
            self._result_lbl.setText(tr("scan_done").format(count))
            self._next_btn.setEnabled(True)
            self._reset_btn.setEnabled(True)

    def retranslate_ui(self) -> None:
        """Update all strings in the UI after a language change."""
        self._settings_grp.setTitle(tr("scan_settings_title"))
        self._dtype_label.setText(tr("scan_type") + ":")
        self._mode_label.setText(tr("scan_mode") + ":")
        self._val_grp.setTitle(tr("col_value"))
        self._tol_label.setText(tr("lbl_tolerance"))
        self._first_btn.setText("⚡ " + tr("btn_first_scan"))
        self._next_btn.setText("▶ " + tr("btn_next_scan"))
        self._reset_btn.setText("✕ " + tr("btn_reset_scan"))
        self._update_ui_state() # Update placeholder
        
        if hasattr(self, "_last_count"):
            self.set_result_count(self._last_count, self._last_scan_num)
        else:
            self._result_lbl.setText(tr("lbl_none"))

    def set_attached(self, attached: bool) -> None:
        self._is_attached = attached
        self._first_btn.setEnabled(attached)
        if not attached:
            self._next_btn.setEnabled(False)
            self._reset_btn.setEnabled(False)
            self._result_lbl.setText(tr("msg_no_scan"))

    # ── Private helpers ───────────────────────────────────────────────────────

    def _update_ui_state(self) -> None:
        mode  = self._mode_combo.currentData()
        dtype = self._dtype_combo.currentData()

        needs_input = mode in VALUE_INPUT_MODES
        self._value_input.setEnabled(needs_input)
        
        if mode == ScanMode.BETWEEN:
            self._value_input.setEnabled(True)
            self._value_input.setPlaceholderText("min,max (e.g., 100,200)")
        elif not needs_input:
            self._value_input.setPlaceholderText("(" + tr("lbl_none") + ")")
        else:
            self._value_input.setPlaceholderText(tr("placeholder_value"))
            
        # Float tolerance
        is_float_tol = (mode == ScanMode.FLOAT_TOLERANCE) or (dtype in FLOAT_TYPES)
        self._tol_widget.setVisible(is_float_tol)
        
        # AOB Hint
        is_aob = (mode == ScanMode.AOB) or (dtype == DataType.BYTES)
        self._aob_hint.setVisible(is_aob)
