"""
Einstellungs-Dialog
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging

logger = logging.getLogger(__name__)


class SettingsDialog:
    """Dialog für Anwendungseinstellungen"""

    def __init__(self, parent, config_manager):
        self.config_manager = config_manager
        self.original_config = config_manager.config.copy()

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Einstellungen")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Setup UI"""
        # Notebook für verschiedene Kategorien
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab: Allgemein
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="Allgemein")
        self._setup_general_tab(general_frame)

        # Tab: Messung
        measurement_frame = ttk.Frame(notebook, padding=10)
        notebook.add(measurement_frame, text="Messung")
        self._setup_measurement_tab(measurement_frame)

        # Tab: Visualisierung
        plot_frame = ttk.Frame(notebook, padding=10)
        notebook.add(plot_frame, text="Visualisierung")
        self._setup_plot_tab(plot_frame)

        # Tab: Erweitert
        advanced_frame = ttk.Frame(notebook, padding=10)
        notebook.add(advanced_frame, text="Erweitert")
        self._setup_advanced_tab(advanced_frame)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="OK",
            command=self.save_and_close
        ).pack(side=tk.RIGHT, padx=2)

        ttk.Button(
            button_frame,
            text="Abbrechen",
            command=self.cancel
        ).pack(side=tk.RIGHT, padx=2)

        ttk.Button(
            button_frame,
            text="Übernehmen",
            command=self.apply
        ).pack(side=tk.RIGHT, padx=2)

        ttk.Button(
            button_frame,
            text="Standard",
            command=self.reset_to_defaults
        ).pack(side=tk.LEFT, padx=2)

    def _setup_general_tab(self, parent):
        """Setup Allgemein-Tab"""
        row = 0

        # Datenbank-Pfad
        ttk.Label(parent, text="Datenbank-Pfad:").grid(row=row, column=0, sticky=tk.W, pady=5)

        path_frame = ttk.Frame(parent)
        path_frame.grid(row=row, column=1, sticky=tk.EW, pady=5)

        self.db_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.db_path_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="...", width=3, command=self.browse_database).pack(side=tk.RIGHT, padx=2)

        row += 1

        # Plugin-Verzeichnis
        ttk.Label(parent, text="Plugin-Verzeichnis:").grid(row=row, column=0, sticky=tk.W, pady=5)

        plugin_frame = ttk.Frame(parent)
        plugin_frame.grid(row=row, column=1, sticky=tk.EW, pady=5)

        self.plugin_dir_var = tk.StringVar()
        ttk.Entry(plugin_frame, textvariable=self.plugin_dir_var, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(plugin_frame, text="...", width=3, command=self.browse_plugin_dir).pack(side=tk.RIGHT, padx=2)

        row += 1

        # Auto-Save
        self.auto_save_var = tk.BooleanVar()
        ttk.Checkbutton(
            parent,
            text="Automatisch speichern",
            variable=self.auto_save_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)

        row += 1

        # Max History
        ttk.Label(parent, text="Maximale Historie:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.max_history_var = tk.IntVar()
        ttk.Spinbox(
            parent,
            from_=100,
            to=10000,
            increment=100,
            textvariable=self.max_history_var,
            width=20
        ).grid(row=row, column=1, sticky=tk.W, pady=5)

        parent.columnconfigure(1, weight=1)

    def _setup_measurement_tab(self, parent):
        """Setup Messungs-Tab"""
        row = 0

        # Messverzögerung
        ttk.Label(parent, text="Messverzögerung (s):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.measurement_delay_var = tk.DoubleVar()
        ttk.Spinbox(
            parent,
            from_=0.0,
            to=10.0,
            increment=0.1,
            textvariable=self.measurement_delay_var,
            width=20
        ).grid(row=row, column=1, sticky=tk.W, pady=5)

        row += 1

        # Hardware Timeout
        ttk.Label(parent, text="Hardware Timeout (s):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.hardware_timeout_var = tk.IntVar()
        ttk.Spinbox(
            parent,
            from_=1,
            to=300,
            increment=1,
            textvariable=self.hardware_timeout_var,
            width=20
        ).grid(row=row, column=1, sticky=tk.W, pady=5)

        row += 1

        # Retry Count
        ttk.Label(parent, text="Wiederholungsversuche:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.retry_count_var = tk.IntVar()
        ttk.Spinbox(
            parent,
            from_=0,
            to=10,
            increment=1,
            textvariable=self.retry_count_var,
            width=20
        ).grid(row=row, column=1, sticky=tk.W, pady=5)

        row += 1

        # Serielle Schnittstelle
        ttk.Label(parent, text="Serieller Port:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.serial_port_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.serial_port_var, width=20).grid(row=row, column=1, sticky=tk.W, pady=5)

        row += 1

        # Baudrate
        ttk.Label(parent, text="Baudrate:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.baud_rate_var = tk.IntVar()
        ttk.Combobox(
            parent,
            textvariable=self.baud_rate_var,
            values=[9600, 19200, 38400, 57600, 115200],
            width=17,
            state='readonly'
        ).grid(row=row, column=1, sticky=tk.W, pady=5)

        parent.columnconfigure(1, weight=1)

    def _setup_plot_tab(self, parent):
        """Setup Visualisierungs-Tab"""
        row = 0

        # Grid anzeigen
        self.plot_grid_var = tk.BooleanVar()
        ttk.Checkbutton(
            parent,
            text="Gitter anzeigen",
            variable=self.plot_grid_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)

        row += 1

        # Legende anzeigen
        self.plot_legend_var = tk.BooleanVar()
        ttk.Checkbutton(
            parent,
            text="Legende anzeigen",
            variable=self.plot_legend_var
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)

        row += 1

        # DPI
        ttk.Label(parent, text="Plot-Auflösung (DPI):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.plot_dpi_var = tk.IntVar()
        ttk.Spinbox(
            parent,
            from_=50,
            to=300,
            increment=10,
            textvariable=self.plot_dpi_var,
            width=20
        ).grid(row=row, column=1, sticky=tk.W, pady=5)

        row += 1

        # Theme
        ttk.Label(parent, text="Plot-Theme:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.plot_theme_var = tk.StringVar()
        ttk.Combobox(
            parent,
            textvariable=self.plot_theme_var,
            values=['default', 'seaborn', 'ggplot', 'dark_background'],
            width=17,
            state='readonly'
        ).grid(row=row, column=1, sticky=tk.W, pady=5)

        parent.columnconfigure(1, weight=1)

    def _setup_advanced_tab(self, parent):
        """Setup Erweitert-Tab"""
        row = 0

        # Log-Level
        ttk.Label(parent, text="Log-Level:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.log_level_var = tk.StringVar()
        ttk.Combobox(
            parent,
            textvariable=self.log_level_var,
            values=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            width=17,
            state='readonly'
        ).grid(row=row, column=1, sticky=tk.W, pady=5)

        row += 1

        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=10)
        row += 1

        # Info-Text
        info_text = "Änderungen an erweiterten Einstellungen können einen Neustart erfordern."
        ttk.Label(
            parent,
            text=info_text,
            foreground='gray',
            wraplength=400
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)

        parent.columnconfigure(1, weight=1)

    def _load_settings(self):
        """Lade Einstellungen aus Config"""
        # Allgemein
        self.db_path_var.set(self.config_manager.get('database_path', 'measurements.db'))
        self.plugin_dir_var.set(self.config_manager.get('plugin_directory', 'plugins'))
        self.auto_save_var.set(self.config_manager.get('auto_save', True))
        self.max_history_var.set(self.config_manager.get('max_history', 1000))

        # Messung
        self.measurement_delay_var.set(self.config_manager.get('measurement_delay', 0.5))

        hardware = self.config_manager.get('hardware', {})
        self.hardware_timeout_var.set(hardware.get('timeout', 30))
        self.retry_count_var.set(hardware.get('retry_count', 3))
        self.serial_port_var.set(hardware.get('serial_port', 'COM1'))
        self.baud_rate_var.set(hardware.get('baud_rate', 9600))

        # Plot
        plot_settings = self.config_manager.get('plot_settings', {})
        self.plot_grid_var.set(plot_settings.get('grid', True))
        self.plot_legend_var.set(plot_settings.get('legend', True))
        self.plot_dpi_var.set(plot_settings.get('dpi', 100))
        self.plot_theme_var.set(plot_settings.get('theme', 'default'))

        # Erweitert
        logging_config = self.config_manager.get('logging', {})
        self.log_level_var.set(logging_config.get('level', 'INFO'))

    def browse_database(self):
        """Durchsuche nach Datenbank-Datei"""
        filepath = filedialog.asksaveasfilename(
            title="Datenbank-Datei",
            filetypes=[("SQLite-Datenbank", "*.db"), ("Alle Dateien", "*.*")],
            defaultextension=".db"
        )
        if filepath:
            self.db_path_var.set(filepath)

    def browse_plugin_dir(self):
        """Durchsuche nach Plugin-Verzeichnis"""
        directory = filedialog.askdirectory(title="Plugin-Verzeichnis")
        if directory:
            self.plugin_dir_var.set(directory)

    def apply(self):
        """Wende Einstellungen an"""
        try:
            # Allgemein
            self.config_manager.set('database_path', self.db_path_var.get())
            self.config_manager.set('plugin_directory', self.plugin_dir_var.get())
            self.config_manager.set('auto_save', self.auto_save_var.get())
            self.config_manager.set('max_history', self.max_history_var.get())

            # Messung
            self.config_manager.set('measurement_delay', self.measurement_delay_var.get())

            hardware = self.config_manager.get('hardware', {})
            hardware['timeout'] = self.hardware_timeout_var.get()
            hardware['retry_count'] = self.retry_count_var.get()
            hardware['serial_port'] = self.serial_port_var.get()
            hardware['baud_rate'] = self.baud_rate_var.get()
            self.config_manager.set('hardware', hardware)

            # Plot
            plot_settings = self.config_manager.get('plot_settings', {})
            plot_settings['grid'] = self.plot_grid_var.get()
            plot_settings['legend'] = self.plot_legend_var.get()
            plot_settings['dpi'] = self.plot_dpi_var.get()
            plot_settings['theme'] = self.plot_theme_var.get()
            self.config_manager.set('plot_settings', plot_settings)

            # Erweitert
            logging_config = self.config_manager.get('logging', {})
            logging_config['level'] = self.log_level_var.get()
            self.config_manager.set('logging', logging_config)

            # Speichere Konfiguration
            self.config_manager.save()

            messagebox.showinfo("Erfolg", "Einstellungen wurden übernommen")

        except Exception as e:
            messagebox.showerror("Fehler", f"Einstellungen konnten nicht übernommen werden:\n{e}")
            logger.error(f"Fehler beim Übernehmen der Einstellungen: {e}")

    def save_and_close(self):
        """Speichere und schließe"""
        self.apply()
        self.dialog.destroy()

    def cancel(self):
        """Abbrechen"""
        # Stelle ursprüngliche Konfiguration wieder her
        self.config_manager.config = self.original_config
        self.dialog.destroy()

    def reset_to_defaults(self):
        """Setze auf Standardwerte zurück"""
        response = messagebox.askyesno(
            "Bestätigung",
            "Wirklich alle Einstellungen auf Standardwerte zurücksetzen?"
        )
        if response:
            self.config_manager.config = self.config_manager._get_default_config()
            self._load_settings()
            messagebox.showinfo("Info", "Einstellungen auf Standardwerte zurückgesetzt")
