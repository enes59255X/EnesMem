# EnesMem v1.2.0 - Python Memory Scanner / Editor

> A production-grade Cheat Engine alternative built with Python + PyQt6.
> Pure `ctypes`; no pymem or external runtime required.

## Download

| File | Size | Description |
|---|---:|---|
| **EnesMem.exe** | 48.5 MB | Single file; no installation |
| **EnesMem-1.2.0-win64.zip** | 34.9 MB | Portable folder; faster launch |

The single-file exe is self-contained. If you use the zip, extract it and run
`EnesMem\EnesMem.exe`; keep the `_internal` folder next to the exe.

> **Administrator:** Elevation is not required for same-user targets. Use
> **Run as administrator** for protected or elevated processes.

## Highlights

- Process enumeration and attachment
- Int8/16/32/64, UInt, Float, Double, String and Bytes read/write
- First scan, next scan, AOB/wildcard and unknown-value (UIV) scans
- Exact, Bigger, Smaller, Between, Increased, Decreased, Changed, Unchanged,
  Increased/Decreased By and Float tolerance modes
- Value freezing, live watchlist, pointer-chain resolution
- Hex and x64 assembly memory viewer
- "What writes here" hardware breakpoints
- Speedhack (NtDelayExecution detour)
- Modern dark/light workspace, Turkish/English UI, UAC elevation

## v1.2.0 interface refresh

- Resizable three-pane workbench: scan rail, results workspace, pointer inspector.
- Command bar carries process state, attach/detach, refresh rate, theme and help.
- Results search, paging, counts, empty state and watchlist actions no longer
  overlap or clip.
- Removed the duplicated pointer-panel title and fixed clipped labels.
- Shared design tokens for dark and light themes; monospace only for addresses.
- Replaced broken emoji glyphs with readable labels and standard Qt icons.

## Quick start

1. Run `EnesMem\EnesMem.exe`.
2. Select a target with **Attach**.
3. Choose a type and value, then run **First Scan** (F5).
4. Change the value in the game; narrow with **Next Scan** (F6).
5. Double-click a result to add it to the watchlist.

## Verification

- 121 Python tests, 20 Rust tests
- GUI smoke: attach, scan, detach, close
- Frozen onedir and onefile `--smoke-test` pass
