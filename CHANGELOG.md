# Changelog

## v1.2.0 - 2026-11-22

### Interface
- Redesigned the main window as a resizable three-pane workbench: scan rail,
  results workspace, and pointer inspector.
- Added a compact command bar with process state, attach/detach, refresh rate,
  theme, and help controls.
- Rebuilt the results/watchlist layout: readable counts, paging, search,
  empty states, and non-overlapping bulk actions.
- Removed the duplicated pointer title, clipped labels, broken emoji glyphs,
  and fixed-width layouts.
- Added shared dark/light design tokens, focus/hover/selected states, custom
  dock title bars, and a styled settings dialog.
- Kept native-aspect icons and monospace text only for addresses and values.

### Packaging
- Portable onedir build: 93.2 MB, frozen smoke OK.
- Single-file EXE: 48.5 MB, frozen smoke OK.
- Portable ZIP: 34.9 MB, extraction + smoke OK.
- Version bumped to 1.2.0; native core remains 0.2.0.

### Verification
- 121 Python tests passed.
- 20 Rust tests passed.
- GUI smoke: attach, first scan, detach, close.
- Dark and light layouts checked at 1440x900.

## v1.1.0 - 2026-11-22

### Fixed
- Speedhack: corrected 64-bit `VirtualAllocEx` return type (address truncation).
- Speedhack: steal instruction-aligned bytes instead of a fixed 14-byte prefix
  that split ntdll's 8-byte `test` instruction.
- UIV UNCHANGED: trim preallocated result buffers when a chunk disappears.
- Cross-process tests no longer fail because of Unicode output encoding.

### Performance
- UIV UNCHANGED peak memory: ~4 GB -> ~1.70 GiB (134M hits).
- `scanner.py`: 1707 lines -> 760 lines; first/next scan split into modules.
- Columnar result storage and preallocated UIV buffers remain in use.

### Security / integrity
- Native module version + SHA-256 sidecar verification.
- Existing S1-S8 hardening retained: trainer validation, least-privilege handle,
  opt-in code injection, bounded watchlist import, handle liveness, per-user UIV
  temp directory, INFO default logging.

### Tests / packaging
- 121 Python tests, 20 Rust tests, live HWBP and speedhack integration.
- Portable onedir build (93.2 MB) and single-file exe (48.5 MB); both pass the
  frozen `--smoke-test`.
