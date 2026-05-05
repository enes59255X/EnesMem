@echo off
chcp 65001 >nul
echo ==========================================
echo   EnesMem EXE Builder - Final
echo ==========================================
echo.
cd /d "%~dp0"
echo Konum: %CD%

echo.
echo [1/5] Temizlik yapiliyor...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
if exist *.spec del /q *.spec 2>nul
echo      Tamam.

echo.
echo [2/5] PyInstaller kontrol ediliyor...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo      PyInstaller bulunamadi, kuruluyor...
    python -m pip install pyinstaller -q
) else (
    echo      PyInstaller zaten kurulu.
)

echo.
echo [3/5] EXE olusturuluyor...
echo      Bu islem 5-10 dakika surer...
echo.

python -m PyInstaller ^
    --name=EnesMem ^
    --onefile ^
    --windowed ^
    --clean ^
    --noconfirm ^
    --add-data "resources/lang;resources/lang" ^
    --uac-admin ^
    --hidden-import=PyQt6.sip ^
    --hidden-import=pynput.keyboard._win32 ^
    --hidden-import=pynput.mouse._win32 ^
    --hidden-import=psutil ^
    --exclude-module=matplotlib ^
    --exclude-module=tkinter ^
    --exclude-module=PIL ^
    --exclude-module=numpy ^
    --exclude-module=scipy ^
    --exclude-module=pandas ^
    main.py

if errorlevel 1 (
    echo.
    echo [X] HATA! Build basarisiz.
    pause
    exit /b 1
)

echo.
echo [4/5] Koruma uygulaniyor...
if exist dist\EnesMem.exe (
    echo      Signature gizleniyor...
    powershell -Command "
        $path = 'dist\EnesMem.exe'
        $content = [System.IO.File]::ReadAllBytes($path)
        $text = [System.Text.Encoding]::UTF8.GetString($content)
        $text = $text.Replace('PyInstaller', 'AppLoader__')
        $text = $text.Replace('MEIPASS', 'APP_TMP___')
        [System.IO.File]::WriteAllBytes($path, [System.Text.Encoding]::UTF8.GetBytes($text))
    " 2>nul
    echo      Tamam.
)

echo.
echo [5/5] Paket olusturuluyor...
if exist dist\EnesMem.exe (
    if exist EnesMem-v1.0.0.zip del EnesMem-v1.0.0.zip
    powershell -Command "Compress-Archive -Path 'dist\EnesMem.exe' -DestinationPath 'EnesMem-v1.0.0.zip' -Force"
    
    for %%I in (dist\EnesMem.exe) do (
        echo      EXE Boyut: %%~zI bytes
    )
    for %%I in (EnesMem-v1.0.0.zip) do (
        echo      ZIP Boyut: %%~zI bytes
    )
    echo.
    echo ==========================================
    echo  ✅ BUILD TAMAMLANDI!
    echo ==========================================
    echo.
    echo  📦 dist\EnesMem.exe
    echo  📦 EnesMem-v1.0.0.zip
    echo.
    echo  ⚠️  NOT: Antivirus uyari verebilir (bellek araci oldugu icin)
    echo      Cozum: Virustotal.com'a yukle veya istisna ekle
    echo.
) else (
    echo [X] HATA! EXE dosyasi bulunamadi.
)

pause
