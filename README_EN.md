# EnesMem — Python Memory Scanner / Editor

> A production-grade Cheat Engine clone built with Python + PyQt6.
> Pure `ctypes` — no pymem dependency.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](CHANGELOG.md)

🇹🇷 [Türkçe için buraya tıklayın](README.md)

---

## Features

| Feature | Status | Phase |
|---------|--------|-------|
| Process enumeration & attachment | ✅ | Core |
| Typed memory read/write (Int8/16/32/64, Float, Double, String, Bytes) | ✅ | Core |
| First Scan (all memory regions) | ✅ | Core |
| Next Scan (narrow previous results) | ✅ | Core |
| Scan modes: Exact, Bigger, Smaller, Increased, Decreased, Changed, Unchanged, Unknown | ✅ | Core |
| Value freezing (background thread) | ✅ | Core |
| Watchlist with live refresh | ✅ | Core |
| Pointer chain resolution | ✅ | Core |
| Dark mode PyQt6 GUI | ✅ | Core |
| UAC elevation prompt | ✅ | Core |
| **Phase 1 - Advanced Features** | | |
| Global Hotkey System | ✅ | Phase 1 |
| Watchlist Groups & Folders | ✅ | Phase 1 |
| AOB Advanced Scanning | ✅ | Phase 1 |
| **Phase 2 - Professional Tools** | | |
| Value Graph System | ✅ | Phase 2 |
| CT File Import/Export | ✅ | Phase 2 |
| Lua Scripting Framework | ✅ | Phase 2 |
| Compare/Diff Scanning | ✅ | Phase 2 |
| **Phase 3 - Expert Features** | | |
| Memory Map Viewer | ✅ | Phase 3 |
| Advanced Scanning Filters | ✅ | Phase 3 |
| Code Injection Framework | ✅ | Phase 3 |

---

## Requirements

- Windows 10/11 (64-bit)
- Python 3.11+
- Administrator privileges (required for `ReadProcessMemory`)

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run as Administrator
python main.py
```

> **Important:** Always run as Administrator. Without it, you can only scan
> processes owned by your current user account.

---

## Running Tests

```bash
# Requires Administrator — open an elevated terminal first
python -m pytest tests/ -v
```

---

## Project Structure

```
EnesMem/
├── main.py                    # Entry point (UAC elevation)
├── requirements.txt           # Dependencies
├── TUTORIAL.md                # Detailed user guide (TR/EN)
├── walkthrough.md             # Feature walkthrough
├── README.md                  # Turkish README
│
├── core/                      # Core engine modules
│   ├── process_manager.py     # Process enumeration, handle lifecycle
│   ├── memory_io.py           # Read/write + region enumeration
│   ├── scanner.py             # First/Next scan engine
│   ├── freezer.py             # Background freeze thread
│   ├── pointer_scanner.py     # Pointer chain resolution
│   ├── aob_scanner.py         # AOB/Pattern scanning
│   ├── hotkey_manager.py      # Global hotkey system
│   ├── value_graph.py         # Value history tracking
│   ├── ct_manager.py          # Cheat Engine CT file support
│   ├── lua_engine.py          # Lua scripting framework
│   ├── compare_scanner.py     # Compare/Diff scanning
│   ├── memory_map.py          # Memory region mapping
│   ├── code_injector.py       # Code injection framework
│   └── advanced_filters.py    # Advanced scanning filters
│
├── gui/                       # UI components
│   ├── main_window.py         # Root QMainWindow
│   ├── process_selector.py    # Process selection dialog
│   ├── scan_panel.py          # Scan controls (left panel)
│   ├── results_table.py       # Found addresses + watchlist
│   ├── pointer_panel.py       # Pointer scanner dock
│   ├── memory_viewer.py       # Hex memory viewer
│   ├── memory_map_dialog.py   # Memory map viewer
│   ├── graph_dialog.py        # Value graph viewer
│   ├── aob_dialog.py          # AOB scanner dialog
│   ├── hotkey_dialog.py       # Hotkey configuration
│   ├── settings_dialog.py     # Settings panel
│   └── watchlist_groups.py    # Group management
│
├── utils/                     # Utilities
│   ├── winapi.py              # Pure ctypes WinAPI declarations
│   ├── converters.py          # bytes ↔ typed values
│   ├── logger.py              # Structured logging
│   ├── patterns.py            # Enums, constants
│   ├── i18n.py                # Internationalization (TR/EN)
│   ├── settings.py            # Settings manager
│   └── watchlist_groups.py    # Group data management
│
├── resources/                 # Assets
│   └── lang/                  # Language files
│       ├── tr.json            # Turkish translations
│       └── en.json            # English translations
│
├── data/                      # User data (gitignored)
│   └── watchlist_groups.json  # Saved groups
│
└── tests/                     # Test suite
    ├── test_memory_io.py
    ├── test_scanner.py
    ├── test_converters.py
    ├── test_watchlist_groups.py
    └── test_performance.py
```

---

## Architecture Notes

- **Pure ctypes**: All Windows API calls go through `utils/winapi.py`. No pymem.
- **Bulk reads**: Scanner reads memory in 4MB chunks using `memoryview` for zero-copy slicing.
- **QThread**: Scan runs off the main thread. Progress is reported via Qt signals.
- **Single freeze thread**: One daemon thread writes all frozen addresses at 50ms intervals.
- **64/32-bit aware**: Detects target bitness via `IsWow64Process`. Pointer reads adjust automatically.

---

## Screenshots

> _Screenshots will be added here showing the main interface and key features._

<!-- 
![Main Window](screenshots/main_window.png)
![Memory Viewer](screenshots/memory_viewer.png)
![Pointer Scanner](screenshots/pointer_scanner.png)
![Value Graph](screenshots/value_graph.png)
-->

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + O` | Attach to Process |
| `Ctrl + Q` | Exit |
| `Ctrl + P` | Pointer Scanner |
| `Ctrl + B` | AOB Scanner |
| `Ctrl + G` | Value Graphs |
| `Ctrl + M` | Memory Map |
| `Ctrl + H` | Global Hotkeys |
| `Enter` | First/Next Scan |
| `Delete` | Delete Selected Address |

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone the repo
git clone https://github.com/enes59255/EnesMem.git
cd EnesMem

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-cov

# Run tests (requires Administrator)
python -m pytest tests/ -v
```

---

## Roadmap

- [x] Core memory scanning
- [x] Pointer scanning
- [x] AOB scanning
- [x] Global hotkeys
- [x] Value graphs
- [x] CT file support
- [x] Lua scripting
- [x] Compare scanning
- [x] Memory map viewer
- [ ] Assembly code injection GUI
- [ ] Disassembler integration
- [ ] Debugger integration
- [ ] Plugin system

---

## Acknowledgments

- Inspired by [Cheat Engine](https://cheatengine.org/) by Dark Byte
- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- Uses [pynput](https://github.com/moses-palmer/pynput) for global hotkeys

---

## Legal Notice

This tool is for educational purposes and authorized use only.
Do not use on software you do not own or have permission to analyze.

**Use at your own risk.** The authors are not responsible for any damage or legal issues caused by the use of this software.
