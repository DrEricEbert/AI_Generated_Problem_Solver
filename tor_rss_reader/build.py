"""
Build-Skript für TOR RSS Reader
Erstellt ausführbare Dateien für verschiedene Plattformen
"""

import PyInstaller.__main__
import platform
import shutil
from pathlib import Path

def build_app():
    """Baut die Anwendung mit PyInstaller"""

    system = platform.system()
    print(f"🔨 Building TOR RSS Reader für {system}...")

    # Build-Argumente
    args = [
        'main.py',
        '--name=TOR_RSS_Reader',
        '--windowed',  # Keine Konsole (GUI-Modus)
        '--onefile',   # Einzelne EXE-Datei
        '--clean',
        '--noconfirm',

        # Zusätzliche Dateien
        '--add-data=README.md:.',

        # Hidden Imports (für feedparser und andere)
        '--hidden-import=feedparser',
        '--hidden-import=socks',
        '--hidden-import=urllib3',
        '--hidden-import=requests',

        # Optimierungen
        #'--optimize=2',

        # Metadata
        '--version-file=version_info.txt' if system == 'Windows' else '',
    ]

    # Icon hinzufügen (wenn vorhanden)
    icon_path = Path('icon.ico' if system == 'Windows' else 'icon.icns')
    if icon_path.exists():
        args.append(f'--icon={icon_path}')

    # Leere Strings entfernen
    args = [arg for arg in args if arg]

    print("📦 PyInstaller Argumente:")
    for arg in args:
        print(f"   {arg}")

    # Build starten
    PyInstaller.__main__.run(args)

    print("✅ Build abgeschlossen!")
    print(f"📁 Ausführbare Datei in: dist/")


def build_directory_version():
    """Baut die Anwendung als Verzeichnis (schneller beim Start)"""

    system = platform.system()
    print(f"🔨 Building TOR RSS Reader (Directory Mode) für {system}...")

    args = [
        'main.py',
        '--name=TOR_RSS_Reader',
        '--windowed',
        '--onedir',  # Verzeichnis statt einzelne Datei
        '--clean',
        '--noconfirm',
        '--add-data=README.md:.',
        '--hidden-import=feedparser',
        '--hidden-import=socks',
        '--hidden-import=urllib3',
        '--hidden-import=requests',
        '--optimize=2',
    ]

    icon_path = Path('icon.ico' if system == 'Windows' else 'icon.icns')
    if icon_path.exists():
        args.append(f'--icon={icon_path}')

    args = [arg for arg in args if arg]

    PyInstaller.__main__.run(args)

    print("✅ Build abgeschlossen!")
    print(f"📁 Anwendung in: dist/TOR_RSS_Reader/")


def clean_build():
    """Bereinigt Build-Artefakte"""
    print("🧹 Bereinige Build-Verzeichnisse...")

    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['*.spec']

    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   ✓ Entfernt: {dir_name}/")

    for pattern in files_to_remove:
        for file_path in Path('.').glob(pattern):
            file_path.unlink()
            print(f"   ✓ Entfernt: {file_path}")

    print("✅ Bereinigung abgeschlossen!")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'clean':
            clean_build()
        elif sys.argv[1] == 'dir':
            build_directory_version()
        elif sys.argv[1] == 'onefile':
            build_app()
        else:
            print("Usage: python build.py [onefile|dir|clean]")
    else:
        # Standard: onefile
        build_app()
