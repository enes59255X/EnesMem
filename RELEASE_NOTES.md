# EnesMem v1.0.0 - Sürüm Notları

## 🚀 Quick Start

**Users:**
1. Download `EnesMem-v1.0.0.zip` from GitHub Releases
2. Extract ZIP to any folder
3. Double-click `EnesMem.exe` (Run as Administrator)
4. Done! No installation needed.

**Developers:**
```bash
git clone https://github.com/enes59255X/EnesMem.git
cd EnesMem
pip install -r requirements.txt
python main.py
```

## 📋 Features

### Core Features
- ✅ Memory scanning (First/Next scan)
- ✅ Multiple data types (Int8/16/32/64, Float, Double, String, Bytes)
- ✅ Scan modes (Exact, Bigger, Smaller, Increased, Decreased, Changed, Unchanged, Unknown)
- ✅ Value freezing with background thread
- ✅ Memory viewer with hex display
- ✅ Pointer chain resolution (manual and automatic)
- ✅ Watchlist management

### Phase 1 - Advanced Features
- ✅ Global hotkey system
- ✅ Watchlist groups and folders
- ✅ AOB (Array of Bytes) scanning
- ✅ Modern PyQt6 dark UI

### Phase 2 - Professional Tools
- ✅ Value graph system with CSV export
- ✅ Cheat Engine CT file import/export
- ✅ Lua scripting engine with templates
- ✅ Compare/Diff scanning between snapshots

### Phase 3 - Expert Features
- ✅ Memory map viewer with filtering
- ✅ Advanced scan filters (alignment, range, module, protection)
- ✅ Code injection framework

### Internationalization
- ✅ Turkish language support
- ✅ English language support
- ✅ Easy language switching

## 🛡️ Technical Details

- **Framework:** PyQt6 (modern, native widgets)
- **Memory Access:** Pure ctypes (no pymem dependency)
- **Performance:** 4MB bulk reads with memoryview optimization
- **Threading:** Non-blocking UI with QThread
- **Architecture:** 64/32-bit compatible with automatic detection
- **Security:** UAC elevation for admin privileges

## 🔧 Requirements

- **OS:** Windows 10/11 (64-bit)
- **Python:** 3.11+ (for development)
- **Privileges:** Administrator (required for memory access)

## 📁 File Structure

```
EnesMem/
├── main.py                 # Entry point with UAC
├── requirements.txt          # Runtime dependencies
├── README.md               # Turkish documentation
├── README_EN.md            # English documentation
├── TUTORIAL.md             # Usage guide (TR/EN)
├── LICENSE                 # MIT license
├── .gitignore              # Git rules
│
├── core/                  # Core engine (13 modules)
├── gui/                   # User interface (12 modules)
├── utils/                  # Utilities (6 modules)
├── resources/lang/         # Languages (2 files)
└── data/                   # User data (gitignored)
```

## ⚠️ Important Notes

### For Users
- **Always run as Administrator** - Required for memory access
- **Antivirus warnings** - May trigger alerts (false positives)
- **Single file** - No installation needed, portable

### For Developers
- **Clean repository** - Only source code, no build artifacts
- **No dependencies** - All packages in requirements.txt
- **Pure Python** - No compiled binaries, just source

## 🎯 What's Next?

### v1.0.1 (Planned)
- [ ] UPX compression for smaller EXE
- [ ] Memory scan performance improvements
- [ ] Additional scan filters

### v1.1.0 (Future)
- [ ] Plugin system
- [ ] Network scanning capabilities
- [ ] Advanced code injection features

## 📞 Support

- **Issues:** https://github.com/enes59255X/EnesMem/issues
- **Documentation:** See TUTORIAL.md
- **Community:** Contributions welcome via Pull Requests

---

**EnesMem v1.0.0** - Professional memory scanner for Windows
*Built with ❤️ by EnesMem*
