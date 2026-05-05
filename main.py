"""
main.py — EnesMem entry point.
Requests UAC elevation if not running as administrator.
"""
import sys
import ctypes
import subprocess


def _is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def _elevate() -> None:
    """Re-launch this script with UAC elevation."""
    params = " ".join(f'"{a}"' for a in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    sys.exit(0)


def main() -> None:
    if not _is_admin():
        reply = _ask_elevation()
        if reply:
            _elevate()
        # Continue without elevation — some processes will be inaccessible

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont

    app = QApplication(sys.argv)
    app.setApplicationName("EnesMem")
    app.setOrganizationName("EnesMem")

    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    from gui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def _ask_elevation() -> bool:
    """Ask user if they want to run as admin (without GUI dependency)."""
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        _tmp = QApplication.instance() or QApplication(sys.argv)
        reply = QMessageBox.question(
            None,
            "Administrator Privileges Required",
            "EnesMem needs Administrator privileges to read/write process memory.\n\n"
            "Restart as Administrator?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes
    except Exception:
        return False


if __name__ == "__main__":
    main()
