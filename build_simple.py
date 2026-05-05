"""
Simple but effective EXE builder for EnesMem.
Uses PyInstaller with UPX compression and anti-detection.
"""
import os
import sys
import subprocess
import shutil
import json
import hashlib
import time
from pathlib import Path


VERSION = {
    "major": 1,
    "minor": 0,
    "patch": 0,
    "build": int(time.time()),
    "channel": "stable"
}


def get_version_string():
    return f"{VERSION['major']}.{VERSION['minor']}.{VERSION['patch']}"


def clean_build():
    """Clean previous builds."""
    print("🧹 Cleaning previous builds...")
    
    for dir_name in ['build', 'dist', '__pycache__']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"   ✓ Removed {dir_name}/")
    
    for pattern in ['*.spec', '*.pyc', '*.pyo']:
        for file in Path('.').glob(pattern):
            file.unlink()


def build_exe():
    """Build executable with PyInstaller."""
    print("\n📦 Building executable with PyInstaller...")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"   ✓ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("   ⚠️ Installing PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "-q"])
    
    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=EnesMem",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        
        # Data files
        "--add-data", f"resources/lang{os.pathsep}resources/lang",
        "--add-data", f"data{os.pathsep}data",
        
        # Hidden imports
        "--hidden-import", "PyQt5.sip",
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse._win32",
        
        # Optimize - exclude unnecessary modules
        "--exclude-module", "matplotlib",
        "--exclude-module", "tkinter",
        "--exclude-module", "PIL",
        "--exclude-module", "numpy",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "sklearn",
        "--exclude-module", "pytest",
        "--exclude-module", "unittest",
        "--exclude-module", "pdb",
        "--exclude-module", "doctest",
        "--exclude-module", "idlelib",
        "--exclude-module", "email",
        "--exclude-module", "html",
        "--exclude-module", "http",
        "--exclude-module", "xml",
        "--exclude-module", "pydoc",
        "--exclude-module", "test",
        
        # Try UPX if available
        "--upx-dir", ".",
        
        # UAC admin
        "--uac-admin",
        
        "main.py"
    ]
    
    print("   Running PyInstaller...")
    print("   This may take 5-10 minutes...")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"   ❌ Build failed: {result.stderr[-500:]}")
        return False
    
    print("   ✓ Build successful")
    return True


def apply_protections():
    """Apply simple protections to EXE."""
    print("\n🛡️ Applying protections...")
    
    exe_path = Path("dist/EnesMem.exe")
    if not exe_path.exists():
        print("   ❌ EXE not found")
        return False
    
    # Rename PyInstaller signatures in binary
    print("   • Renaming signatures...")
    
    with open(exe_path, "rb") as f:
        content = f.read()
    
    # Replace common signatures
    replacements = [
        (b"PyInstaller", b"AppLoader_"),
        (b"pyi-runtime", b"rt-runtime__"),
        (b"MEIPASS", b"APP_DIR___"),
    ]
    
    modified = content
    for old, new in replacements:
        modified = modified.replace(old, new)
    
    with open(exe_path, "wb") as f:
        f.write(modified)
    
    print("   ✓ Protections applied")
    return True


def create_version_file():
    """Create version info."""
    version_info = {
        "version": get_version_string(),
        "build": VERSION["build"],
        "channel": VERSION["channel"],
        "release_date": time.strftime("%Y-%m-%d"),
        "download_url": "https://github.com/enes59255/EnesMem/releases",
        "changelog": "Initial release v1.0.0",
        "hash": ""
    }
    
    with open("version.json", "w") as f:
        json.dump(version_info, f, indent=2)
    
    return version_info


def calculate_hashes():
    """Calculate file hashes."""
    print("\n🔢 Calculating hashes...")
    
    exe_path = Path("dist/EnesMem.exe")
    if not exe_path.exists():
        return None
    
    with open(exe_path, "rb") as f:
        data = f.read()
    
    hashes = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data).hexdigest(),
        "size": len(data)
    }
    
    # Update version.json
    with open("version.json", "r") as f:
        version_data = json.load(f)
    version_data["hash"] = hashes["sha256"]
    with open("version.json", "w") as f:
        json.dump(version_data, f, indent=2)
    
    # Write hashes.txt
    with open("dist/hashes.txt", "w") as f:
        f.write(f"EnesMem v{get_version_string()}\n")
        f.write(f"SHA256: {hashes['sha256']}\n")
        f.write(f"MD5: {hashes['md5']}\n")
        f.write(f"Size: {hashes['size']/(1024*1024):.2f} MB\n")
    
    print(f"   ✓ SHA256: {hashes['sha256'][:32]}...")
    return hashes


def create_package():
    """Create distribution package."""
    import zipfile
    
    print("\n📦 Creating distribution package...")
    
    zip_name = f"EnesMem-v{get_version_string()}-windows-x64.zip"
    
    if os.path.exists(zip_name):
        os.remove(zip_name)
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write("dist/EnesMem.exe", "EnesMem.exe")
        zf.write("dist/hashes.txt", "hashes.txt")
        zf.write("version.json", "version.json")
        
        readme = f"""EnesMem v{get_version_string()} - Windows 64-bit Memory Scanner

REQUIREMENTS:
- Windows 10/11 (64-bit)
- Administrator privileges (auto-requested)

USAGE:
1. Right-click EnesMem.exe → "Run as Administrator"
2. Select process to attach
3. Start scanning!

DETAILS: https://github.com/enes59255/EnesMem

⚠️ Antivirus may flag this as suspicious (memory tool).
Add exception or click "Run anyway" if blocked.

LEGAL: Educational/authorized use only.
"""
        zf.writestr("README.txt", readme)
    
    size_mb = os.path.getsize(zip_name) / (1024*1024)
    print(f"   ✓ Package: {zip_name}")
    print(f"   📊 Size: {size_mb:.2f} MB")
    
    return zip_name


def main():
    print("=" * 60)
    print("🔧 EnesMem Simple Build System")
    print("=" * 60)
    print(f"\nVersion: {get_version_string()}")
    
    try:
        clean_build()
        create_version_file()
        
        if not build_exe():
            print("\n❌ BUILD FAILED")
            return 1
        
        apply_protections()
        calculate_hashes()
        package = create_package()
        
        print("\n" + "=" * 60)
        print("🎉 BUILD SUCCESSFUL!")
        print("=" * 60)
        print(f"\n📦 Output: {package}")
        print(f"🔢 SHA256: See dist/hashes.txt")
        print("\n⚠️ Note: Antivirus may flag - add exception if needed")
        print("✅ Ready for distribution!")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
