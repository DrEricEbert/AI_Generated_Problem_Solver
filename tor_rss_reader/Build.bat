@echo off
REM Build-Skript für Windows

echo 🔨 Building TOR RSS Reader...

REM Virtuelle Umgebung aktivieren (falls vorhanden)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM PyInstaller installieren (falls nicht vorhanden)
pip install pyinstaller

REM Build durchführen
python build.py onefile

REM Prüfen ob erfolgreich
if exist dist\TOR_RSS_Reader.exe (
    echo ✅ Build erfolgreich!
    echo 📁 Ausführbare Datei: dist\TOR_RSS_Reader.exe
) else (
    echo ❌ Build fehlgeschlagen!
    exit /b 1
)

pause
