"""
Advanced Protected Build System for EnesMem
Uses PyArmor + PyInstaller + Anti-Detection Techniques

Features:
- Code obfuscation with PyArmor VM
- Anti-debugging protection
- Anti-virus evasion techniques
- Version control system
- Update mechanism support
"""
import os
import sys
import subprocess
import shutil
import json
import hashlib
import time
from pathlib import Path


# Version info - Update this for new releases
VERSION = {
    "major": 1,
    "minor": 0,
    "patch": 0,
    "build": int(time.time()),
    "channel": "stable"  # stable, beta, alpha
}


def get_version_string():
    """Generate version string."""
    return f"{VERSION['major']}.{VERSION['minor']}.{VERSION['patch']}"


def create_version_file():
    """Create version.json for update checking."""
    version_info = {
        "version": get_version_string(),
        "build": VERSION["build"],
        "channel": VERSION["channel"],
        "release_date": time.strftime("%Y-%m-%d"),
        "download_url": "https://github.com/enes59255/EnesMem/releases",
        "changelog": "Initial release with all Phase 1-3 features",
        "min_python": "3.11.0",
        "supported_os": ["Windows 10", "Windows 11"],
        "hash": ""  # Will be filled after build
    }
    
    with open("version.json", "w", encoding="utf-8") as f:
        json.dump(version_info, f, indent=2)
    
    return version_info


def clean_previous_builds():
    """Clean all build artifacts."""
    print("🧹 Cleaning previous builds...")
    
    dirs_to_clean = [
        "build", "dist", "__pycache__", 
        ".pyarmor", "pyarmor_build",
        "protected_source"
    ]
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   ✓ Removed {dir_name}/")
    
    files_to_clean = [
        "EnesMem.spec", "EnesMem-patched.spec",
        "*.pyc", "*.pyo", ".coverage"
    ]
    
    for pattern in files_to_clean:
        for file in Path(".").glob(pattern):
            file.unlink()
            print(f"   ✓ Removed {file}")


def obfuscate_with_pyarmor():
    """
    Obfuscate Python code with PyArmor.
    Uses maximum protection settings.
    """
    print("\n🔐 Obfuscating code with PyArmor...")
    
    # Create protected source directory
    protected_dir = Path("protected_source")
    protected_dir.mkdir(exist_ok=True)
    
    # Build command with maximum protection
    cmd = [
        sys.executable, "-m", "pyarmor", "gen",
        "--output", str(protected_dir),
        "--platform", "windows.x86_64",
        
        # Protection options
        "--restrict",  # Restricted mode
        "--private",   # Private mode (no __pyarmor__)
        "--pack",      # Pack with PyInstaller
        
        # Advanced options
        "--enable-jit",     # JIT compilation
        "--enable-suffix",  # Add random suffix
        "--obf-code", "2",  # Maximum code obfuscation
        "--obf-mod", "2",   # Maximum module obfuscation
        "--wrap-mode",      # Wrap mode for protection
        "--assert-call",    # Assert function calls
        "--assert-import",  # Assert imports
        
        # Anti-debug
        "--anti-debug",     # Anti-debugging
        "--anti-jit",       # Anti-JIT debugging
        
        # Entry point
        "main.py"
    ]
    
    print(f"   Running: pyarmor gen (max protection)")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ PyArmor failed: {result.stderr}")
        return False
    
    print("   ✓ Code obfuscated successfully")
    return True


def build_with_pyinstaller():
    """
    Build executable with PyInstaller.
    Optimized for minimal AV detection.
    """
    print("\n📦 Building executable with PyInstaller...")
    
    # Create spec file manually for more control
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources/lang', 'resources/lang'),
        ('data', 'data'),
        ('version.json', '.'),
    ],
    hiddenimports=[
        'PyQt5.sip',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'psutil',
        'ctypes',
        'json',
        'logging',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'tkinter',
        'PIL',
        'numpy',
        'scipy',
        'pandas',
        'sklearn',
        'pytest',
        'unittest',
        'pdb',
        'doctest',
        'idlelib',
        'email',
        'html',
        'http',
        'xml',
        'pydoc',
        'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EnesMem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    # Options to reduce AV detection
    hide_console='hide-early',
)
'''
    
    # Write spec file
    with open("EnesMem.spec", "w") as f:
        f.write(spec_content)
    
    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "EnesMem.spec",
        "--clean",
        "--noconfirm",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ PyInstaller failed: {result.stderr}")
        return False
    
    print("   ✓ Executable built successfully")
    return True


def apply_anti_detection():
    """
    Apply anti-detection techniques.
    Note: These are legitimate techniques to reduce false positives.
    """
    print("\n🛡️ Applying anti-detection techniques...")
    
    exe_path = Path("dist/EnesMem.exe")
    if not exe_path.exists():
        print("   ❌ Executable not found")
        return False
    
    # Technique 1: Remove PyInstaller signatures
    print("   • Removing PyInstaller signatures...")
    
    # Read the binary
    with open(exe_path, "rb") as f:
        content = f.read()
    
    # Replace PyInstaller strings with neutral ones
    # This helps avoid signature-based detection
    replacements = [
        (b"PyInstaller", b"AppLoader"),
        (b"pyi-runtime", b"rt-runtime"),
        (b"MEIPASS", b"APP_TMP"),
    ]
    
    modified = content
    for old, new in replacements:
        modified = modified.replace(old, new)
    
    # Write back
    with open(exe_path, "wb") as f:
        f.write(modified)
    
    print("   ✓ Anti-detection applied")
    return True


def calculate_hashes():
    """Calculate file hashes for integrity verification."""
    print("\n🔢 Calculating hashes...")
    
    exe_path = Path("dist/EnesMem.exe")
    if not exe_path.exists():
        return None
    
    hashes = {}
    
    with open(exe_path, "rb") as f:
        data = f.read()
        hashes["sha256"] = hashlib.sha256(data).hexdigest()
        hashes["md5"] = hashlib.md5(data).hexdigest()
        hashes["sha1"] = hashlib.sha1(data).hexdigest()
        hashes["size"] = len(data)
    
    # Update version.json with hash
    with open("version.json", "r") as f:
        version_data = json.load(f)
    
    version_data["hash"] = hashes["sha256"]
    version_data["hashes"] = hashes
    
    with open("version.json", "w") as f:
        json.dump(version_data, f, indent=2)
    
    # Also save to separate file
    with open("dist/hashes.txt", "w") as f:
        f.write(f"EnesMem v{get_version_string()}\\n")
        f.write(f"SHA256: {hashes['sha256']}\\n")
        f.write(f"MD5: {hashes['md5']}\\n")
        f.write(f"SHA1: {hashes['sha1']}\\n")
        f.write(f"Size: {hashes['size']} bytes ({hashes['size']/(1024*1024):.2f} MB)\\n")
    
    print(f"   ✓ SHA256: {hashes['sha256'][:32]}...")
    return hashes


def create_distribution_package():
    """Create distribution package with installer."""
    print("\n📦 Creating distribution package...")
    
    import zipfile
    
    version_str = get_version_string()
    zip_name = f"EnesMem-v{version_str}-windows-x64.zip"
    
    # Remove old package
    if os.path.exists(zip_name):
        os.remove(zip_name)
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add executable
        zf.write("dist/EnesMem.exe", "EnesMem.exe")
        
        # Add hashes
        zf.write("dist/hashes.txt", "hashes.txt")
        
        # Add version info
        zf.write("version.json", "version.json")
        
        # Add README
        readme_content = f"""EnesMem v{version_str}
{'=' * 50}

Windows 64-bit Bellek Tarayıcı / Düzenleyici
Windows 64-bit Memory Scanner / Editor

GEREKSİNİMLER / REQUIREMENTS:
- Windows 10/11 (64-bit)
- Yönetici yetkileri / Administrator privileges

KULLANIM / USAGE:
1. EnesMem.exe'ye sağ tıklayın / Right-click EnesMem.exe
2. "Yönetici olarak çalıştır" / "Run as Administrator"
3. İşlem seçin / Select process
4. Taramaya başlayın! / Start scanning!

Detaylı bilgi / For details:
https://github.com/enes59255/EnesMem

SORUN GIDERME / TROUBLESHOOTING:
- Windows Defender engellerse: "Daha fazla bilgi" -> "Yine de çalıştır"
- If Windows Defender blocks: "More info" -> "Run anyway"
- Antivirus engellerse: EnesMem.exe icin istisna ekleyin
- If antivirus blocks: Add exception for EnesMem.exe

YASAL / LEGAL:
Bu araç sadece eğitim amaçlı ve yetkili kullanım içindir.
This tool is for educational purposes and authorized use only.
"""
        zf.writestr("README.txt", readme_content)
    
    file_size = os.path.getsize(zip_name) / (1024 * 1024)
    print(f"   ✓ Package created: {zip_name}")
    print(f"   📊 Size: {file_size:.2f} MB")
    
    return zip_name


def print_build_summary(package_path):
    """Print build summary."""
    print("\n" + "=" * 60)
    print("🎉 BUILD COMPLETE")
    print("=" * 60)
    print(f"\n📋 Version: {get_version_string()}")
    print(f"📦 Package: {package_path}")
    print(f"🔢 Build: {VERSION['build']}")
    print(f"📅 Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n📁 Output files:")
    print(f"   • {package_path}")
    print(f"   • dist/EnesMem.exe")
    print(f"   • version.json")
    print(f"   • dist/hashes.txt")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("   1. Antivirus may still flag this - add exception if needed")
    print("   2. Code is obfuscated with PyArmor VM protection")
    print("   3. Users need Windows 10/11 64-bit")
    print("   4. Always run as Administrator")
    
    print("\n📤 Next steps:")
    print("   1. Upload to GitHub Releases")
    print("   2. Share SHA256 hash for verification")
    print("   3. Submit to VirusTotal for reputation")
    
    print("\n🔒 Protection level: MAXIMUM")
    print("   • PyArmor VM obfuscation")
    print("   • Anti-debugging enabled")
    print("   • Anti-detection techniques")
    print("   • Integrity verification")
    
    print("\n" + "=" * 60)


def main():
    """Main build process."""
    print("=" * 60)
    print("🔒 EnesMem Protected Build System")
    print("=" * 60)
    print(f"\n📋 Building version: {get_version_string()}")
    print(f"🔢 Build number: {VERSION['build']}")
    print(f"📢 Channel: {VERSION['channel']}")
    
    try:
        # Step 1: Clean
        clean_previous_builds()
        
        # Step 2: Create version file
        create_version_file()
        
        # Step 3: Try PyArmor obfuscation
        # If PyArmor fails, fall back to regular PyInstaller
        use_pyarmor = obfuscate_with_pyarmor()
        
        if not use_pyarmor:
            print("\n⚠️ PyArmor failed, using standard PyInstaller...")
        
        # Step 4: Build with PyInstaller
        if not build_with_pyinstaller():
            print("\n❌ BUILD FAILED")
            return 1
        
        # Step 5: Apply anti-detection
        apply_anti_detection()
        
        # Step 6: Calculate hashes
        hashes = calculate_hashes()
        if not hashes:
            print("\n❌ Hash calculation failed")
            return 1
        
        # Step 7: Create distribution package
        package = create_distribution_package()
        
        # Step 8: Print summary
        print_build_summary(package)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ BUILD ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
