@echo off
chcp 65001 >nul
echo ==========================================
echo   EnesMem EXE Builder
echo ==========================================
echo.

echo [1/3] Temizlik yapiliyor...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec
echo      Tamam.

echo.
echo [2/3] EXE olusturuluyor...
echo      Bu islem 5-10 dakika surer...
echo      Lutfen bekleyin...
echo.

python -m PyInstaller --name=EnesMem --onefile --windowed --clean --noconfirm --add-data "resources/lang;resources/lang" --uac-admin --hidden-import=PyQt6.sip --hidden-import=pynput.keyboard._win32 --hidden-import=pynput.mouse._win32 --exclude-module=matplotlib --exclude-module=tkinter main.py

if errorlevel 1 (
    echo.
    echo [X] Build hatasi!
    pause
    exit /b 1
)

echo.
echo [3/3] Paket olusturuluyor...
if exist dist\EnesMem.exe (
    if exist EnesMem-v1.0.0.zip del EnesMem-v1.0.0.zip
    python -c "import zipfile; z=zipfile.ZipFile('EnesMem-v1.0.0.zip','w'); z.write('dist/EnesMem.exe','EnesMem.exe'); z.close()"
    
    for %%I in (dist\EnesMem.exe) do echo      EXE: %%~zI bytes
    for %%I in (EnesMem-v1.0.0.zip) do echo      ZIP: %%~zI bytes
    
    echo.
    echo ==========================================
    echo  ✅ BUILD TAMAMLANDI!
    echo ==========================================
    echo.
    echo  📦 dist\EnesMem.exe
    echo  📦 EnesMem-v1.0.0.zip
    echo.
) else (
    echo [X] EXE bulunamadi!
)

pause
