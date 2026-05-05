"""
memory_viewer.py — High-performance, virtualized memory hex editor.
Uses QAbstractScrollArea to handle raw memory inspection.
"""
from PyQt6.QtWidgets import QAbstractScrollArea, QWidget, QMenu
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QFont, QColor, QPalette, QKeyEvent, QMouseEvent

from utils.converters import format_address
from utils.logger import log

# Configuration
ROWS_VISIBLE = 32
BYTES_PER_ROW = 16
FONT_SIZE = 10
LINE_HEIGHT = 20
ADDR_WIDTH = 140
HEX_WIDTH = 450
ASCII_WIDTH = 200

class MemoryViewer(QAbstractScrollArea):
    """
    Virtualized Hex Viewer/Editor.
    Displays Address | Hex Bytes | ASCII.
    """
    def __init__(self, memory_io=None, parent=None):
        super().__init__(parent)
        self._mem_io = memory_io
        self._current_address = 0
        self._active = False
        
        # UI State
        self._bytes_data = b""
        self._prev_bytes_data = b""
        self._highlight_timer = 0 # for live refresh fades
        
        self.setMouseTracking(True)
        self._setup_ui()
        
    def _setup_ui(self):
        self.setObjectName("memory_viewer")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)
        self.setFont(QFont("Consolas", FONT_SIZE))
        
        # Scrollbar setup
        # We use a virtual range for the scrollbar. 
        # Since we can't scroll the whole 64-bit space easily, we scroll relative to the base.
        self.verticalScrollBar().setRange(0, 100000) 
        self.verticalScrollBar().setValue(50000) # Start in the middle of our virtual buffer
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        self.horizontalScrollBar().setRange(0, 0)
        self.horizontalScrollBar().hide()
        
        # Refresh timer (managed by main_window usually, but can be internal)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        
    def set_memory_io(self, memory_io):
        self._mem_io = memory_io
        
    def set_address(self, address: int):
        """Jump to a specific address."""
        self._current_address = address & ~0xF # Align to 16 bytes
        self._active = True
        self.verticalScrollBar().setValue(50000) # Reset scrollbar to center
        self.refresh(force=True)
        
    def _on_scroll(self, value):
        if not self._active:
            return
        # Calculate delta
        delta = (value - 50000) * BYTES_PER_ROW
        # This is a bit naive but works for local scrolling
        # In a real app, we'd jump regions.
        self._current_address += delta
        self.verticalScrollBar().blockSignals(True)
        self.verticalScrollBar().setValue(50000)
        self.verticalScrollBar().blockSignals(False)
        self.refresh()

    def refresh(self, force=False):
        if not self._active or not self._mem_io:
            return
            
        # Read enough bytes to fill the view
        bytes_to_read = ROWS_VISIBLE * BYTES_PER_ROW
        data = self._mem_io.read_bytes(self._current_address, bytes_to_read)
        
        if data is None:
            # Maybe region changed or unreadable
            self._bytes_data = b"\x00" * bytes_to_read
        else:
            if not force:
                self._prev_bytes_data = self._bytes_data
            else:
                self._prev_bytes_data = data
            self._bytes_data = data
            
        self.viewport().update()

    # ── Rendering ─────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setFont(self.font())
        
        palette = self.palette()
        text_color = palette.color(QPalette.ColorRole.Text)
        dim_color = QColor("#8b949e")
        addr_color = QColor("#58a6ff")
        changed_color = QColor("#f87171") # Red for changes
        
        rect = self.viewport().rect()
        
        for row in range(ROWS_VISIBLE):
            y = row * LINE_HEIGHT + 15
            row_addr = self._current_address + (row * BYTES_PER_ROW)
            
            # 1. Draw Address
            painter.setPen(addr_color)
            painter.drawText(10, y, format_address(row_addr))
            
            # 2. Draw Hex
            for col in range(BYTES_PER_ROW):
                idx = row * BYTES_PER_ROW + col
                if idx < len(self._bytes_data):
                    val = self._bytes_data[idx]
                    prev_val = self._prev_bytes_data[idx] if idx < len(self._prev_bytes_data) else val
                    
                    if val != prev_val:
                        painter.setPen(changed_color)
                    else:
                        painter.setPen(text_color)
                        
                    hex_str = f"{val:02X}"
                    painter.drawText(ADDR_WIDTH + (col * 28), y, hex_str)
                else:
                    painter.setPen(dim_color)
                    painter.drawText(ADDR_WIDTH + (col * 28), y, "??")
            
            # 3. Draw ASCII
            painter.setPen(dim_color)
            ascii_text = ""
            for col in range(BYTES_PER_ROW):
                idx = row * BYTES_PER_ROW + col
                if idx < len(self._bytes_data):
                    val = self._bytes_data[idx]
                    if 32 <= val <= 126:
                        ascii_text += chr(val)
                    else:
                        ascii_text += "."
                else:
                    ascii_text += " "
            painter.drawText(ADDR_WIDTH + HEX_WIDTH, y, ascii_text)

    def sizeHint(self):
        return QSize(ADDR_WIDTH + HEX_WIDTH + ASCII_WIDTH, 400)

    # ── Interaction ───────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_PageDown:
            self._current_address += ROWS_VISIBLE * BYTES_PER_ROW
            self.refresh()
        elif event.key() == Qt.Key.Key_PageUp:
            self._current_address -= ROWS_VISIBLE * BYTES_PER_ROW
            self.refresh()
        elif event.key() == Qt.Key.Key_Down:
            self._current_address += BYTES_PER_ROW
            self.refresh()
        elif event.key() == Qt.Key.Key_Up:
            self._current_address -= BYTES_PER_ROW
            self.refresh()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        # TODO: Implement byte selection and editing
        super().mousePressEvent(event)

    def _on_context_menu(self, pos):
        menu = QMenu(self)
        act_goto = menu.addAction("🔍 Go to Address...")
        act_copy = menu.addAction("📋 Copy Current Address")
        
        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if chosen == act_goto:
            from PyQt6.QtWidgets import QInputDialog
            addr_str, ok = QInputDialog.getText(self, "Go to Address", "Address (hex):")
            if ok and addr_str.strip():
                try:
                    addr = int(addr_str.strip(), 16)
                    self.set_address(addr)
                except ValueError:
                    pass
        elif chosen == act_copy:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(format_address(self._current_address))
