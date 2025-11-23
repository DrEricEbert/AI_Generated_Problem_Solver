"""
Launcher für das Messsequenz-System
"""

import sys
import os
import logging

# Stelle sicher dass alle Module gefunden werden
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """Prüfe ob alle Abhängigkeiten installiert sind"""
    missing = []

    # Prüfe optionale Pakete
    optional = {
        'numpy': 'NumPy',
        'matplotlib': 'Matplotlib',
        'PIL': 'Pillow'
    }

    for module, name in optional.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(name)

    if missing:
        print("Warnung: Folgende optionale Pakete sind nicht installiert:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nEinige Funktionen könnten eingeschränkt sein.")
        print("Installieren Sie mit: pip install -r requirements.txt\n")

        response = input("Trotzdem fortfahren? (j/n): ")
        if response.lower() not in ['j', 'y', 'yes', 'ja']:
            sys.exit(0)


def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("Messsequenz-System v1.0")
    print("=" * 60)
    print()

    # Prüfe Abhängigkeiten
    check_dependencies()

    # Importiere und starte Hauptanwendung
    try:
        from main import MeasurementApplication

        app = MeasurementApplication()
        app.run()

    except KeyboardInterrupt:
        print("\nAnwendung durch Benutzer beendet.")
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Kritischer Fehler: {e}", exc_info=True)
        print(f"\nKRITISCHER FEHLER: {e}")
        print("Siehe measurement_system.log für Details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
