# EnesMem — Python Memory Scanner / Editor

> A production-grade Cheat Engine clone built with Python + PyQt6.
> Pure `ctypes` — no pymem dependency.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](CHANGELOG.md)

🇹🇷 [Türkçe için buraya tıklayın](README.md)

---

## Download

[📥 Download EnesMem v1.0.0 (Releases)](https://github.com/enes59255X/EnesMem/releases)

---

## Features

- ✅ Process enumeration & attachment
- ✅ Typed memory read/write (Int8/16/32/64, Float, Double, String, Bytes)
- ✅ First Scan & Next Scan
- ✅ Scan modes: Exact, Bigger, Smaller, Increased, Decreased, Changed, Unchanged, Unknown
- ✅ Value freezing (background thread)
- ✅ Watchlist with live refresh
- ✅ Pointer chain resolution
- ✅ Dark/Light theme support
- ✅ Global Hotkey System
- ✅ AOB Advanced Scanning
- ✅ Value Graph System
- ✅ CT File Import/Export
- ✅ Lua Scripting Framework
- ✅ Memory Map Viewer

---

## Requirements

- Windows 10/11 (64-bit)
- Administrator privileges

---

## Installation & Usage

1. Download `EnesMem.exe` from **Releases**
2. Run as Administrator (Right click → Run as administrator)
3. Select process → Scan → Edit values

> **Important:** Always run as Administrator. Without it, you can only scan processes owned by your current user account.

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
