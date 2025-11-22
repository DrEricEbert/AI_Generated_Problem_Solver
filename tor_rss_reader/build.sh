#!/bin/bash
# Build-Skript für Linux/macOS

echo "🔨 Building TOR RSS Reader..."

# Virtuelle Umgebung aktivieren (falls vorhanden)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# PyInstaller installieren (falls nicht vorhanden)
pip install pyinstaller

# Build durchführen
python build.py onefile

# Berechtigungen setzen
if [ -f "dist/TOR_RSS_Reader" ]; then
    chmod +x dist/TOR_RSS_Reader
    echo "✅ Build erfolgreich!"
    echo "📁 Ausführbare Datei: dist/TOR_RSS_Reader"
else
    echo "❌ Build fehlgeschlagen!"
    exit 1
fi
