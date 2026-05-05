"""
graph_dialog.py — Value history graph visualization dialog.
"""
from typing import Optional, List

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QSplitter, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QPaintEvent

from core.value_graph import graph_manager, ValueHistory
from utils.i18n import tr
from utils.logger import log


class GraphWidget(QWidget):
    """Custom widget for drawing value history graphs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: Optional[ValueHistory] = None
        self._min_value = 0.0
        self._max_value = 100.0
        self._padding = 40
        self.setMinimumSize(400, 250)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
    
    def set_history(self, history: Optional[ValueHistory]) -> None:
        """Set the history to display."""
        self._history = history
        if history:
            min_val, max_val = history.get_min_max()
            # Add some padding to y-axis
            range_val = max_val - min_val
            if range_val == 0:
                range_val = max_val * 0.1 if max_val != 0 else 10
            self._min_value = min_val - range_val * 0.1
            self._max_value = max_val + range_val * 0.1
        self.update()
    
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), QColor("#0d1117"))
        
        if not self._history or not self._history.data_points:
            # Draw "No data" message
            painter.setPen(QColor("#8b949e"))
            painter.setFont(QFont("Segoe UI", 12))
            text = tr("graph_no_data") if tr("graph_no_data") != "!graph_no_data!" else "Veri yok"
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
            return
        
        data = self._history.get_data()
        if len(data) < 2:
            return
        
        width = self.width() - 2 * self._padding
        height = self.height() - 2 * self._padding
        
        # Calculate scales
        min_ts = data[0][0]
        max_ts = data[-1][0]
        ts_range = max_ts - min_ts if max_ts != min_ts else 1
        
        value_range = self._max_value - self._min_value
        if value_range == 0:
            value_range = 1
        
        # Draw grid lines
        painter.setPen(QPen(QColor("#21262d"), 1))
        for i in range(5):
            y = self._padding + (height * i) / 4
            painter.drawLine(self._padding, int(y), self._padding + width, int(y))
        
        # Draw axes
        painter.setPen(QPen(QColor("#8b949e"), 2))
        # Y-axis
        painter.drawLine(self._padding, self._padding, self._padding, self._padding + height)
        # X-axis
        painter.drawLine(self._padding, self._padding + height, self._padding + width, self._padding + height)
        
        # Draw value labels on Y-axis
        painter.setPen(QColor("#8b949e"))
        painter.setFont(QFont("Consolas", 8))
        for i in range(5):
            value = self._max_value - (value_range * i) / 4
            y = self._padding + (height * i) / 4
            label = f"{value:.2f}" if abs(value) < 10000 else f"{value:.1e}"
            painter.drawText(5, int(y) + 4, label)
        
        # Draw graph line
        pen = QPen(QColor("#58a6ff"), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        points = []
        for ts, value in data:
            x = self._padding + ((ts - min_ts) / ts_range) * width
            y = self._padding + height - ((value - self._min_value) / value_range) * height
            points.append(QPoint(int(x), int(y)))
        
        # Draw polyline
        if len(points) > 1:
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])
        
        # Draw points
        painter.setPen(QPen(QColor("#3fb950"), 4))
        for point in points[::max(1, len(points) // 50)]:  # Draw every Nth point to avoid clutter
            painter.drawPoint(point)
        
        # Draw info box
        if data:
            latest = data[-1]
            painter.fillRect(self._padding, 5, 200, 25, QColor("#161b22"))
            painter.setPen(QColor("#c9d1d9"))
            painter.setFont(QFont("Segoe UI", 9))
            desc = self._history.description or f"0x{self._history.address:X}"
            info_text = f"{desc}: {latest[1]:.4f}"
            painter.drawText(self._padding + 5, 22, info_text)


class GraphDialog(QDialog):
    """Dialog for viewing value history graphs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_graphs)
        self._refresh_timer.start(500)  # Update every 500ms
        
        self.setWindowTitle(tr("graph_title") if tr("graph_title") != "!graph_title!" else "📊 Değer Grafikleri")
        self.setMinimumSize(900, 600)
        self.resize(1000, 700)
        
        self._build_ui()
        self._update_address_list()
    
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Controls
        controls = QHBoxLayout()
        
        controls.addWidget(QLabel(tr("lbl_select_address") if tr("lbl_select_address") != "!lbl_select_address!" else "Adres:"))
        
        self._address_combo = QComboBox()
        self._address_combo.setMinimumWidth(250)
        self._address_combo.currentIndexChanged.connect(self._on_address_changed)
        controls.addWidget(self._address_combo)
        
        self._track_chk = QCheckBox(tr("chk_track_live") if tr("chk_track_live") != "!chk_track_live!" else "Canlı İzle")
        self._track_chk.setChecked(True)
        controls.addWidget(self._track_chk)
        
        controls.addStretch()
        
        self._export_btn = QPushButton("📤 " + (tr("btn_export_csv") if tr("btn_export_csv") != "!btn_export_csv!" else "CSV Dışa Aktar"))
        self._export_btn.clicked.connect(self._on_export_csv)
        controls.addWidget(self._export_btn)
        
        self._clear_btn = QPushButton("🗑️ " + (tr("btn_clear_history") if tr("btn_clear_history") != "!btn_clear_history!" else "Geçmişi Temizle"))
        self._clear_btn.clicked.connect(self._on_clear_history)
        controls.addWidget(self._clear_btn)
        
        layout.addLayout(controls)
        
        # Splitter for graph and stats
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Graph widget
        self._graph_widget = GraphWidget()
        splitter.addWidget(self._graph_widget)
        
        # Stats table
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        stats_layout.addWidget(QLabel(tr("lbl_statistics") if tr("lbl_statistics") != "!lbl_statistics!" else "İstatistikler:"))
        
        self._stats_table = QTableWidget(0, 4)
        self._stats_table.setHorizontalHeaderLabels([
            tr("col_stat") if tr("col_stat") != "!col_stat!" else "İstatistik",
            tr("col_value") if tr("col_value") != "!col_value!" else "Değer",
            tr("col_time") if tr("col_time") != "!col_time!" else "Zaman",
            tr("col_count") if tr("col_count") != "!col_count!" else "Sayı"
        ])
        self._stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._stats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._stats_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._stats_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._stats_table.setMaximumHeight(150)
        stats_layout.addWidget(self._stats_table)
        
        splitter.addWidget(stats_widget)
        splitter.setSizes([500, 150])
        
        layout.addWidget(splitter)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton(tr("btn_close") if tr("btn_close") != "!btn_close!" else "Kapat")
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _update_address_list(self) -> None:
        """Update the address combo box."""
        current_text = self._address_combo.currentText()
        self._address_combo.clear()
        
        histories = graph_manager.get_all_histories()
        for history in histories:
            desc = history.description or f"0x{history.address:X}"
            self._address_combo.addItem(f"{desc} ({len(history.data_points)} nokta)", history.address)
        
        # Restore selection
        if current_text:
            index = self._address_combo.findText(current_text)
            if index >= 0:
                self._address_combo.setCurrentIndex(index)
        
        if self._address_combo.count() == 0:
            self._address_combo.addItem(tr("no_tracked_addresses") if tr("no_tracked_addresses") != "!no_tracked_addresses!" else "İzlenen adres yok")
    
    def _on_address_changed(self, index: int) -> None:
        """Handle address selection change."""
        if index < 0:
            return
        
        address = self._address_combo.itemData(index)
        if address:
            history = graph_manager.get_history(address)
            self._graph_widget.set_history(history)
            self._update_stats(history)
    
    def _update_stats(self, history: Optional[ValueHistory]) -> None:
        """Update statistics table."""
        if not history or not history.data_points:
            self._stats_table.setRowCount(0)
            return
        
        data = history.get_data()
        values = [v for _, v in data]
        timestamps = [t for t, _ in data]
        
        stats = [
            (tr("stat_current") if tr("stat_current") != "!stat_current!" else "Güncel", values[-1], "", ""),
            (tr("stat_min") if tr("stat_min") != "!stat_min!" else "Minimum", min(values), "", ""),
            (tr("stat_max") if tr("stat_max") != "!stat_max!" else "Maksimum", max(values), "", ""),
            (tr("stat_avg") if tr("stat_avg") != "!stat_avg!" else "Ortalama", sum(values) / len(values), "", ""),
            (tr("stat_range") if tr("stat_range") != "!stat_range!" else "Aralık", max(values) - min(values), "", ""),
            (tr("stat_duration") if tr("stat_duration") != "!stat_duration!" else "Süre (sn)", "", max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0, ""),
            (tr("stat_data_points") if tr("stat_data_points") != "!stat_data_points!" else "Veri Noktası", "", "", len(values)),
        ]
        
        self._stats_table.setRowCount(len(stats))
        for row, (name, value, time_val, count) in enumerate(stats):
            self._stats_table.setItem(row, 0, QTableWidgetItem(name))
            if isinstance(value, (int, float)) and value != "":
                self._stats_table.setItem(row, 1, QTableWidgetItem(f"{value:.4f}"))
            else:
                self._stats_table.setItem(row, 1, QTableWidgetItem(str(value)))
            self._stats_table.setItem(row, 2, QTableWidgetItem(f"{time_val:.2f}" if isinstance(time_val, (int, float)) else str(time_val)))
            self._stats_table.setItem(row, 3, QTableWidgetItem(str(count)))
    
    def _refresh_graphs(self) -> None:
        """Refresh graph display."""
        if not self._track_chk.isChecked():
            return
        
        # Update address list in case new addresses were added
        current_count = self._address_combo.count()
        history_count = len(graph_manager.get_all_histories())
        
        if current_count != history_count + (1 if current_count > 0 and self._address_combo.itemData(0) is None else 0):
            self._update_address_list()
        
        # Refresh current graph
        address = self._address_combo.currentData()
        if address:
            history = graph_manager.get_history(address)
            self._graph_widget.set_history(history)
            self._update_stats(history)
    
    def _on_export_csv(self) -> None:
        """Export current history to CSV."""
        address = self._address_combo.currentData()
        if not address:
            QMessageBox.information(self, "Bilgi", "Dışa aktarılacak adres yok.")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("btn_export_csv") if tr("btn_export_csv") != "!btn_export_csv!" else "CSV Dışa Aktar",
            f"graph_0x{address:X}.csv",
            "CSV Files (*.csv)"
        )
        
        if path:
            if graph_manager.export_csv(address, path):
                QMessageBox.information(self, "Başarılı", f"Veriler dışa aktarıldı:\n{path}")
            else:
                QMessageBox.critical(self, "Hata", "Dışa aktarma başarısız.")
    
    def _on_clear_history(self) -> None:
        """Clear history for selected address."""
        address = self._address_combo.currentData()
        if not address:
            return
        
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            tr("dlg_confirm") if tr("dlg_confirm") != "!dlg_confirm!" else "Onay",
            tr("msg_clear_confirm") if tr("msg_clear_confirm") != "!msg_clear_confirm!" else "Bu adresin geçmişi silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            graph_manager.remove_history(address)
            self._update_address_list()
            self._graph_widget.set_history(None)
            self._stats_table.setRowCount(0)
    
    def closeEvent(self, event) -> None:
        """Clean up on close."""
        self._refresh_timer.stop()
        event.accept()


def show_graph_dialog(parent=None) -> None:
    """Show the graph dialog."""
    dialog = GraphDialog(parent)
    dialog.exec()
