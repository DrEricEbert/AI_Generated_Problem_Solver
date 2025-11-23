"""
Hauptfenster der Anwendung - VOLLSTÄNDIG IMPLEMENTIERT
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import csv
import json
from datetime import datetime
from gui.sequence_editor import SequenceEditor
from gui.plugin_manager_gui import PluginManagerGUI
from gui.measurement_control import MeasurementControl
from gui.data_visualization import DataVisualization
from gui.database_browser import DatabaseBrowser
from gui.settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)


class MainWindow:
    """Hauptfenster der Anwendung"""

    def __init__(self, root, sequence_manager, plugin_manager,
                 database_manager, config_manager):
        self.root = root
        self.sequence_manager = sequence_manager
        self.plugin_manager = plugin_manager
        self.database_manager = database_manager
        self.config_manager = config_manager

        self._setup_ui()
        self._setup_menu()
        self._load_window_geometry()

        # Speichere Geometrie beim Ändern
        self.root.bind('<Configure>', self._on_configure)

    def _setup_ui(self):
        """Erstelle UI-Komponenten"""
        # Hauptcontainer
        self.main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Linke Seite: Sequenz-Editor und Plugin-Manager
        left_panel = ttk.Frame(self.main_container)
        self.main_container.add(left_panel, weight=1)

        # Notebook für verschiedene Tabs
        self.left_notebook = ttk.Notebook(left_panel)
        self.left_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab: Sequenz-Editor
        self.sequence_editor = SequenceEditor(
            self.left_notebook,
            self.sequence_manager,
            self.plugin_manager
        )
        self.left_notebook.add(
            self.sequence_editor.frame,
            text="Sequenz-Editor"
        )

        # Tab: Plugin-Manager
        self.plugin_manager_gui = PluginManagerGUI(
            self.left_notebook,
            self.plugin_manager
        )
        self.left_notebook.add(
            self.plugin_manager_gui.frame,
            text="Plugin-Verwaltung"
        )

        # Tab: Datenbank-Browser
        self.database_browser = DatabaseBrowser(
            self.left_notebook,
            self.database_manager
        )
        self.left_notebook.add(
            self.database_browser.frame,
            text="Datenbank"
        )

        # Rechte Seite: Messsteuerung und Visualisierung
        right_panel = ttk.Frame(self.main_container)
        self.main_container.add(right_panel, weight=2)

        self.right_notebook = ttk.Notebook(right_panel)
        self.right_notebook.pack(fill=tk.BOTH, expand=True)

        # Tab: Messsteuerung
        self.measurement_control = MeasurementControl(
            self.right_notebook,
            self.sequence_manager
        )
        self.right_notebook.add(
            self.measurement_control.frame,
            text="Messung"
        )

        # Tab: Visualisierung
        self.data_visualization = DataVisualization(
            self.right_notebook,
            self.database_manager
        )
        self.right_notebook.add(
            self.data_visualization.frame,
            text="Visualisierung"
        )

        # Statusleiste
        self._create_status_bar()

    def _create_status_bar(self):
        """Erstelle Statusleiste"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = ttk.Label(
            self.status_bar,
            text="Bereit",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Plugins-Status
        self.plugins_status = ttk.Label(
            self.status_bar,
            text=f"Plugins: {len(self.plugin_manager.plugin_classes)}",
            relief=tk.SUNKEN,
            width=15
        )
        self.plugins_status.pack(side=tk.RIGHT, padx=2)

        # Datenbank-Status
        db_name = self.config_manager.get('database_path', 'measurements.db')
        self.db_status = ttk.Label(
            self.status_bar,
            text=f"DB: {db_name}",
            relief=tk.SUNKEN,
            width=20
        )
        self.db_status.pack(side=tk.RIGHT, padx=2)

    def _setup_menu(self):
        """Erstelle Menüleiste"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Datei-Menü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(
            label="Neue Sequenz",
            command=self.new_sequence,
            accelerator="Ctrl+N"
        )
        file_menu.add_command(
            label="Sequenz öffnen...",
            command=self.load_sequence,
            accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Sequenz speichern",
            command=self.save_sequence,
            accelerator="Ctrl+S"
        )
        file_menu.add_command(
            label="Sequenz speichern als...",
            command=self.save_sequence_as,
            accelerator="Ctrl+Shift+S"
        )
        file_menu.add_separator()

        # Letzte Dateien
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Zuletzt verwendet", menu=self.recent_menu)
        self._update_recent_files_menu()

        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.on_closing)

        # Bearbeiten-Menü
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bearbeiten", menu=edit_menu)
        edit_menu.add_command(
            label="Einstellungen...",
            command=self.show_settings,
            accelerator="Ctrl+,"
        )

        # Ansicht-Menü
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ansicht", menu=view_menu)
        view_menu.add_command(
            label="Plugins aktualisieren",
            command=self.refresh_plugins,
            accelerator="F5"
        )
        view_menu.add_command(
            label="Datenbank aktualisieren",
            command=self.refresh_database
        )
        view_menu.add_separator()
        view_menu.add_checkbutton(
            label="Statusleiste anzeigen",
            command=self.toggle_statusbar
        )

        # Messung-Menü
        measurement_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Messung", menu=measurement_menu)
        measurement_menu.add_command(
            label="Starten",
            command=self.start_measurement,
            accelerator="F9"
        )
        measurement_menu.add_command(
            label="Pause/Fortsetzen",
            command=self.pause_measurement,
            accelerator="F10"
        )
        measurement_menu.add_command(
            label="Stoppen",
            command=self.stop_measurement,
            accelerator="F11"
        )

        # Extras-Menü
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Extras", menu=tools_menu)
        tools_menu.add_command(
            label="Datenbank exportieren...",
            command=self.export_database
        )
        tools_menu.add_command(
            label="Datenbank optimieren",
            command=self.optimize_database
        )
        tools_menu.add_separator()
        tools_menu.add_command(
            label="Log-Datei öffnen",
            command=self.open_log_file
        )
        tools_menu.add_command(
            label="Plugin-Verzeichnis öffnen",
            command=self.open_plugin_directory
        )

        # Hilfe-Menü
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Hilfe", menu=help_menu)
        help_menu.add_command(
            label="Dokumentation",
            command=self.show_help,
            accelerator="F1"
        )
        help_menu.add_command(
            label="Tastenkombinationen",
            command=self.show_shortcuts
        )
        help_menu.add_separator()
        help_menu.add_command(
            label="Über",
            command=self.show_about
        )

        # Tastenkombinationen
        self.root.bind('<Control-n>', lambda e: self.new_sequence())
        self.root.bind('<Control-o>', lambda e: self.load_sequence())
        self.root.bind('<Control-s>', lambda e: self.save_sequence())
        self.root.bind('<Control-Shift-S>', lambda e: self.save_sequence_as())
        self.root.bind('<Control-comma>', lambda e: self.show_settings())
        self.root.bind('<F1>', lambda e: self.show_help())
        self.root.bind('<F5>', lambda e: self.refresh_plugins())
        self.root.bind('<F9>', lambda e: self.start_measurement())
        self.root.bind('<F10>', lambda e: self.pause_measurement())
        self.root.bind('<F11>', lambda e: self.stop_measurement())

    def _update_recent_files_menu(self):
        """Aktualisiere Liste der letzten Dateien"""
        self.recent_menu.delete(0, tk.END)
        recent_files = self.config_manager.get('recent_files', [])

        if not recent_files:
            self.recent_menu.add_command(label="(Keine)", state=tk.DISABLED)
        else:
            for filepath in recent_files:
                # Kürze lange Pfade
                display_path = filepath
                if len(display_path) > 50:
                    display_path = "..." + display_path[-47:]

                self.recent_menu.add_command(
                    label=display_path,
                    command=lambda f=filepath: self._load_sequence_file(f)
                )

            self.recent_menu.add_separator()
            self.recent_menu.add_command(
                label="Liste leeren",
                command=self.clear_recent_files
            )

    def clear_recent_files(self):
        """Leere Liste der letzten Dateien"""
        self.config_manager.set('recent_files', [])
        self._update_recent_files_menu()
        self.update_status("Liste der letzten Dateien geleert")

    def new_sequence(self):
        """Erstelle neue Sequenz"""
        # Prüfe ob ungespeicherte Änderungen existieren
        if self.sequence_manager.current_sequence:
            response = messagebox.askyesnocancel(
                "Ungespeicherte Änderungen",
                "Möchten Sie die aktuelle Sequenz speichern?"
            )
            if response is None:  # Cancel
                return
            elif response:  # Yes
                self.save_sequence()

        self.sequence_editor.new_sequence()
        self.update_status("Neue Sequenz erstellt")

    def load_sequence(self):
        """Lade Sequenz aus Datei"""
        filepath = filedialog.askopenfilename(
            title="Sequenz öffnen",
            filetypes=[
                ("JSON-Dateien", "*.json"),
                ("Alle Dateien", "*.*")
            ],
            initialdir=self.config_manager.get('last_directory', '.')
        )
        if filepath:
            self._load_sequence_file(filepath)

    def _load_sequence_file(self, filepath: str):
        """Lade Sequenz aus Datei"""
        try:
            self.sequence_manager.load_sequence(filepath)
            self.sequence_editor.load_current_sequence()
            self.config_manager.add_recent_file(filepath)

            # Speichere letztes Verzeichnis
            import os
            self.config_manager.set('last_directory', os.path.dirname(filepath))

            self._update_recent_files_menu()
            self.update_status(f"Sequenz geladen: {filepath}")

        except Exception as e:
            messagebox.showerror(
                "Fehler",
                f"Sequenz konnte nicht geladen werden:\n{e}"
            )
            logger.error(f"Fehler beim Laden: {e}", exc_info=True)

    def save_sequence(self):
        """Speichere aktuelle Sequenz"""
        last_path = self.config_manager.get('last_sequence_path', '')
        if last_path:
            self._save_sequence_file(last_path)
        else:
            self.save_sequence_as()

    def save_sequence_as(self):
        """Speichere Sequenz unter neuem Namen"""
        if not self.sequence_manager.current_sequence:
            messagebox.showwarning("Warnung", "Keine Sequenz zum Speichern vorhanden")
            return

        default_name = self.sequence_manager.current_sequence.name.replace(' ', '_') + '.json'

        filepath = filedialog.asksaveasfilename(
            title="Sequenz speichern",
            filetypes=[
                ("JSON-Dateien", "*.json"),
                ("Alle Dateien", "*.*")
            ],
            defaultextension=".json",
            initialfile=default_name,
            initialdir=self.config_manager.get('last_directory', '.')
        )
        if filepath:
            self._save_sequence_file(filepath)

    def _save_sequence_file(self, filepath: str):
        """Speichere Sequenz in Datei"""
        try:
            self.sequence_editor.save_to_sequence_manager()
            self.sequence_manager.save_sequence(filepath)
            self.config_manager.set('last_sequence_path', filepath)
            self.config_manager.add_recent_file(filepath)

            import os
            self.config_manager.set('last_directory', os.path.dirname(filepath))

            self._update_recent_files_menu()
            self.update_status(f"Sequenz gespeichert: {filepath}")

        except Exception as e:
            messagebox.showerror(
                "Fehler",
                f"Sequenz konnte nicht gespeichert werden:\n{e}"
            )
            logger.error(f"Fehler beim Speichern: {e}", exc_info=True)

    def start_measurement(self):
        """Starte Messung"""
        self.measurement_control.start_measurement()

    def pause_measurement(self):
        """Pausiere Messung"""
        self.measurement_control.pause_measurement()

    def stop_measurement(self):
        """Stoppe Messung"""
        self.measurement_control.stop_measurement()

    def refresh_plugins(self):
        """Aktualisiere Plugin-Liste"""
        try:
            self.plugin_manager.load_plugins()
            self.plugin_manager_gui.refresh()
            self.sequence_editor.refresh_plugin_lists()
            self.plugins_status.config(
                text=f"Plugins: {len(self.plugin_manager.plugin_classes)}"
            )
            self.update_status("Plugins aktualisiert")
        except Exception as e:
            messagebox.showerror("Fehler", f"Plugins konnten nicht aktualisiert werden:\n{e}")
            logger.error(f"Plugin-Aktualisierung fehlgeschlagen: {e}")

    def refresh_database(self):
        """Aktualisiere Datenbank-Ansicht"""
        self.database_browser.refresh()
        self.data_visualization.refresh_sequences()
        self.update_status("Datenbank aktualisiert")

    def export_database(self):
        """Exportiere Datenbank als CSV oder JSON"""
        # Dialog für Export-Optionen
        export_dialog = DatabaseExportDialog(self.root, self.database_manager)

    def optimize_database(self):
        """Optimiere Datenbank (VACUUM)"""
        try:
            cursor = self.database_manager.connection.cursor()
            cursor.execute("VACUUM")
            self.database_manager.connection.commit()
            messagebox.showinfo("Erfolg", "Datenbank wurde optimiert")
            self.update_status("Datenbank optimiert")
        except Exception as e:
            messagebox.showerror("Fehler", f"Optimierung fehlgeschlagen:\n{e}")
            logger.error(f"Datenbank-Optimierung fehlgeschlagen: {e}")

    def open_log_file(self):
        """Öffne Log-Datei im Standard-Editor"""
        import os
        import subprocess
        import platform

        log_file = "measurement_system.log"

        if not os.path.exists(log_file):
            messagebox.showinfo("Info", "Keine Log-Datei gefunden")
            return

        try:
            if platform.system() == 'Windows':
                os.startfile(log_file)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', log_file])
            else:  # Linux
                subprocess.run(['xdg-open', log_file])
        except Exception as e:
            messagebox.showerror("Fehler", f"Log-Datei konnte nicht geöffnet werden:\n{e}")

    def open_plugin_directory(self):
        """Öffne Plugin-Verzeichnis im Datei-Explorer"""
        import os
        import subprocess
        import platform

        plugin_dir = self.config_manager.get('plugin_directory', 'plugins')

        if not os.path.exists(plugin_dir):
            os.makedirs(plugin_dir)

        try:
            if platform.system() == 'Windows':
                os.startfile(plugin_dir)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', plugin_dir])
            else:  # Linux
                subprocess.run(['xdg-open', plugin_dir])
        except Exception as e:
            messagebox.showerror("Fehler", f"Verzeichnis konnte nicht geöffnet werden:\n{e}")

    def toggle_statusbar(self):
        """Toggle Statusleiste"""
        if self.status_bar.winfo_viewable():
            self.status_bar.pack_forget()
        else:
            self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def show_settings(self):
        """Zeige Einstellungen"""
        SettingsDialog(self.root, self.config_manager)

    def show_help(self):
        """Zeige Hilfe"""
        help_text = """
Messsequenz-System - Hilfe

SEQUENZ ERSTELLEN:
1. Datei → Neue Sequenz (Ctrl+N)
2. Parameterbereiche im Tab "Parameterbereiche" definieren
3. "Messpunkte generieren" klicken
4. Im Tab "Plugin-Auswahl" Plugins aktivieren
5. Datei → Sequenz speichern (Ctrl+S)

MESSUNG DURCHFÜHREN:
1. Sequenz laden
2. Zum Tab "Messung" wechseln
3. Start drücken (F9)
4. Ergebnisse werden automatisch gespeichert

DATEN VISUALISIEREN:
1. Zum Tab "Visualisierung" wechseln
2. Sequenz auswählen
3. Parameter für X- und Y-Achse wählen
4. Plot wird automatisch erstellt

PLUGINS ENTWICKELN:
1. Neue .py Datei im plugins/ Verzeichnis erstellen
2. Von MeasurementPlugin oder ProcessingPlugin erben
3. Erforderliche Methoden implementieren
4. Ansicht → Plugins aktualisieren (F5)

TASTENKOMBINATIONEN:
Ctrl+N      Neue Sequenz
Ctrl+O      Sequenz öffnen
Ctrl+S      Sequenz speichern
F1          Diese Hilfe
F5          Plugins aktualisieren
F9          Messung starten
F10         Messung pausieren
F11         Messung stoppen

Weitere Informationen in der README.md
        """

        # Erstelle scrollbares Hilfefenster
        help_window = tk.Toplevel(self.root)
        help_window.title("Hilfe")
        help_window.geometry("600x500")

        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(help_window, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.insert('1.0', help_text)
        text_widget.configure(state=tk.DISABLED)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(
            help_window,
            text="Schließen",
            command=help_window.destroy
        ).pack(pady=5)

    def show_shortcuts(self):
        """Zeige Tastenkombinationen"""
        shortcuts_text = """
DATEI:
Ctrl+N              Neue Sequenz
Ctrl+O              Sequenz öffnen
Ctrl+S              Sequenz speichern
Ctrl+Shift+S        Sequenz speichern als

BEARBEITEN:
Ctrl+,              Einstellungen

ANSICHT:
F5                  Plugins aktualisieren

MESSUNG:
F9                  Messung starten
F10                 Messung pausieren/fortsetzen
F11                 Messung stoppen

HILFE:
F1                  Hilfe anzeigen
        """
        messagebox.showinfo("Tastenkombinationen", shortcuts_text)

    def show_about(self):
        """Zeige Info-Dialog"""
        about_text = """
Professionelles Messsequenz-System
Version 1.0.0

Ein umfassendes, erweiterbares System zur
Verwaltung und Durchführung von Messsequenzen
mit Plugin-Architektur.

FEATURES:
• Flexible Sequenz-Definition
• Plugin-basierte Erweiterbarkeit
• SQLite Datenbank für Messergebnisse
• Datenvisualisierung
• Statistische Auswertung
• Bildverarbeitung

ENTWICKELT MIT:
• Python 3.8+
• Tkinter
• Matplotlib
• NumPy/SciPy
• Pillow

© 2024
Lizenz: MIT

https://github.com/yourusername/measurement-sequence-system
        """
        messagebox.showinfo("Über", about_text)

    def update_status(self, message: str):
        """Aktualisiere Statusleiste"""
        self.status_label.config(text=message)
        logger.info(f"Status: {message}")

    def _load_window_geometry(self):
        """Lade Fenstergeometrie"""
        geometry = self.config_manager.get('window_geometry', '1400x900')
        try:
            self.root.geometry(geometry)
        except:
            self.root.geometry('1400x900')

    def _on_configure(self, event):
        """Event-Handler für Fenster-Konfiguration"""
        # Nur auf Root-Window reagieren
        if event.widget == self.root:
            # Verzögere das Speichern um zu häufige Updates zu vermeiden
            if hasattr(self, '_geometry_save_job'):
                self.root.after_cancel(self._geometry_save_job)
            self._geometry_save_job = self.root.after(500, self.save_window_geometry)

    def save_window_geometry(self):
        """Speichere Fenstergeometrie"""
        self.config_manager.set('window_geometry', self.root.geometry())

    def on_closing(self):
        """Event-Handler für Fenster schließen"""
        try:
            # Speichere Konfiguration
            self.save_window_geometry()
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

            logger.info("Anwendung wird beendet")
            self.root.destroy()

        except Exception as e:
            logger.error(f"Fehler beim Beenden: {e}")
            self.root.destroy()


class DatabaseExportDialog:
    """Dialog für Datenbank-Export"""

    def __init__(self, parent, database_manager):
        self.database_manager = database_manager
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Datenbank exportieren")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI"""
        # Beschreibung
        ttk.Label(
            self.dialog,
            text="Wählen Sie die zu exportierenden Sequenzen:",
            font=('', 10, 'bold')
        ).pack(padx=10, pady=10, anchor=tk.W)

        # Sequenz-Auswahl
        list_frame = ttk.Frame(self.dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.sequence_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            height=10
        )
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.sequence_listbox.yview)
        self.sequence_listbox.configure(yscrollcommand=scrollbar.set)

        self.sequence_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Lade Sequenzen
        sequences = self.database_manager.get_all_sequences()
        for seq in sequences:
            self.sequence_listbox.insert(tk.END, seq)

        # Auswahl-Buttons
        select_frame = ttk.Frame(self.dialog)
        select_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            select_frame,
            text="Alle auswählen",
            command=self.select_all
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            select_frame,
            text="Keine auswählen",
            command=self.select_none
        ).pack(side=tk.LEFT, padx=2)

        # Export-Format
        format_frame = ttk.LabelFrame(self.dialog, text="Export-Format", padding=10)
        format_frame.pack(fill=tk.X, padx=10, pady=5)

        self.export_format = tk.StringVar(value="csv")
        ttk.Radiobutton(
            format_frame,
            text="CSV (Comma-Separated Values)",
            variable=self.export_format,
            value="csv"
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            format_frame,
            text="JSON (JavaScript Object Notation)",
            variable=self.export_format,
            value="json"
        ).pack(anchor=tk.W)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="Exportieren",
            command=self.export
        ).pack(side=tk.RIGHT, padx=2)

        ttk.Button(
            button_frame,
            text="Abbrechen",
            command=self.dialog.destroy
        ).pack(side=tk.RIGHT, padx=2)

    def select_all(self):
        """Wähle alle Sequenzen"""
        self.sequence_listbox.selection_set(0, tk.END)

    def select_none(self):
        """Wähle keine Sequenz"""
        self.sequence_listbox.selection_clear(0, tk.END)

    def export(self):
        """Exportiere Daten"""
        # Hole ausgewählte Sequenzen
        selection = self.sequence_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warnung", "Bitte mindestens eine Sequenz auswählen")
            return

        selected_sequences = [self.sequence_listbox.get(i) for i in selection]
        export_format = self.export_format.get()

        # Datei-Dialog
        if export_format == "csv":
            filetypes = [("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")]
            defaultext = ".csv"
        else:
            filetypes = [("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")]
            defaultext = ".json"

        filepath = filedialog.asksaveasfilename(
            title="Datenbank exportieren",
            filetypes=filetypes,
            defaultextension=defaultext
        )

        if not filepath:
            return

        try:
            if export_format == "csv":
                self._export_csv(selected_sequences, filepath)
            else:
                self._export_json(selected_sequences, filepath)

            messagebox.showinfo("Erfolg", f"Datenbank erfolgreich exportiert nach:\n{filepath}")
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")
            logger.error(f"Export-Fehler: {e}", exc_info=True)

    def _export_csv(self, sequences, filepath):
        """Exportiere als CSV"""
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Sequenz',
                'Messpunkt',
                'Zeitstempel',
                'Parameter_Name',
                'Parameter_Wert',
                'Messwert_Name',
                'Messwert',
                'Einheit',
                'Plugin'
            ])

            # Daten
            for seq_name in sequences:
                data = self.database_manager.get_sequence_data(seq_name)

                for point in data:
                    timestamp = point['timestamp']
                    point_name = point['point_name']
                    parameters = point['parameters']

                    # Schreibe Zeilen für jeden Messwert
                    for plugin_name, plugin_values in point['values'].items():
                        for param_name, param_data in plugin_values.items():
                            value = param_data.get('value', '')
                            unit = param_data.get('unit', '')

                            # Parameter als String
                            param_str = ', '.join([f"{k}={v}" for k, v in parameters.items()])

                            writer.writerow([
                                seq_name,
                                point_name,
                                timestamp,
                                param_str,
                                '',
                                param_name,
                                value,
                                unit,
                                plugin_name
                            ])

    def _export_json(self, sequences, filepath):
        """Exportiere als JSON"""
        export_data = {}

        for seq_name in sequences:
            data = self.database_manager.get_sequence_data(seq_name)
            export_data[seq_name] = data

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
