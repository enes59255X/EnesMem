@echo off
chcp 65001 >nul
echo ==========================================
echo   EnesMem EXE Builder
echo ==========================================
echo.

:: Check if running as admin (optional, build doesn't need it but final exe does)
echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.11+ and add to PATH
    pause
    exit /b 1
)

echo Checking PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist EnesMem.spec del EnesMem.spec

echo.
echo Building executable...
echo This may take a few minutes...
echo.

:: Build with PyInstaller
python -m PyInstaller ^
    --name=EnesMem ^
    --onefile ^
    --windowed ^
    --clean ^
    --noconfirm ^
    --add-data "resources/lang;resources/lang" ^
    --add-data "data;data" ^
    --hidden-import PyQt6.sip ^
    --hidden-import pynput.keyboard._win32 ^
    --hidden-import pynput.mouse._win32 ^
    --uac-admin ^
    main.py

if errorlevel 1 (
    echo.
    echo ❌ BUILD FAILED!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo ✅ BUILD SUCCESSFUL!
echo ==========================================
echo.
echo Location: dist\EnesMem.exe
for %%I in (dist\EnesMem.exe) do (
    echo Size: %%~zI bytes
)
echo.
echo IMPORTANT NOTES:
echo 1. Run EnesMem.exe as Administrator
echo 2. Antivirus may flag this - add exception if needed
echo 3. Users don't need Python installed
echo.
pause
