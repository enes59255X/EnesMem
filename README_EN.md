# EnesMem v1.1.0 — Python Memory Scanner / Editor

> A production-grade Cheat Engine alternative built with Python + PyQt6.
> Pure `ctypes`; no pymem or external runtime required.

## Download

| File | Size | Description |
|---|---:|---|
| **EnesMem.exe** | 48.5 MB | Single file; no installation |
| **EnesMem-1.1.0-win64.zip** | 34.9 MB | Portable folder; faster launch |

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
- Dark theme, Turkish/English UI, UAC elevation

## v1.1.0 changes

- Fixed two real speedhack bugs: truncated 64-bit `VirtualAllocEx` address and
  a hook that split an ntdll instruction. Added a live target test.
- UIV UNCHANGED peak memory reduced from ~4 GB to **~1.70 GiB**.
- `scanner.py` reduced from 1707 lines to **760**; first/next scan moved into
  focused modules.
- 121 Python tests and 20 Rust tests; live HWBP/speedhack coverage.
- Native `.pyd` version + SHA-256 integrity check.
- Single-file and portable-folder builds; both pass the frozen smoke test.

## Verification

- Python: **121/121 passed**
- Rust: **20/20 passed**
- GUI smoke: attach → scan → detach → close **OK**
- Packages: single file and folder **OK**

SHA-256:

```text
09b2339c0e44dd69f26d31c09ede888418025e93961f81c32ede552002e63ff7  EnesMem-1.1.0-win64-onefile.exe
58505c292432e6ffc2b7be1614f146a73060a54aec3e4137dad7aadba0086033  EnesMem-1.1.0-win64.zip
```

## License

MIT. See `LICENSE`.

This tool is for educational and authorized testing only. Do not use it on
software you do not own or have permission to analyze.
