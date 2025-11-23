"""
GUI für Datenvisualisierung - VOLLSTÄNDIG
Mit Zeitstempel-Unterstützung auf X-Achse
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

# Matplotlib-Integration
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    import matplotlib.dates as mdates
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib nicht verfuegbar - Visualisierung eingeschraenkt")

logger = logging.getLogger(__name__)


class DataVisualization:
    """Visualisierung von Messdaten"""

    def __init__(self, parent, database_manager):
        self.database_manager = database_manager
        self.frame = ttk.Frame(parent)

        self.current_sequence = None
        self.current_data = []

        self._setup_ui()

    def _setup_ui(self):
        """Erstelle UI"""
        # Toolbar
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="Sequenz:").pack(side=tk.LEFT, padx=5)

        self.sequence_combo = ttk.Combobox(toolbar, width=30, state='readonly')
        self.sequence_combo.pack(side=tk.LEFT, padx=5)
        self.sequence_combo.bind('<<ComboboxSelected>>', self.on_sequence_selected)

        ttk.Button(
            toolbar,
            text="Aktualisieren",
            command=self.refresh_sequences
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            toolbar,
            text="Plot aktualisieren",
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        # Plot-Optionen
        options_frame = ttk.LabelFrame(self.frame, text="Plot-Optionen", padding=5)
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        # Erste Zeile: Plot-Typ und Optionen
        row1 = ttk.Frame(options_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="Plot-Typ:").pack(side=tk.LEFT, padx=5)

        self.plot_type = tk.StringVar(value="line")
        ttk.Radiobutton(
            row1,
            text="Linie",
            variable=self.plot_type,
            value="line",
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            row1,
            text="Scatter",
            variable=self.plot_type,
            value="scatter",
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            row1,
            text="Bar",
            variable=self.plot_type,
            value="bar",
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            row1,
            text="Gitter",
            variable=self.grid_var,
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        # Zeitstempel-Option
        self.timestamp_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            row1,
            text="Zeitstempel auf X-Achse",
            variable=self.timestamp_var,
            command=self._on_timestamp_toggle
        ).pack(side=tk.LEFT, padx=5)

        # Parameter-Auswahl
        param_frame = ttk.LabelFrame(self.frame, text="Parameter", padding=5)
        param_frame.pack(fill=tk.X, padx=5, pady=5)

        # X-Achse
        x_frame = ttk.Frame(param_frame)
        x_frame.pack(fill=tk.X, pady=2)

        ttk.Label(x_frame, text="X-Achse:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.x_param_combo = ttk.Combobox(x_frame, width=25, state='readonly')
        self.x_param_combo.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        self.x_param_combo.bind('<<ComboboxSelected>>', lambda e: self.update_plot())

        self.x_info_label = ttk.Label(x_frame, text="", foreground='gray')
        self.x_info_label.grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)

        # Y-Achse
        y_frame = ttk.Frame(param_frame)
        y_frame.pack(fill=tk.X, pady=2)

        ttk.Label(y_frame, text="Y-Achse:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.y_param_combo = ttk.Combobox(y_frame, width=25, state='readonly')
        self.y_param_combo.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        self.y_param_combo.bind('<<ComboboxSelected>>', lambda e: self.update_plot())

        self.y_info_label = ttk.Label(y_frame, text="", foreground='gray')
        self.y_info_label.grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)

        if MATPLOTLIB_AVAILABLE:
            # Matplotlib-Figure
            self.figure = Figure(figsize=(8, 6), dpi=100)
            self.ax = self.figure.add_subplot(111)

            self.canvas = FigureCanvasTkAgg(self.figure, self.frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Toolbar
            toolbar_frame = ttk.Frame(self.frame)
            toolbar_frame.pack(fill=tk.X)
            self.mpl_toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
            self.mpl_toolbar.update()
        else:
            # Fallback ohne Matplotlib
            fallback_label = ttk.Label(
                self.frame,
                text="Matplotlib nicht verfuegbar.\nBitte installieren Sie matplotlib fuer Visualisierung.",
                justify=tk.CENTER
            )
            fallback_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Statistik-Frame
        stats_frame = ttk.LabelFrame(self.frame, text="Statistik", padding=5)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_text = tk.Text(stats_frame, height=4, wrap=tk.WORD)
        self.stats_text.pack(fill=tk.X)

        # Lade verfügbare Sequenzen
        self.refresh_sequences()

    def _on_timestamp_toggle(self):
        """Callback wenn Zeitstempel-Option geändert wird"""
        if self.timestamp_var.get():
            # Zeitstempel aktiviert - deaktiviere X-Parameter Auswahl
            self.x_param_combo.config(state='disabled')
            self.x_info_label.config(text="(Zeitstempel wird verwendet)")
        else:
            # Zeitstempel deaktiviert - aktiviere X-Parameter Auswahl
            self.x_param_combo.config(state='readonly')
            self.x_info_label.config(text="")

        self.update_plot()

    def refresh_sequences(self):
        """Aktualisiere Sequenz-Liste"""
        sequences = self.database_manager.get_all_sequences()
        self.sequence_combo['values'] = sequences

        if sequences and not self.current_sequence:
            self.sequence_combo.current(0)
            self.on_sequence_selected(None)

    def on_sequence_selected(self, event):
        """Sequenz wurde ausgewählt"""
        self.current_sequence = self.sequence_combo.get()
        if self.current_sequence:
            self.load_sequence_data()

    def load_sequence_data(self):
        """Lade Daten der ausgewählten Sequenz"""
        try:
            self.current_data = self.database_manager.get_sequence_data(self.current_sequence)
            self.update_parameter_lists()
            self.update_plot()
            logger.info(f"Daten geladen: {self.current_sequence}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Daten:\n{e}")
            logger.error(f"Fehler beim Laden: {e}")

    def update_parameter_lists(self):
        """Aktualisiere Parameter-Listen"""
        if not self.current_data:
            return

        # Sammle alle verfügbaren Parameter
        all_params = set()

        for point in self.current_data:
            # Parameter aus den Eingabeparametern
            all_params.update(point['parameters'].keys())

            # Parameter aus den Messwerten
            for plugin_values in point['values'].values():
                all_params.update(plugin_values.keys())

        params = sorted(list(all_params))

        # Füge "Zeitstempel" als Option hinzu
        params_with_time = ['[Zeitstempel]'] + params

        self.x_param_combo['values'] = params_with_time
        self.y_param_combo['values'] = params

        if params:
            # Wähle automatisch sinnvolle Defaults
            if not self.x_param_combo.get():
                # Wenn nur ein Parameter: Zeitstempel auf X
                if len(params) == 1:
                    self.x_param_combo.set('[Zeitstempel]')
                    self.timestamp_var.set(True)
                    self.x_param_combo.config(state='disabled')
                else:
                    self.x_param_combo.current(1)  # Erster echter Parameter

            if not self.y_param_combo.get():
                # Suche nach typischen Messwerten
                typical_params = ['temperature', 'voltage', 'current', 'value']
                y_selected = False

                for typ_param in typical_params:
                    for param in params:
                        if typ_param in param.lower():
                            idx = params.index(param)
                            self.y_param_combo.current(idx)
                            y_selected = True
                            break
                    if y_selected:
                        break

                if not y_selected:
                    # Nimm den zweiten Parameter oder ersten wenn nur einer
                    if len(params) > 1:
                        self.y_param_combo.current(1)
                    else:
                        self.y_param_combo.current(0)

    def update_plot(self):
        """Aktualisiere Plot"""
        if not MATPLOTLIB_AVAILABLE:
            return

        if not self.current_data:
            return

        use_timestamp = self.timestamp_var.get()

        if use_timestamp:
            x_param = None
            x_label = "Zeitstempel"
        else:
            x_param = self.x_param_combo.get()
            if x_param == '[Zeitstempel]':
                use_timestamp = True
                x_param = None
                x_label = "Zeitstempel"
            else:
                x_label = x_param

        y_param = self.y_param_combo.get()

        if not y_param:
            return

        if not use_timestamp and not x_param:
            return

        try:
            # Extrahiere Daten
            x_data = []
            y_data = []
            timestamps = []

            for point in self.current_data:
                if use_timestamp:
                    # Verwende Zeitstempel
                    try:
                        timestamp_str = point.get('timestamp', '')
                        if timestamp_str:
                            # Parse ISO-Format: 2024-01-01T12:00:00
                            dt = datetime.fromisoformat(timestamp_str)
                            timestamps.append(dt)
                        else:
                            continue
                    except Exception as e:
                        logger.warning(f"Konnte Zeitstempel nicht parsen: {e}")
                        continue
                else:
                    # Verwende Parameter-Wert
                    x_val = self._get_parameter_value(point, x_param)
                    if x_val is None:
                        continue
                    x_data.append(x_val)

                # Y-Wert
                y_val = self._get_parameter_value(point, y_param)
                if y_val is None:
                    continue
                y_data.append(y_val)

            if use_timestamp:
                if not timestamps or not y_data:
                    logger.warning("Keine Daten zum Plotten")
                    return

                if len(timestamps) != len(y_data):
                    # Kürze auf gleiche Länge
                    min_len = min(len(timestamps), len(y_data))
                    timestamps = timestamps[:min_len]
                    y_data = y_data[:min_len]

                x_plot_data = timestamps
            else:
                if not x_data or not y_data:
                    logger.warning("Keine Daten zum Plotten")
                    return
                x_plot_data = x_data

            # Plot erstellen
            self.ax.clear()

            plot_type = self.plot_type.get()

            if plot_type == "line":
                if use_timestamp:
                    self.ax.plot(x_plot_data, y_data, marker='o', linestyle='-', linewidth=2)
                else:
                    self.ax.plot(x_plot_data, y_data, marker='o', linestyle='-', linewidth=2)

            elif plot_type == "scatter":
                if use_timestamp:
                    self.ax.scatter(x_plot_data, y_data, s=50, alpha=0.6)
                else:
                    self.ax.scatter(x_plot_data, y_data, s=50, alpha=0.6)

            elif plot_type == "bar":
                if use_timestamp:
                    # Bar-Plot mit Zeitstempel ist schwierig - verwende Index
                    x_indices = range(len(y_data))
                    self.ax.bar(x_indices, y_data)
                    # Setze Labels
                    if len(timestamps) <= 20:
                        self.ax.set_xticks(x_indices)
                        labels = [ts.strftime("%H:%M:%S") for ts in timestamps]
                        self.ax.set_xticklabels(labels, rotation=45, ha='right')
                else:
                    self.ax.bar(range(len(y_data)), y_data)
                    self.ax.set_xticks(range(len(y_data)))
                    self.ax.set_xticklabels([f"{x:.2f}" for x in x_plot_data], rotation=45, ha='right')

            # Achsenbeschriftungen
            if use_timestamp:
                self.ax.set_xlabel("Zeitstempel")
                # Formatiere X-Achse für Zeitstempel
                if plot_type != "bar":
                    self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                    self.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    self.figure.autofmt_xdate()  # Rotiere Zeitstempel
            else:
                self.ax.set_xlabel(x_label)

            self.ax.set_ylabel(y_param)
            self.ax.set_title(f"{self.current_sequence}")

            if self.grid_var.get():
                self.ax.grid(True, alpha=0.3)

            self.figure.tight_layout()
            self.canvas.draw()

            # Statistik berechnen
            self.update_statistics(y_data, y_param)

        except Exception as e:
            logger.error(f"Plot-Fehler: {e}", exc_info=True)
            messagebox.showerror("Fehler", f"Fehler beim Plotten:\n{e}")

    def _get_parameter_value(self, point, param_name):
        """Hole Parameterwert aus Datenpunkt"""
        # Prüfe Eingabeparameter
        if param_name in point['parameters']:
            return point['parameters'][param_name]

        # Prüfe Messwerte
        for plugin_values in point['values'].values():
            if param_name in plugin_values:
                return plugin_values[param_name]['value']

        return None

    def update_statistics(self, data, param_name):
        """Aktualisiere Statistik-Anzeige"""
        if not data:
            return

        if MATPLOTLIB_AVAILABLE:
            try:
                data_array = np.array(data)

                stats = f"Parameter: {param_name}\n"
                stats += f"Anzahl: {len(data)}  |  "
                stats += f"Mittelwert: {np.mean(data_array):.4f}  |  "
                stats += f"Std.abw.: {np.std(data_array):.4f}\n"
                stats += f"Min: {np.min(data_array):.4f}  |  "
                stats += f"Max: {np.max(data_array):.4f}  |  "
                stats += f"Median: {np.median(data_array):.4f}"
            except:
                # Fallback
                stats = self._calculate_basic_stats(data, param_name)
        else:
            stats = self._calculate_basic_stats(data, param_name)

        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert('1.0', stats)

    def _calculate_basic_stats(self, data, param_name):
        """Berechne Basis-Statistiken ohne NumPy"""
        stats = f"Parameter: {param_name}\n"
        stats += f"Anzahl: {len(data)}  |  "
        stats += f"Min: {min(data):.4f}  |  "
        stats += f"Max: {max(data):.4f}\n"

        mean = sum(data) / len(data)
        stats += f"Mittelwert: {mean:.4f}"

        return stats
