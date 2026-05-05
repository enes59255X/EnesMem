# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-05-05

### Added - Phase 3 (Expert Features)
- Memory Map Viewer with filtering and export
- Advanced Scanning Filters (alignment, range, module)
- Code Injection Framework (low-level memory patching)

### Added - Phase 2 (Professional Tools)
- Value Graph System for tracking value changes over time
- CT File Import/Export (Cheat Engine compatibility)
- Lua Scripting Framework with memory access bindings
- Compare/Diff Scanning for finding changed values

### Added - Phase 1 (Advanced Features)
- Global Hotkey System with configurable shortcuts
- Watchlist Groups and Folder System
- AOB (Array of Bytes) Advanced Scanning

### Core Features
- Process enumeration and attachment
- Multi-type memory read/write (Int8/16/32/64, Float, Double, String, Bytes)
- First Scan and Next Scan with multiple modes (Exact, Bigger, Smaller, etc.)
- Value freezing with background thread
- Watchlist with live refresh
- Pointer chain resolution (manual and automatic)
- Memory Viewer (Hex Editor) with virtualized scrolling
- Unknown Initial Value (UIV) scanning
- Float tolerance scanning
- String search (UTF-8, UTF-16LE)
- Dark mode PyQt6 GUI
- Turkish and English language support

### Technical
- Pure ctypes implementation (no pymem dependency)
- 64/32-bit process support
- Bulk memory reads with memoryview optimization
- QThread-based scanning (non-blocking UI)
- Comprehensive test suite (22+ tests)

## [0.9.0] - 2025-04-XX

### Added
- Initial release with core memory scanning functionality
- Basic GUI with PyQt6
- Process attachment
- First/Next scan implementation

### Notes
- Development version
- Windows 10/11 support only
