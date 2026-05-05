# EnesMem — Python Memory Scanner / Editor

> A production-grade Cheat Engine clone built with Python + PyQt6.
> Pure `ctypes` — no pymem dependency.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.1-brightgreen.svg)](CHANGELOG.md)

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

## Acknowledgments

- Inspired by [Cheat Engine](https://cheatengine.org/) by Dark Byte
- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- Uses [pynput](https://github.com/moses-palmer/pynput) for global hotkeys

---

## Legal Notice

This tool is for educational purposes and authorized use only.
Do not use on software you do not own or have permission to analyze.

**Use at your own risk.** The authors are not responsible for any damage or legal issues caused by the use of this software.
