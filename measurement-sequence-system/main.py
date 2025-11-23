"""
Messsequenz-Software - Hauptanwendung
Professional Measurement Sequence Management System
VOLLSTÄNDIG IMPLEMENTIERT https://lmarena.ai/c/019aac7a-6199-7434-a6d2-186f3db5ae2c MacBook Air
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
import sys
import os
from pathlib import Path
from gui.main_window import MainWindow
from core.sequence_manager import SequenceManager
from core.plugin_manager import PluginManager
from core.database_manager import DatabaseManager
from core.config_manager import ConfigManager

# Stelle sicher dass alle Pfade korrekt sind
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


def setup_logging(config_manager):
    """Konfiguriere Logging-System"""
    log_config = config_manager.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_file = log_config.get('file', 'measurement_system.log')
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Konvertiere String zu Log-Level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


class MeasurementApplication:
    """Hauptanwendungsklasse für das Messsystem"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Professionelles Messsequenz-System v1.0")

        # Style konfigurieren
        self._configure_style()

        # Initialisiere Manager
        self._initialize_managers()

        # Setup Logging
        self.logger = setup_logging(self.config_manager)

        # Erstelle Verzeichnisse falls nicht vorhanden
        self._ensure_directories()

        # Setze Icon (falls vorhanden)
        self._set_icon()

        # Erstelle GUI
        self.main_window = MainWindow(
            self.root,
            self.sequence_manager,
            self.plugin_manager,
            self.database_manager,
            self.config_manager
        )

        # Event-Handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Behandle unbehandelte Exceptions
        self.root.report_callback_exception = self.handle_exception

        self.logger.info("=" * 60)
        self.logger.info("Anwendung erfolgreich gestartet")
        self.logger.info("=" * 60)

        # Zeige Willkommens-Dialog beim ersten Start
        if self.config_manager.get('first_run', True):
            self.root.after(500, self.show_welcome_dialog)

    def _configure_style(self):
        """Konfiguriere TTK-Style"""
        style = ttk.Style()

        # Versuche moderneres Theme zu verwenden
        available_themes = style.theme_names()

        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')

        # Konfiguriere Farben
        style.configure('TButton', padding=6)
        style.configure('TLabel', padding=2)
        style.configure('TFrame', background='#f0f0f0')

    def _initialize_managers(self):
        """Initialisiere alle Manager-Komponenten"""
        try:
            # Config Manager zuerst
            self.config_manager = ConfigManager()
            self.config_manager.load()

            # Database Manager
            db_path = self.config_manager.get('database_path', 'measurements.db')
            self.database_manager = DatabaseManager(db_path)

            # Plugin Manager
            self.plugin_manager = PluginManager()
            plugin_dir = self.config_manager.get('plugin_directory', 'plugins')
            self.plugin_manager.plugin_directory = Path(plugin_dir)

            # Sequence Manager
            self.sequence_manager = SequenceManager(
                self.plugin_manager,
                self.database_manager
            )

            # Lade Plugins
            self.plugin_manager.load_plugins()

            print(f"✓ {len(self.plugin_manager.plugin_classes)} Plugins geladen")

        except Exception as e:
            print(f"✗ Fehler bei der Initialisierung: {e}")
            messagebox.showerror(
                "Initialisierungsfehler",
                f"Die Anwendung konnte nicht initialisiert werden:\n\n{e}\n\n"
                "Bitte überprüfen Sie die Log-Datei für Details."
            )
            raise

    def _ensure_directories(self):
        """Stelle sicher dass alle benötigten Verzeichnisse existieren"""
        directories = [
            'plugins',
            'examples',
            'examples/example_sequences',
            'logs'
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def _set_icon(self):
        """Setze Anwendungs-Icon falls vorhanden"""
        icon_path = Path('icon.ico')
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except:
                pass  # Icon nicht kritisch

    def show_welcome_dialog(self):
        """Zeige Willkommens-Dialog beim ersten Start"""
        welcome_text = """
Willkommen zum Messsequenz-System!

ERSTE SCHRITTE:

1. Beispiel-Sequenz laden:
   Datei → Sequenz öffnen → examples/

2. Neue Sequenz erstellen:
   Datei → Neue Sequenz

3. Plugins durchstöbern:
   Tab "Plugin-Verwaltung"

4. Hilfe anzeigen:
   Hilfe → Dokumentation (F1)

TIPPS:
• Drücken Sie F5 um Plugins zu aktualisieren
• Verwenden Sie Ctrl+S zum Speichern
• Die Datenbank speichert alle Messergebnisse automatisch

Viel Erfolg mit Ihren Messungen!
        """

        dialog = tk.Toplevel(self.root)
        dialog.title("Willkommen")
        dialog.geometry("500x450")
        dialog.transient(self.root)
        dialog.grab_set()

        # Text
        text_frame = ttk.Frame(dialog, padding=20)
        text_frame.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(text_frame, wrap=tk.WORD, height=15)
        scrollbar = ttk.Scrollbar(text_frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.insert('1.0', welcome_text)
        text.configure(state=tk.DISABLED)

        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Checkbox
        show_again_var = tk.BooleanVar(value=True)

        check_frame = ttk.Frame(dialog, padding=(20, 0, 20, 10))
        check_frame.pack(fill=tk.X)

        ttk.Checkbutton(
            check_frame,
            text="Beim nächsten Start wieder anzeigen",
            variable=show_again_var
        ).pack(anchor=tk.W)

        # Button
        def close_welcome():
            self.config_manager.set('first_run', show_again_var.get())
            self.config_manager.save()
            dialog.destroy()

        ttk.Button(
            dialog,
            text="Los geht's!",
            command=close_welcome
        ).pack(pady=10)

        # Zentriere Dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Behandle unbehandelte Exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self.logger.error(
            "Unbehandelte Exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

        error_msg = f"{exc_type.__name__}: {exc_value}"

        messagebox.showerror(
            "Fehler",
            f"Ein unerwarteter Fehler ist aufgetreten:\n\n{error_msg}\n\n"
            "Details wurden in der Log-Datei gespeichert."
        )

    def on_closing(self):
        """Cleanup beim Schließen der Anwendung"""
        try:
            # Speichere Fenster-Geometrie
            self.main_window.save_window_geometry()

            # Speichere Konfiguration
            self.config_manager.save()

            # Beende laufende Sequenzen
            if self.sequence_manager.is_running():
                response = messagebox.askyesno(
                    "Sequenz läuft",
                    "Eine Messsequenz läuft noch. Trotzdem beenden?"
                )
                if not response:
                    return
                self.sequence_manager.stop()

            # Cleanup Plugins
            self.plugin_manager.cleanup_all()

            # Schließe Datenbankverbindung
            self.database_manager.close()

            self.logger.info("Anwendung wird beendet")
            self.logger.info("=" * 60)

            self.root.destroy()

        except Exception as e:
            self.logger.error(f"Fehler beim Beenden: {e}")
            self.root.destroy()

    def run(self):
        """Starte die Anwendung"""
        # Zentriere Hauptfenster
        self.root.update_idletasks()

        # Hole gespeicherte Geometrie oder zentriere
        geometry = self.config_manager.get('window_geometry', None)
        if not geometry:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            window_width = 1400
            window_height = 900

            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2)

            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.root.mainloop()


def check_dependencies():
    """Prüfe ob optionale Abhängigkeiten vorhanden sind"""
    missing = []
    warnings = []

    # Kritische Pakete
    try:
        import tkinter
    except ImportError:
        missing.append('tkinter (Teil von Python)')

    # Optionale Pakete
    optional_packages = {
        'numpy': ('NumPy', 'Statistische Berechnungen eingeschränkt'),
        'matplotlib': ('Matplotlib', 'Datenvisualisierung nicht verfügbar'),
        'PIL': ('Pillow', 'Bildverarbeitung nicht verfügbar'),
        'scipy': ('SciPy', 'Erweiterte Statistik nicht verfügbar')
    }

    for module, (name, warning) in optional_packages.items():
        try:
            __import__(module)
        except ImportError:
            warnings.append(f"{name}: {warning}")

    return missing, warnings


def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("Messsequenz-System v1.0")
    print("=" * 60)
    print()

    # Prüfe Abhängigkeiten
    missing, warnings = check_dependencies()

    if missing:
        print("✗ FEHLER: Folgende kritische Pakete fehlen:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nBitte installieren Sie die fehlenden Pakete.")
        sys.exit(1)

    if warnings:
        print("⚠ Warnung: Einige optionale Pakete fehlen:")
        for warn in warnings:
            print(f"  - {warn}")
        print("\nEinige Funktionen sind möglicherweise eingeschränkt.")
        print("Installieren Sie mit: pip install -r requirements.txt")
        print()

    print("Starte Anwendung...")
    print()

    try:
        app = MeasurementApplication()
        app.run()

    except KeyboardInterrupt:
        print("\n\nAnwendung durch Benutzer beendet.")
        sys.exit(0)

    except Exception as e:
        print(f"\n\n✗ KRITISCHER FEHLER: {e}")
        import traceback
        traceback.print_exc()

        print("\nBitte überprüfen Sie die Log-Datei 'measurement_system.log' für Details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
