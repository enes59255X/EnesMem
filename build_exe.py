"""
Build script for EnesMem executable.
Creates a standalone .exe file with all resources included.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


def clean_build():
    """Remove previous build artifacts."""
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"Removing {dir_name}/...")
            shutil.rmtree(dir_name)
    
    # Remove spec file if exists
    spec_file = 'EnesMem.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)
        print(f"Removing {spec_file}...")


def build_exe():
    """Build the executable using PyInstaller."""
    print("=" * 60)
    print("Building EnesMem Executable")
    print("=" * 60)
    
    # Ensure resources are included
    resources_dir = Path("resources/lang")
    if not resources_dir.exists():
        print("ERROR: resources/lang directory not found!")
        sys.exit(1)
    
    # PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=EnesMem",
        "--onefile",  # Single executable file
        "--windowed",  # No console window
        "--clean",  # Clean PyInstaller cache
        "--noconfirm",  # Overwrite without asking
        
        # Icon (if available)
        # "--icon=resources/icon.ico",
        
        # Add data files (language files)
        "--add-data", f"resources/lang{os.pathsep}resources/lang",
        "--add-data", f"data{os.pathsep}data",
        
        # Hidden imports (if any dynamic imports are missed)
        "--hidden-import", "PyQt5.sip",
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse._win32",
        
        # Optimize
        "--strip",  # Strip symbols (smaller file)
        
        # UAC elevation (manifest)
        "--uac-admin",  # Request administrator privileges
        
        # Main script
        "main.py"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=False)
    
    if result.returncode != 0:
        print("\n❌ BUILD FAILED!")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ BUILD SUCCESSFUL!")
    print("=" * 60)
    print(f"\nExecutable location: dist/EnesMem.exe")
    print(f"File size: {os.path.getsize('dist/EnesMem.exe') / (1024*1024):.1f} MB")
    print("\nNote: This file can be distributed to users.")
    print("Users do NOT need Python installed to run it.")
    print("\n⚠️  WARNING: Antivirus software may flag this as suspicious")
    print("    because it's a memory manipulation tool.")
    print("    You may need to add an exception or sign the executable.")


def create_distribution_package():
    """Create a zip file for distribution."""
    import zipfile
    
    exe_path = "dist/EnesMem.exe"
    if not os.path.exists(exe_path):
        print("ERROR: Executable not found. Run build first.")
        return
    
    zip_name = "EnesMem-v1.0.0-windows-x64.zip"
    
    print(f"\nCreating distribution package: {zip_name}")
    
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(exe_path, "EnesMem.exe")
        zf.writestr("README.txt", """EnesMem v1.0.0
================

Windows 64-bit Memory Scanner/Editor

REQUIREMENTS:
- Windows 10/11 (64-bit)
- Administrator privileges (automatically requested)

USAGE:
1. Right-click EnesMem.exe
2. Select "Run as Administrator"
3. Select a process to attach
4. Start scanning!

For detailed usage instructions, see:
https://github.com/enes59255/EnesMem

TROUBLESHOOTING:
- If Windows Defender blocks: Click "More info" -> "Run anyway"
- If antivirus blocks: Add exception for EnesMem.exe
- "Access Denied": Ensure running as Administrator

LEGAL:
This tool is for educational purposes and authorized use only.
Do not use on software you do not own or have permission to analyze.
""")
    
    print(f"✅ Package created: {zip_name}")
    print(f"Size: {os.path.getsize(zip_name) / (1024*1024):.1f} MB")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Build EnesMem executable")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts first")
    parser.add_argument("--package", action="store_true", help="Create distribution zip after build")
    
    args = parser.parse_args()
    
    if args.clean:
        clean_build()
    
    build_exe()
    
    if args.package:
        create_distribution_package()
