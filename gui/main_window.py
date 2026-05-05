"""
main_window.py — Root QMainWindow for EnesMem.
Orchestrates: process attachment, scan workers, live refresh timer,
freeze/unfreeze, pointer resolution, and UI theming.
"""
import sys
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStatusBar, QPushButton, QToolBar,
    QMessageBox, QInputDialog, QDockWidget, QSplitter,
    QApplication, QFileDialog,
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QObject, pyqtSlot,
)
from PyQt5.QtGui import QIcon, QFont, QKeySequence
from PyQt5.QtWidgets import QAction

from core.process_manager import ProcessManager
from core.memory_io import MemoryIO
from core.scanner import Scanner
from core.freezer import Freezer
from core.pointer_scanner import PointerScanner
from core.hotkey_manager import hotkey_manager, HotkeyAction
from core.value_graph import graph_manager

from gui.process_selector import ProcessSelectorDialog
from gui.scan_panel import ScanPanel
from gui.results_table import ResultsTable
from gui.pointer_panel import PointerPanel
from gui.memory_viewer import MemoryViewer
from gui.hotkey_dialog import show_hotkey_dialog
from gui.aob_dialog import show_aob_dialog
from gui.graph_dialog import show_graph_dialog
from gui.memory_map_dialog import show_memory_map_dialog
from core.ct_manager import import_ct_file, export_ct_file

from utils.converters import parse_user_input, format_address, format_value, value_to_bytes
from utils.logger import log
from utils.patterns import DataType, ScanMode, LIVE_REFRESH_INTERVAL_MS
from utils.i18n import tr
from utils.settings import SettingsManager
from gui.settings_dialog import SettingsDialog


# ── Scan Worker (QThread) ──────────────────────────────────────────────────────

class ScanWorker(QObject):
    """Runs first/next scan off the main thread."""
    sig_progress = pyqtSignal(int)
    sig_done     = pyqtSignal(int)    # result count
    sig_error    = pyqtSignal(str)

    def __init__(
        self,
        scanner:   Scanner,
        is_first:  bool,
        dtype:     DataType,
        mode:      ScanMode,
        value,
        tolerance: float = 0.0,
    ) -> None:
        super().__init__()
        self._scanner   = scanner
        self._is_first  = is_first
        self._dtype     = dtype
        self._mode      = mode
        self._value     = value
        self._tolerance = tolerance
        self._last_pct  = -1
        self._last_emit_time = 0

    def _on_progress(self, pct: int) -> None:
        import time
        now = time.time()
        # Emit if percentage changed AND at least 33ms passed (approx 30 FPS)
        # Always emit 0 and 100 for completeness
        if pct == 0 or pct == 100 or (pct != self._last_pct and now - self._last_emit_time > 0.033):
            self.sig_progress.emit(pct)
            self._last_pct = pct
            self._last_emit_time = now

    @pyqtSlot()
    def run(self) -> None:
        try:
            if self._is_first:
                count = self._scanner.first_scan(
                    self._dtype, self._mode, self._value,
                    tolerance=self._tolerance,
                    progress_cb=self._on_progress,
                )
            else:
                count = self._scanner.next_scan(
                    self._mode, self._value,
                    tolerance=self._tolerance,
                    progress_cb=self._on_progress,
                )
            self.sig_done.emit(count)
        except Exception as exc:
            log.exception("ScanWorker error")
            self.sig_error.emit(str(exc))


class PointerWorker(QObject):
    """Runs recursive pointer scanner or filter off the main thread."""
    sig_progress = pyqtSignal(int)
    sig_done     = pyqtSignal(list)   # list[PointerChain]
    sig_error    = pyqtSignal(str)

    def __init__(self, scanner: PointerScanner, target=None, max_depth: int = 3, max_offset: int = 2048, mode="SCAN", dtype=DataType.INT32, chains=None) -> None:
        super().__init__()
        self._scanner = scanner
        self._target  = target
        self._max_depth = max_depth
        self._max_offset = max_offset
        self._mode = mode
        self._dtype = dtype
        self._chains = chains or []

    def _on_progress(self, pct: int) -> None:
        self.sig_progress.emit(pct)

    @pyqtSlot()
    def run(self) -> None:
        try:
            # Validate scanner and memory
            if not self._scanner or not self._scanner._mem:
                self.sig_error.emit("Scanner not initialized")
                return
            
            # Validate handle
            if not getattr(self._scanner._mem, '_handle', None):
                self.sig_error.emit("Process detached")
                return
            
            if self._mode == "SCAN":
                log.info("PointerWorker: Starting scan for 0x%X (depth=%d, offset=%d)", self._target, self._max_depth, self._max_offset)
                results = self._scanner.auto_scan(
                    self._target, 
                    max_depth=self._max_depth, 
                    max_offset=self._max_offset,
                    progress_cb=self._on_progress
                )
            else:
                log.info("PointerWorker: Starting filter for %d chains", len(self._chains))
                results = self._scanner.filter_chains(
                    self._chains,
                    self._target,
                    self._dtype,
                    progress_cb=self._on_progress
                )
            
            # Resolve values for the UI - with individual error handling per chain
            from utils.converters import format_value
            safe_results = []
            for chain in results:
                try:
                    # Validate handle before each read
                    if not getattr(self._scanner._mem, '_handle', None):
                        chain.value = "???"
                        safe_results.append(chain)
                        continue
                    
                    val = self._scanner._mem.read_value(chain.final_addr, self._dtype)
                    chain.value = format_value(val, self._dtype) if val is not None else "???"
                    safe_results.append(chain)
                except Exception as e:
                    log.debug("Error resolving chain value: %s", e)
                    chain.value = "???"
                    safe_results.append(chain)
                
            self.sig_done.emit(safe_results)
        except Exception as exc:
            log.exception("PointerWorker error")
            self.sig_error.emit(str(exc))



# ── Main Window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    TITLE = "EnesMem — Python Memory Scanner"

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("app_name"))
        self.setMinimumSize(1100, 700)
        self.resize(1280, 800)

        # ── Core objects ──
        self._pm      = ProcessManager()
        self._mem:    Optional[MemoryIO]    = None
        self._scanner: Optional[Scanner]   = None
        self._freezer: Optional[Freezer]   = None
        self._ptr_sc:  Optional[PointerScanner] = None

        # Scan threads
        self._scan_thread:  Optional[QThread]     = None
        self._scan_worker:  Optional[ScanWorker]  = None
        self._ptr_thread:   Optional[QThread]     = None
        self._ptr_worker:   Optional[PointerWorker] = None

        # ── Build UI ──
        self._apply_stylesheet()
        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_status_bar()

        # ── Live refresh timer ──
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._live_refresh)
        # Does not start until attached

        # ── Global Hotkeys ──
        self._setup_hotkeys()

        log.info("MainWindow initialized")
    
    def _setup_hotkeys(self) -> None:
        """Setup global hotkey manager and connections."""
        try:
            # Load saved hotkey configuration
            hotkey_manager.load_config()
            
            # Connect hotkey action handler
            hotkey_manager.sig_action_triggered.connect(self._on_hotkey_action)
            hotkey_manager.sig_error.connect(self._on_hotkey_error)
            
            # Start global hotkey listener
            if not hotkey_manager.start():
                log.warning("MainWindow: Failed to start global hotkeys")
            else:
                log.info("MainWindow: Global hotkeys active (%d hotkeys)", 
                        len([hk for hk in hotkey_manager.get_all_hotkeys() if hk.enabled]))
        except Exception as e:
            log.error("MainWindow: Hotkey setup failed: %s", e)
    
    def _on_hotkey_action(self, action: HotkeyAction, params: dict) -> None:
        """Handle global hotkey actions."""
        try:
            log.debug("Hotkey action: %s", action.name)
            
            if action == HotkeyAction.TOGGLE_FREEZE_ALL:
                self._toggle_freeze_all()
            elif action == HotkeyAction.UNFREEZE_ALL:
                self._unfreeze_all()
            elif action == HotkeyAction.TOGGLE_WINDOW:
                self._toggle_window_visibility()
            elif action == HotkeyAction.NEXT_SCAN:
                self._on_next_scan()
            elif action == HotkeyAction.RESET_SCAN:
                self._on_reset()
            elif action == HotkeyAction.ATTACH_PROCESS:
                self._open_process_selector()
            elif action == HotkeyAction.DETACH_PROCESS:
                self._detach()
            else:
                log.debug("Unhandled hotkey action: %s", action.name)
                
        except Exception as e:
            log.error("Hotkey action error: %s", e)
    
    def _on_hotkey_error(self, msg: str) -> None:
        """Handle hotkey errors."""
        log.error("Hotkey error: %s", msg)
        self._status_lbl.setText(f"Kısayol hatası: {msg}")
    
    def _toggle_freeze_all(self) -> None:
        """Toggle freeze state for all watchlist entries."""
        if not self._freezer:
            return
        try:
            # Get all frozen addresses
            frozen_addrs = set(self._freezer._frozen.keys())
            watchlist_addrs = {entry.address for entry in self._results._watchlist}
            
            if frozen_addrs:
                # Some are frozen, unfreeze all
                self._unfreeze_all()
                self._status_lbl.setText("Tüm dondurmalar kaldırıldı (kısayol)")
            else:
                # None frozen, freeze all
                for entry in self._results._watchlist:
                    if entry.current_value is not None:
                        self._freezer.freeze(entry.address, entry.current_value, entry.dtype)
                self._status_lbl.setText(f"Tüm değerler donduruldu ({len(self._results._watchlist)} adet)")
        except Exception as e:
            log.error("Toggle freeze all error: %s", e)
    
    def _unfreeze_all(self) -> None:
        """Unfreeze all watchlist entries."""
        if not self._freezer:
            return
        try:
            for entry in self._results._watchlist:
                self._freezer.unfreeze(entry.address)
            self._status_lbl.setText("Tüm dondurmalar kaldırıldı")
        except Exception as e:
            log.error("Unfreeze all error: %s", e)
    
    def _toggle_window_visibility(self) -> None:
        """Toggle main window visibility."""
        if self.isVisible() and not self.isMinimized():
            self.hide()
            self._status_lbl.setText("Pencere gizlendi (Ctrl+F3 ile göster)")
        else:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def _open_hotkey_dialog(self) -> None:
        """Open global hotkey configuration dialog."""
        from gui.hotkey_dialog import HotkeyDialog
        dlg = HotkeyDialog(self)
        if dlg.exec():
            pass  # Settings are automatically saved

    def _open_language_dialog(self) -> None:
        """Open language selection dialog."""
        from gui.language_dialog import LanguageDialog
        dlg = LanguageDialog(self)
        dlg.language_changed.connect(self._on_language_changed)
        if dlg.exec():
            pass

    def _on_language_changed(self, lang_code: str, lang_name: str) -> None:
        """Handle language change."""
        from utils.i18n_enhanced import get_i18n_manager
        i18n_manager = get_i18n_manager()
        
        if i18n_manager.switch_language(lang_code):
            self.retranslate_ui()
            self._status_lbl.setText(f"Dil değiştirildi: {lang_name}")
            log.info("Language changed to %s (%s)", lang_code, lang_name)
            hotkey_manager.start()
            self._status_lbl.setText("Kısayol ayarları güncellendi")

    # ── Stylesheet ────────────────────────────────────────────────────────────

    def _apply_stylesheet(self) -> None:
        from utils.settings import settings
        is_dark = settings.theme == "dark"
        
        # Color Palettes (Premium Modern Palette)
        if is_dark:
            bg        = "#0d1117"  # GitHub Dark
            surface   = "#161b22"
            border    = "#30363d"
            text      = "#c9d1d9"
            text_dim  = "#8b949e"
            btn       = "#21262d"
            btn_hover = "#2d333b"
            input_bg  = "#0d1117"
            header_bg = "#161b22"
            sel_bg    = "#1f3349"
        else:
            bg        = "#f6f8fa"  # GitHub Light
            surface   = "#ffffff"
            border    = "#d0d7de"
            text      = "#24292f"
            text_dim  = "#57606a"
            btn       = "#f3f4f6"
            btn_hover = "#ebecf0"
            input_bg  = "#ffffff"
            header_bg = "#f6f8fa"
            sel_bg    = "#e2e9f0"

        accent       = "#e94560" # EnesMem Red
        accent_hover = "#ff5a75"
        success      = "#3fb950"

        self.setStyleSheet(f"""
        /* ─── Global ─── */
        QMainWindow, QDialog, QWidget {{
            background-color: {bg};
            color: {text};
            font-family: 'Segoe UI', 'Inter', sans-serif;
            font-size: 13px;
        }}

        /* ─── Menu ─── */
        QMenuBar {{
            background-color: {surface};
            color: {text};
            border-bottom: 1px solid {border};
            padding: 2px;
        }}
        QMenuBar::item:selected {{ background-color: {btn}; border-radius: 4px; }}
        QMenu {{
            background-color: {surface};
            color: {text};
            border: 1px solid {border};
            border-radius: 6px;
        }}
        QMenu::item:selected {{ background-color: {btn}; }}

        /* ─── Toolbar ─── */
        QToolBar {{
            background-color: {surface};
            border-bottom: 1px solid {border};
            spacing: 4px;
            padding: 4px 8px;
        }}

        /* ─── Buttons ─── */
        QPushButton {{
            background-color: {btn};
            color: {text};
            border: 1px solid {border};
            border-radius: 5px;
            padding: 5px 12px;
        }}
        QPushButton:hover  {{ background-color: {btn_hover}; border-color: {accent}; }}
        QPushButton:pressed{{ background-color: {surface}; }}
        QPushButton:disabled {{ color: {text_dim}; background-color: {surface}; }}

        QPushButton#primary_btn {{
            background-color: {accent};
            color: #ffffff;
            border: none;
            font-weight: 600;
        }}
        QPushButton#primary_btn:hover  {{ background-color: {accent_hover}; }}
        QPushButton#primary_btn:pressed{{ background-color: #c73350; }}

        QPushButton#danger_btn {{
            background-color: {"#2d1b1b" if is_dark else "#fff0f0"};
            color: {accent};
            border: 1px solid {accent};
        }}
        QPushButton#danger_btn:hover {{ background-color: {"#3a1f1f" if is_dark else "#ffe0e0"}; }}

        QPushButton#small_btn {{
            font-size: 11px;
            padding: 2px 8px;
        }}

        /* ─── Inputs ─── */
        QLineEdit, QComboBox, QSpinBox, QAbstractItemView {{
            background-color: {input_bg};
            color: {text};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 4px 8px;
            selection-background-color: {sel_bg};
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border-color: {accent};
        }}
        QComboBox::drop-down {{ border: none; }}

        /* ─── GroupBox ─── */
        QGroupBox {{
            color: {text_dim};
            border: 1px solid {border};
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }}

        /* ─── Tables ─── */
        QTableWidget, QTreeView {{
            background-color: {bg};
            alternate-background-color: {surface};
            gridline-color: {border};
            border: 1px solid {border};
            border-radius: 4px;
            selection-background-color: {sel_bg};
            selection-color: {text};
        }}
        QTableWidget::item {{ padding: 2px 6px; }}
        QHeaderView::section {{
            background-color: {header_bg};
            color: {text_dim};
            border: none;
            border-bottom: 1px solid {border};
            padding: 6px;
            font-weight: 600;
            font-size: 11px;
        }}
        QHeaderView::section:hover {{ background-color: {btn}; }}

        /* ─── Progress bar ─── */
        QProgressBar {{
            background-color: {btn};
            border: none;
            border-radius: 5px;
            text-align: center;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {accent}, stop:1 #ff8c42);
            border-radius: 5px;
        }}

        /* ─── Status bar ─── */
        QStatusBar {{
            background-color: {surface};
            color: {text_dim};
            border-top: 1px solid {border};
            font-size: 11px;
        }}

        /* ─── Labels ─── */
        QLabel#section_label {{
            color: {"#58a6ff" if is_dark else "#0969da"};
            font-weight: 600;
            font-size: 12px;
        }}
        QLabel#dim_label    {{ color: {text_dim}; font-size: 11px; }}
        QLabel#result_count_lbl {{
            color: {success};
            font-weight: 700;
            font-size: 14px;
        }}
        QLabel#proc_lbl {{
            color: {text};
            font-weight: 600;
        }}

        /* ─── Splitter ─── */
        QSplitter::handle {{ background-color: {border}; }}
        QSplitter::handle:horizontal {{ width: 1px; }}
        QSplitter::handle:vertical   {{ height: 1px; }}

        /* ─── Scrollbars ─── */
        QScrollBar:vertical {{
            background: {bg};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {border};
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {text_dim}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        
        QScrollBar:horizontal {{
            background: {bg};
            height: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {border};
            border-radius: 4px;
            min-width: 20px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}

        /* ─── Dock widget ─── */
        QDockWidget::title {{
            background-color: {surface};
            color: {text};
            padding: 4px 8px;
            border-bottom: 1px solid {border};
        }}
        
        /* ─── Tabs ─── */
        QTabWidget::pane {{ border: 1px solid {border}; top: -1px; }}
        QTabBar::tab {{
            background: {surface};
            color: {text_dim};
            padding: 8px 16px;
            border: 1px solid {border};
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{ background: {bg}; border-bottom-color: {bg}; color: {text}; font-weight: bold; }}

        QCheckBox::indicator {{
            width: 16px; height: 16px;
            border: 1px solid {border};
            border-radius: 3px;
            background: {btn};
        }}
        QCheckBox::indicator:checked {{
            background: {accent};
            border-color: {accent};
        }}
        """)

    # ── Menu ──────────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        mb = self.menuBar()

        # File
        self._file_menu = mb.addMenu(tr("menu_file"))
        
        self._act_attach = QAction(tr("btn_attach"), self)
        self._act_attach.setShortcut(QKeySequence("Ctrl+O"))
        self._act_attach.triggered.connect(self._open_process_selector)
        self._file_menu.addAction(self._act_attach)

        self._act_detach = QAction(tr("btn_detach"), self)
        self._act_detach.triggered.connect(self._detach)
        self._file_menu.addAction(self._act_detach)
        self._file_menu.addSeparator()
        
        # CT (Cheat Engine) import/export
        self._act_import_ct = QAction("📂 CT İçe Aktar", self)
        self._act_import_ct.triggered.connect(self._on_import_ct)
        self._file_menu.addAction(self._act_import_ct)
        
        self._act_export_ct = QAction("📤 CT Dışa Aktar", self)
        self._act_export_ct.triggered.connect(self._on_export_ct)
        self._file_menu.addAction(self._act_export_ct)
        
        self._file_menu.addSeparator()
        
        self._act_import_json = QAction("📥 " + (tr("btn_import") if tr("btn_import") != "!btn_import!" else "JSON İçe Aktar"), self)
        self._act_import_json.triggered.connect(self._on_import_json)
        self._file_menu.addAction(self._act_import_json)
        
        self._act_export_json = QAction("📤 " + (tr("btn_export") if tr("btn_export") != "!btn_export!" else "JSON Dışa Aktar"), self)
        self._act_export_json.triggered.connect(self._on_export_json)
        self._file_menu.addAction(self._act_export_json)
        self._file_menu.addSeparator()

        self._act_exit = QAction(tr("menu_exit"), self)
        self._act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        self._act_exit.triggered.connect(self.close)
        self._file_menu.addAction(self._act_exit)

        # Settings
        self._settings_menu = mb.addMenu(tr("menu_settings"))
        self._act_settings = QAction(tr("settings_title"), self)
        self._act_settings.triggered.connect(self._open_settings)
        self._settings_menu.addAction(self._act_settings)
        self._settings_menu.addSeparator()
        
        # Language configuration
        self._act_language = QAction("🌍 Dil / Language", self)
        self._act_language.setShortcut(QKeySequence("Ctrl+L"))
        self._act_language.triggered.connect(self._open_language_dialog)
        self._settings_menu.addAction(self._act_language)
        self._settings_menu.addSeparator()
        
        # Hotkey configuration
        self._act_hotkeys = QAction(tr("menu_hotkeys") if tr("menu_hotkeys") != "!menu_hotkeys!" else "⌨️ Global Kısayollar", self)
        self._act_hotkeys.setShortcut(QKeySequence("Ctrl+H"))
        self._act_hotkeys.triggered.connect(self._open_hotkey_dialog)
        self._settings_menu.addAction(self._act_hotkeys)

        # View / Görünüm
        self._view_menu = mb.addMenu(tr("menu_view"))
        self._act_ptr = QAction("🎯 " + tr("menu_pointer"), self)
        self._act_ptr.setShortcut(QKeySequence("Ctrl+P"))
        self._act_ptr.triggered.connect(self._show_pointer_panel)
        self._view_menu.addAction(self._act_ptr)
        
        # AOB Scanner
        self._act_aob = QAction("� " + tr("menu_aob"), self)
        self._act_aob.setShortcut(QKeySequence("Ctrl+B"))
        self._act_aob.triggered.connect(self._show_aob_dialog)
        self._view_menu.addAction(self._act_aob)
        
        # Graph Viewer
        self._act_graph = QAction("� " + tr("menu_graph"), self)
        self._act_graph.setShortcut(QKeySequence("Ctrl+G"))
        self._act_graph.triggered.connect(self._show_graph_dialog)
        self._view_menu.addAction(self._act_graph)
        
        # Memory Map
        self._act_memmap = QAction("�️ " + tr("menu_memory_map"), self)
        self._act_memmap.setShortcut(QKeySequence("Ctrl+M"))
        self._act_memmap.triggered.connect(self._show_memory_map)
        self._view_menu.addAction(self._act_memmap)

        # Help
        self._help_menu = mb.addMenu(tr("menu_help"))
        self._act_about = QAction(tr("menu_about"), self)
        self._act_about.triggered.connect(self._show_about)
        self._help_menu.addAction(self._act_about)

    def retranslate_ui(self) -> None:
        """Update all strings in the UI after a language change."""
        self.setWindowTitle(tr("app_name"))
        self._file_menu.setTitle(tr("menu_file"))
        self._act_attach.setText(tr("btn_attach"))
        self._act_detach.setText(tr("btn_detach"))
        self._act_exit.setText(tr("menu_exit"))
        self._settings_menu.setTitle(tr("menu_settings"))
        self._act_settings.setText(tr("settings_title"))
        self._help_menu.setTitle(tr("menu_help"))
        self._act_about.setText(tr("menu_about"))
        
        self._attach_btn.setText("  ⚙ " + tr("btn_attach"))
        if not self._pm.is_attached:
            self._proc_lbl.setText("  " + tr("lbl_none"))
            self._status_lbl.setText(tr("msg_detached"))
        
        self._scan_panel.retranslate_ui()
        self._results.retranslate_ui()
        self._ptr_panel.retranslate_ui()
        self._mem_viewer_dock.setWindowTitle(tr("tab_memory"))
        self._ptr_dock.setWindowTitle(tr("tab_pointer"))

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main Toolbar", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        self._attach_btn = QPushButton("  🔗 " + tr("btn_attach"))
        self._attach_btn.setObjectName("primary_btn")
        self._attach_btn.setFixedHeight(32)
        self._attach_btn.clicked.connect(self._open_process_selector)
        tb.addWidget(self._attach_btn)
        
        tb.addSeparator()
        
        self._proc_lbl = QLabel("  " + tr("lbl_none"))
        self._proc_lbl.setObjectName("proc_lbl")
        tb.addWidget(self._proc_lbl)

    # ── Central widget ────────────────────────────────────────────────────────

    def _build_central(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_lay = QHBoxLayout(central)
        main_lay.setContentsMargins(12, 12, 12, 12)
        main_lay.setSpacing(10)

        # Left: scan panel (fixed width)
        self._scan_panel = ScanPanel()
        self._scan_panel.sig_first_scan.connect(self._on_first_scan)
        self._scan_panel.sig_next_scan.connect(self._on_next_scan)
        self._scan_panel.sig_reset.connect(self._on_reset)
        self._scan_panel.set_attached(False)
        main_lay.addWidget(self._scan_panel)

        # Right: results
        self._results = ResultsTable()
        self._results.sig_add_to_watchlist.connect(self._on_add_watchlist)
        self._results.sig_write_value.connect(self._on_write_value)
        self._results.sig_freeze_toggled.connect(self._on_freeze_toggled)
        self._results.sig_browse_memory.connect(self._on_browse_memory)
        self._results.sig_request_page.connect(self._on_request_result_page)
        main_lay.addWidget(self._results, stretch=1)

        # Memory Viewer (dock)
        self._mem_viewer = MemoryViewer()
        self._mem_viewer_dock = QDockWidget(tr("tab_memory"), self)
        self._mem_viewer_dock.setWidget(self._mem_viewer)
        self._mem_viewer_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)
        self._mem_viewer_dock.hide()
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._mem_viewer_dock)

        # Pointer panel (dock) - compact size
        self._ptr_panel = PointerPanel()
        self._ptr_panel.sig_resolve.connect(self._on_pointer_resolve)
        self._ptr_panel.sig_add_chain.connect(self._on_add_chain_watchlist)
        self._ptr_panel.sig_filter.connect(self._on_pointer_filter)
        self._ptr_panel.sig_save.connect(self._on_pointer_save)
        self._ptr_panel.sig_load.connect(self._on_pointer_load)
        self._ptr_panel.set_attached(False)  # Başlangıçta bağlı değil
        dock = QDockWidget(tr("dock_pointer") if tr("dock_pointer") != "!dock_pointer!" else "🎯 Pointer", self)
        dock.setWidget(self._ptr_panel)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        dock.hide()
        self._ptr_dock = dock
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        
        # Tabify docks to save space (after both are created)
        self.tabifyDockWidget(self._mem_viewer_dock, self._ptr_dock)

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_lbl = QLabel(tr("lbl_none"))
        sb.addWidget(self._status_lbl, 1)
        self._region_lbl = QLabel("")
        sb.addPermanentWidget(self._region_lbl)

    # ── Process Attachment ────────────────────────────────────────────────────

    def _open_process_selector(self) -> None:
        dlg = ProcessSelectorDialog(self)
        if dlg.exec() and dlg.selected_process:
            proc = dlg.selected_process
            self._attach(proc.pid, proc.name)

    def _attach(self, pid: int, name: str) -> None:
        try:
            self._detach()

            ok = self._pm.open_process(pid)
            if not ok:
                QMessageBox.critical(
                    self, tr("settings_title"),
                    tr("msg_attach_error").format(pid) + "\n" +
                    "Try running EnesMem as Administrator.",
                )
                return

            self._mem     = MemoryIO(self._pm.handle, self._pm.is_64bit)
            self._scanner = Scanner(self._mem)
            self._freezer = Freezer(self._mem)
            self._ptr_sc  = PointerScanner(self._mem, self._pm)
            self._mem_viewer.set_memory_io(self._mem)

            self._scan_panel.set_attached(True)
            self._ptr_panel.set_attached(True)
            self._proc_lbl.setText(f"  ⬤  {name}  (PID: {pid})")
            self._status_lbl.setText(tr("msg_attached").format(name, pid))

            # Count regions
            try:
                regions = self._mem.get_regions()
                self._region_lbl.setText(f"Regions: {len(regions):,}")
            except Exception:
                self._region_lbl.setText("")

            # Start live refresh
            self._refresh_timer.start(LIVE_REFRESH_INTERVAL_MS)
            log.info("Attached to %s PID=%d", name, pid)
        except Exception as e:
            log.exception("Crash during attach")
            QMessageBox.critical(self, "Critical Error", f"EnesMem crashed during process attachment:\n{str(e)}")
            self._detach()

    def _detach(self) -> None:
        self._refresh_timer.stop()
        if self._freezer:
            self._freezer.stop()
        try:
            if self._scan_thread and self._scan_thread.isRunning():
                if self._scanner:
                    self._scanner.cancel()
                self._scan_thread.quit()
                self._scan_thread.wait(2000)
            
            if self._ptr_thread and self._ptr_thread.isRunning():
                if self._ptr_sc:
                    self._ptr_sc.cancel()
                self._ptr_thread.quit()
                self._ptr_thread.wait(2000)
        except RuntimeError:
            self._scan_thread = None
            self._scan_worker = None
            self._ptr_thread = None
            self._ptr_worker = None

        self._pm.close_handle()
        self._mem     = None
        self._scanner = None
        self._freezer = None
        self._ptr_sc  = None

        self._scan_panel.set_attached(False)
        self._ptr_panel.set_attached(False)
        self._results.clear_found()
        self._proc_lbl.setText("  " + tr("lbl_none"))
        self._status_lbl.setText(tr("msg_detached"))
        self._region_lbl.setText("")

    # ── Scan slots ────────────────────────────────────────────────────────────

    @pyqtSlot(object, object, str, float)
    def _on_first_scan(self, dtype: DataType, mode: ScanMode, value_str: str, tolerance: float) -> None:
        if not self._scanner:
            return

        value = None
        if value_str:
            value = parse_user_input(value_str, dtype)
            if value is None and mode.name in {"EXACT", "BIGGER", "SMALLER", "INCREASED_BY", "DECREASED_BY"}:
                QMessageBox.warning(self, "Invalid Value",
                                    f"Cannot parse '{value_str}' as {dtype.name}")
                return

        self._run_scan(is_first=True, dtype=dtype, mode=mode, value=value, tolerance=tolerance)

    @pyqtSlot(object, str, float)
    def _on_next_scan(self, mode: ScanMode, value_str: str, tolerance: float) -> None:
        if not self._scanner:
            return
        dtype = self._scanner.dtype
        value = parse_user_input(value_str, dtype) if value_str else None
        self._run_scan(is_first=False, dtype=dtype, mode=mode, value=value, tolerance=tolerance)

    @pyqtSlot()
    def _on_reset(self) -> None:
        if self._scanner:
            self._scanner.reset()
        self._results.clear_found()
        self._scan_panel.set_result_count(0, 0)
        self._status_lbl.setText(tr("msg_scan_reset"))

    def _run_scan(self, is_first: bool, dtype: DataType, mode: ScanMode, value, tolerance: float = 0.0) -> None:
        """Launch scan on a QThread."""
        try:
            if self._scan_thread and self._scan_thread.isRunning():
                return  # Already scanning
        except RuntimeError:
            self._scan_thread = None
            self._scan_worker = None

        self._scan_panel.set_scanning(True)
        self._status_lbl.setText(tr("msg_scanning"))

        if is_first:
            self._results.reset_pagination()

        worker = ScanWorker(self._scanner, is_first, dtype, mode, value, tolerance)
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.sig_progress.connect(self._scan_panel.set_progress)
        worker.sig_done.connect(self._on_scan_done)
        worker.sig_error.connect(self._on_scan_error)
        worker.sig_done.connect(thread.quit)
        worker.sig_error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._scan_thread = thread
        self._scan_worker = worker
        thread.start()

    @pyqtSlot(int)
    def _on_scan_done(self, count: int) -> None:
        self._scan_panel.set_scanning(False)
        scan_num = self._scanner.scan_count if self._scanner else 0
        self._scan_panel.set_result_count(count, scan_num)

        dtype = self._scanner.dtype if self._scanner else DataType.INT32
        
        # Get the first page of results (0-2000)
        results = self._scanner.get_results_slice(0, 2000) if self._scanner else []
        
        # Update results table - this will show the first page
        self._results.populate_found(results, dtype, total_count=count)
        self._results.set_dtype(dtype)

        label = tr("btn_first_scan") if scan_num == 1 else tr("btn_next_scan")
        self._status_lbl.setText(tr("msg_scan_complete").format(label, f"{count:,}"))

    @pyqtSlot(int, int)
    def _on_request_result_page(self, start: int, count: int) -> None:
        if not self._scanner: return
        results = self._scanner.get_results_slice(start, count)
        self._results.populate_found(results, self._scanner.dtype, total_count=self._scanner.result_count)

    @pyqtSlot(str)
    def _on_scan_error(self, msg: str) -> None:
        self._scan_panel.set_scanning(False)
        QMessageBox.critical(self, tr("menu_help"), msg)
        self._status_lbl.setText(tr("msg_scan_failed"))

    # ── Live refresh ──────────────────────────────────────────────────────────

    def _live_refresh(self) -> None:
        if not self._scanner or not self._mem:
            return
        
        # Validate handle
        if not getattr(self._mem, '_handle', None):
            return
            
        try:
            if self._scan_thread and self._scan_thread.isRunning():
                return
        except RuntimeError:
            # C++ object has been deleted, clean up Python references
            self._scan_thread = None
            self._scan_worker = None

        try:
            # Refresh found addresses
            self._scanner.refresh_values()
            results = self._scanner.get_results_slice(0, 2000)
            self._results.refresh_found(results)
        except Exception as e:
            log.debug("Live refresh (found): %s", e)

        try:
            # Refresh pointer panel live values
            self._ptr_panel.refresh_live_values(self._ptr_sc, self._mem)
        except Exception as e:
            log.debug("Live refresh (pointer): %s", e)

        # Refresh watchlist
        try:
            if self._results._watchlist:
                val_map: dict = {}
                for entry in self._results._watchlist:
                    # Validate handle before each read
                    if not getattr(self._mem, '_handle', None):
                        return
                    
                    # 1. Resolve pointer if applicable
                    if entry.module_name and entry.offsets and self._ptr_sc:
                        try:
                            addr = self._ptr_sc.resolve_from_module(entry.module_name, entry.offsets)
                            if addr is not None and addr != entry.address:
                                old_addr = entry.address
                                entry.address = addr
                                # Transfer freeze status
                                if entry.frozen and self._freezer:
                                    try:
                                        self._freezer.unfreeze(old_addr)
                                    except Exception:
                                        pass
                                    # We keep the old locked value
                                    if entry.current_value is not None:
                                        try:
                                            self._freezer.freeze(addr, entry.current_value, entry.dtype)
                                        except Exception:
                                            pass
                        except Exception:
                            pass

                    # 2. Read value
                    try:
                        addr = entry.address
                        val = self._mem.read_value(addr, entry.dtype)
                        if val is not None:
                            val_map[addr] = val
                            
                            # 3. Track value for graphing
                            try:
                                graph_manager.track_value(addr, float(val) if isinstance(val, (int, float)) else 0.0, entry.dtype, entry.description)
                            except Exception:
                                pass
                    except Exception:
                        pass
                self._results.refresh_watchlist(val_map)
        except Exception as e:
            log.debug("Live refresh (watchlist): %s", e)

        # Refresh Memory Viewer if visible
        try:
            if self._mem_viewer_dock.isVisible():
                self._mem_viewer.refresh()
        except Exception as e:
            log.debug("Live refresh (memviewer): %s", e)

    def _watchlist_addrs(self) -> list[int]:
        return [e.address for e in self._results._watchlist]

    # ── Write / Freeze ────────────────────────────────────────────────────────

    @pyqtSlot(int, object)
    def _mask_addr(self, address: int) -> int:
        """Mask address based on current process bitness to prevent sign extension issues."""
        if not self._mem:
            return address
        mask = (1 << (8 * self._mem._ptr_size)) - 1
        return address & mask

    def _on_add_watchlist(self, address: int, dtype: DataType) -> None:
        address = self._mask_addr(address)
        log.debug("Added to watchlist: 0x%X (%s)", address, dtype.name)

    @pyqtSlot(object, object, str)
    def _on_write_value(self, address: int, dtype: DataType, value_str: str) -> None:
        address = self._mask_addr(address)
        log.info("GUI: Write request for 0x%X (%s) value='%s'", address, dtype.name, value_str)
        if not self._mem:
            log.error("GUI: No memory object!")
            return
        val = parse_user_input(value_str, dtype)
        if val is None:
            log.warning("GUI: Parse error for '%s'", value_str)
            QMessageBox.warning(self, "Write Error", f"Cannot parse '{value_str}' as {dtype.name}")
            return
        raw = value_to_bytes(val, dtype)
        log.info("GUI: Writing %d bytes to 0x%X: %s", len(raw) if raw else 0, address, raw.hex() if raw else "None")
        
        ok = self._mem.write_value(address, val, dtype)
        if ok:
            log.info("GUI: Write SUCCESS for 0x%X", address)
            self._status_lbl.setText(f"Written {value_str} → 0x{address:X}")
            if self._freezer and self._freezer.is_frozen(address):
                log.info("GUI: Updating frozen value for 0x%X", address)
                self._freezer.freeze(address, val, dtype)
        else:
            from utils.winapi import last_error_str
            err = last_error_str()
            log.error("GUI: Write FAILED for 0x%X - %s", address, err)
            QMessageBox.warning(
                self, "Write Failed", 
                f"Could not write {value_str} to 0x{address:X}\n\nReason: {err}"
            )

    @pyqtSlot(object, object, bool)
    def _on_freeze_toggled(self, address: int, dtype: DataType, freeze: bool) -> None:
        address = self._mask_addr(address)
        log.info("GUI: Freeze toggle for 0x%X (%s) -> %s", address, dtype.name, freeze)
        if not self._freezer or not self._mem:
            log.error("GUI: Freezer or Mem not initialized")
            return
        
        if freeze:
            val = self._mem.read_value(address, dtype)
            if val is not None:
                log.info("GUI: Freezing 0x%X at current value %s", address, val)
                self._freezer.freeze(address, val, dtype)
                self._status_lbl.setText(f"Frozen 0x{address:X}")
            else:
                log.warning("GUI: Could not read value to freeze 0x%X", address)
        else:
            log.info("GUI: Unfreezing 0x%X", address)
            self._freezer.unfreeze(address)
            self._status_lbl.setText(f"Unfrozen 0x{address:X}")

    @pyqtSlot(object)
    def _on_browse_memory(self, address: int) -> None:
        self._mem_viewer_dock.show()
        self._mem_viewer_dock.raise_()
        self._mem_viewer.set_address(address)
        self._status_lbl.setText(f"Browsing memory at 0x{format_address(address)}")

    # ── Pointer Scanner ───────────────────────────────────────────────────────

    def _show_pointer_panel(self) -> None:
        self._ptr_dock.show()
    
    def _show_aob_dialog(self) -> None:
        """Show AOB pattern scanner dialog."""
        show_aob_dialog(self._mem, self)
    
    def _show_graph_dialog(self) -> None:
        """Show value graph dialog."""
        show_graph_dialog(self)
    
    def _show_memory_map(self) -> None:
        """Show memory map dialog."""
        handle = getattr(self._mem, '_handle', None) if self._mem else None
        show_memory_map_dialog(handle, self)
    
    def _on_import_json(self) -> None:
        """Import watchlist from JSON."""
        self._results.import_watchlist()
    
    def _on_export_json(self) -> None:
        """Export watchlist to JSON."""
        self._results.export_watchlist()
    
    def _on_import_ct(self) -> None:
        """Import Cheat Engine CT file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "CT Dosyası İçe Aktar",
            "",
            "Cheat Engine Tables (*.CT);;All Files (*.*)"
        )
        if not path:
            return
        
        entries = import_ct_file(path)
        if entries:
            for entry in entries:
                if entry.get("is_pointer"):
                    self._results.add_pointer_to_watchlist(
                        entry.get("module_name", ""),
                        entry.get("offsets", []),
                        entry.get("address", 0),
                        entry.get("dtype", DataType.INT32),
                        entry.get("description", "")
                    )
                else:
                    self._results.add_to_watchlist(
                        entry.get("address", 0),
                        entry.get("dtype", DataType.INT32),
                        entry.get("description", "")
                    )
            
            self._status_lbl.setText(f"CT dosyası yüklendi: {len(entries)} giriş")
            QMessageBox.information(self, "Başarılı", f"{len(entries)} giriş içe aktarıldı.")
        else:
            QMessageBox.warning(self, "Hata", "CT dosyası okunamadı.")
    
    def _on_export_ct(self) -> None:
        """Export watchlist to CT file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "CT Dosyası Olarak Kaydet",
            "enesmem_table.ct",
            "Cheat Engine Tables (*.CT)"
        )
        if not path:
            return
        
        if export_ct_file(self._results._watchlist, path):
            self._status_lbl.setText(f"Watchlist CT olarak kaydedildi")
            QMessageBox.information(self, "Başarılı", f"Watchlist CT dosyasına kaydedildi.")
        else:
            QMessageBox.critical(self, "Hata", "Dışa aktarma başarısız.")

    @pyqtSlot(str, str, object, int, int)
    def _on_pointer_resolve(self, module: str, offsets_str: str, dtype: DataType, depth: int, max_offset: int) -> None:
        if not self._ptr_sc or not self._mem:
            QMessageBox.warning(self, "Not Attached", "Attach to a process first.")
            return
        
        # Validate handle
        if not getattr(self._mem, '_handle', None):
            QMessageBox.warning(self, "Not Attached", "Process detached. Please reattach.")
            return

        if module == "__scan__":
            # Chain scan
            try:
                target = int(offsets_str, 16)
            except ValueError:
                target = int(offsets_str) if offsets_str.isdigit() else None
                if target is None:
                    QMessageBox.warning(self, "Bad Address", "Enter a valid hex or decimal target address.")
                    return

            self._run_pointer_scan(target, depth=depth, max_offset=max_offset)
            return

        # Manual offset resolution
        try:
            offsets = [int(x.strip(), 16) for x in offsets_str.replace(",", " ").split()]
        except ValueError:
            QMessageBox.warning(self, "Bad Offsets",
                                "Offsets must be hex values, comma or space separated.")
            return

        try:
            # Validate handle before resolve
            if not getattr(self._mem, '_handle', None):
                self._ptr_panel.set_result(None)
                return
                
            final = self._ptr_sc.resolve_from_module(module, offsets)
            if final and self._mem:
                # Validate handle again before read
                if not getattr(self._mem, '_handle', None):
                    self._ptr_panel.set_result(None)
                    return
                val = self._mem.read_value(final, dtype)
                self._ptr_panel.set_result(final, format_value(val, dtype))
            else:
                self._ptr_panel.set_result(None)
        except Exception as e:
            log.debug("Pointer resolve error: %s", e)
            self._ptr_panel.set_result(None)

    def _run_pointer_scan(self, target: int, depth: int = 3, max_offset: int = 2048) -> None:
        """Launch pointer scan on a QThread."""
        try:
            if self._ptr_thread and self._ptr_thread.isRunning():
                return
        except RuntimeError:
            self._ptr_thread = None
            self._ptr_worker = None

        self._ptr_panel.set_scanning(True)
        self._scan_panel.set_scanning(True) # Use main progress bar too
        self._status_lbl.setText(f"Scanning pointers for 0x{target:X} (depth={depth}, offset={max_offset})...")

        worker = PointerWorker(self._ptr_sc, target, max_depth=depth, max_offset=max_offset)
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.sig_progress.connect(self._scan_panel.set_progress)
        worker.sig_done.connect(self._on_pointer_scan_done)
        worker.sig_error.connect(self._on_pointer_scan_error)
        worker.sig_done.connect(thread.quit)
        worker.sig_error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._ptr_thread = thread
        self._ptr_worker = worker
        thread.start()

    @pyqtSlot(list)
    def _on_pointer_scan_done(self, chains: list) -> None:
        self._ptr_panel.set_scanning(False)
        self._scan_panel.set_scanning(False)
        self._last_ptr_results = chains
        self._ptr_panel.populate_chains(chains)
        self._status_lbl.setText(f"Pointer scan complete: {len(chains)} chains found.")

    @pyqtSlot(str)
    def _on_pointer_scan_error(self, msg: str) -> None:
        self._ptr_panel.set_scanning(False)
        self._scan_panel.set_scanning(False)
        QMessageBox.critical(self, "Pointer Scan Error", msg)
        self._status_lbl.setText("Pointer scan failed.")

    @pyqtSlot(str, list, object, object)
    def _on_add_chain_watchlist(self, module_name: str, offsets: list, dtype: DataType, final_addr: int) -> None:
        self._results.add_pointer_to_watchlist(module_name, offsets, final_addr, dtype)
        self._status_lbl.setText(f"Added pointer to watchlist: {module_name} + offsets")

    @pyqtSlot(object, object)
    def _on_pointer_filter(self, expected_value: any, dtype: DataType) -> None:
        if not self._ptr_sc:
            QMessageBox.warning(self, "Not Attached", "Attach to a process first.")
            return
            
        if not hasattr(self, "_last_ptr_results") or not self._last_ptr_results:
            QMessageBox.information(self, "No Results", "Perform a scan or load results first.")
            return
            
        chains = self._last_ptr_results

        self._run_pointer_filter(chains, expected_value, dtype)

    def _run_pointer_filter(self, chains: list, expected_value: any, dtype: DataType) -> None:
        try:
            if self._ptr_thread and self._ptr_thread.isRunning():
                return
        except RuntimeError:
            self._ptr_thread = None

        self._ptr_panel.set_scanning(True)
        self._scan_panel.set_scanning(True)
        self._status_lbl.setText(f"Filtering {len(chains)} chains for value {expected_value}...")

        worker = PointerWorker(self._ptr_sc, target=expected_value, mode="FILTER", dtype=dtype, chains=chains)
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.sig_progress.connect(self._scan_panel.set_progress)
        worker.sig_done.connect(self._on_pointer_scan_done)
        worker.sig_error.connect(self._on_pointer_scan_error)
        worker.sig_done.connect(thread.quit)
        worker.sig_error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self._ptr_thread = thread
        self._ptr_worker = worker
        thread.start()

    @pyqtSlot()
    def _on_pointer_save(self) -> None:
        if not hasattr(self, "_last_ptr_results") or not self._last_ptr_results:
            QMessageBox.warning(self, "No Results", "Nothing to save.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Save Pointer Chains", "", "JSON Files (*.json)")
        if path:
            self._ptr_sc.export_chains(self._last_ptr_results, path)
            self._status_lbl.setText(f"Saved {len(self._last_ptr_results)} chains to {path}")

    @pyqtSlot()
    def _on_pointer_load(self) -> None:
        if not self._ptr_sc:
            QMessageBox.warning(self, "Not Attached", "Attach to a process first.")
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "Load Pointer Chains", "", "JSON Files (*.json)")
        if path:
            chains = self._ptr_sc.import_chains(path)
            if chains:
                self._last_ptr_results = chains
                # We should also resolve values for the loaded chains
                self._run_pointer_filter(chains, None, DataType.INT32) # Pass None/INT32 just to refresh values without strict filtering?
                # Actually, filter_chains with expected_value=None might not work.
                # Let's just populate them and maybe trigger a manual refresh?
                # For now, let's just populate.
                self._ptr_panel.populate_chains(chains)
                self._status_lbl.setText(f"Loaded {len(chains)} chains from {path}")

    # ── Misc ──────────────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        if SettingsDialog.show_settings(self):
            # If settings changed (language/theme), update everything
            self._apply_stylesheet()
            self.retranslate_ui()

    def _show_about(self) -> None:
        about_text = """
        <center>
        <h2>🧠 EnesMem</h2>
        <p><b>Gelişmiş Bellek Tarayıcı & Editör</b></p>
        <hr>
        <table cellpadding="4">
        <tr><td align="right"><b>Versiyon:</b></td><td>v2.0.0</td></tr>
        <tr><td align="right"><b>Yapımcı:</b></td><td>Enes Talha Elcan</td></tr>
        <tr><td align="right"><b>Teknoloji:</b></td><td>Python 3.11+ · PyQt6 · ctypes</td></tr>
        <tr><td align="right"><b>Platform:</b></td><td>Windows x64</td></tr>
        </table>
        <hr>
        <p><i>Cheat Engine'den ilham alınmış, Python ile yeniden yazılmıştır.</i></p>
        <p>© 2024 EnesMem Project</p>
        </center>
        """
        QMessageBox.about(self, tr("about_title") if tr("about_title") != "!about_title!" else "Hakkında", about_text)

    def closeEvent(self, event) -> None:
        # Stop global hotkeys
        try:
            hotkey_manager.stop()
            log.info("MainWindow: Global hotkeys stopped")
        except Exception as e:
            log.debug("Hotkey stop error: %s", e)
        
        self._detach()
        event.accept()


def main() -> None:
    """Main entry point for EnesMem application."""
    import sys
    from PyQt5.QtWidgets import QApplication
    from utils.i18n import tr
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
