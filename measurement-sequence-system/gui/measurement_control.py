"""
GUI für Messsteuerung und -überwachung
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class MeasurementControl:
    """Steuerung und Überwachung von Messungen"""

    def __init__(self, parent, sequence_manager):
        self.sequence_manager = sequence_manager
        self.frame = ttk.Frame(parent)

        self._setup_ui()
        self._register_callbacks()

    def _setup_ui(self):
        """Erstelle UI"""
        # Steuerungs-Frame
        control_frame = ttk.LabelFrame(self.frame, text="Steuerung", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Buttons
        button_container = ttk.Frame(control_frame)
        button_container.pack(fill=tk.X)

        self.start_button = ttk.Button(
            button_container,
            text="▶ Start",
            command=self.start_measurement,
            width=15
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = ttk.Button(
            button_container,
            text="⏸ Pause",
            command=self.pause_measurement,
            state=tk.DISABLED,
            width=15
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            button_container,
            text="⏹ Stop",
            command=self.stop_measurement,
            state=tk.DISABLED,
            width=15
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Status-Frame
        status_frame = ttk.LabelFrame(self.frame, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        # Status-Informationen
        info_grid = ttk.Frame(status_frame)
        info_grid.pack(fill=tk.X)

        ttk.Label(info_grid, text="Sequenz:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sequence_label = ttk.Label(info_grid, text="-", foreground="blue")
        self.sequence_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=10)

        ttk.Label(info_grid, text="Status:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.status_label = ttk.Label(info_grid, text="Bereit", foreground="green")
        self.status_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=10)

        ttk.Label(info_grid, text="Fortschritt:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.progress_label = ttk.Label(info_grid, text="0 / 0")
        self.progress_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=10)

        ttk.Label(info_grid, text="Aktueller Punkt:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.current_point_label = ttk.Label(info_grid, text="-")
        self.current_point_label.grid(row=3, column=1, sticky=tk.W, pady=2, padx=10)

        ttk.Label(info_grid, text="Verstrichene Zeit:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.time_label = ttk.Label(info_grid, text="00:00:00")
        self.time_label.grid(row=4, column=1, sticky=tk.W, pady=2, padx=10)

        # Fortschrittsbalken
        self.progress_bar = ttk.Progressbar(
            status_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=10)

        # Log-Frame
        log_frame = ttk.LabelFrame(self.frame, text="Messprotokoll", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Log-Textfeld
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Aktuelle Messwerte
        values_frame = ttk.LabelFrame(self.frame, text="Aktuelle Messwerte", padding=10)
        values_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview für Messwerte
        columns = ('parameter', 'value', 'unit', 'plugin')
        self.values_tree = ttk.Treeview(values_frame, columns=columns, show='headings', height=8)

        self.values_tree.heading('parameter', text='Parameter')
        self.values_tree.heading('value', text='Wert')
        self.values_tree.heading('unit', text='Einheit')
        self.values_tree.heading('plugin', text='Plugin')

        self.values_tree.column('parameter', width=150)
        self.values_tree.column('value', width=100)
        self.values_tree.column('unit', width=80)
        self.values_tree.column('plugin', width=120)

        values_scrollbar = ttk.Scrollbar(values_frame, command=self.values_tree.yview)
        self.values_tree.configure(yscrollcommand=values_scrollbar.set)

        self.values_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        values_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Zeit-Tracking
        self.start_time = None
        self.time_update_job = None

    def _register_callbacks(self):
        """Registriere Callbacks beim SequenceManager"""
        self.sequence_manager.register_callback('on_start', self.on_sequence_start)
        self.sequence_manager.register_callback('on_point_complete', self.on_point_complete)
        self.sequence_manager.register_callback('on_complete', self.on_sequence_complete)
        self.sequence_manager.register_callback('on_error', self.on_error)
        self.sequence_manager.register_callback('on_progress', self.on_progress)

    def start_measurement(self):
        """Starte Messung"""
        if not self.sequence_manager.current_sequence:
            messagebox.showwarning("Warnung", "Keine Sequenz geladen")
            return

        if not self.sequence_manager.current_sequence.measurement_points:
            messagebox.showwarning("Warnung", "Keine Messpunkte definiert")
            return

        if not self.sequence_manager.current_sequence.active_plugins:
            messagebox.showwarning("Warnung", "Keine Plugins ausgewählt")
            return

        try:
            self.sequence_manager.start_sequence()
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.NORMAL)

            self.status_label.config(text="Läuft...", foreground="orange")
            self.log_message("Messung gestartet")

        except Exception as e:
            messagebox.showerror("Fehler", f"Messung konnte nicht gestartet werden:\n{e}")
            logger.error(f"Start-Fehler: {e}")

    def pause_measurement(self):
        """Pausiere/Fortsetzen Messung"""
        if self.sequence_manager.is_paused:
            self.sequence_manager.resume()
            self.pause_button.config(text="⏸ Pause")
            self.status_label.config(text="Läuft...", foreground="orange")
            self.log_message("Messung fortgesetzt")
        else:
            self.sequence_manager.pause()
            self.pause_button.config(text="▶ Fortsetzen")
            self.status_label.config(text="Pausiert", foreground="blue")
            self.log_message("Messung pausiert")

    def stop_measurement(self):
        """Stoppe Messung"""
        response = messagebox.askyesno(
            "Bestätigung",
            "Messung wirklich abbrechen?"
        )
        if response:
            self.sequence_manager.stop()
            self.reset_ui()
            self.log_message("Messung abgebrochen")

    def on_sequence_start(self, sequence):
        """Callback: Sequenz gestartet"""
        self.frame.after(0, lambda: self._update_sequence_start(sequence))

    def _update_sequence_start(self, sequence):
        """UI-Update für Sequenzstart"""
        self.sequence_label.config(text=sequence.name)
        total = len(sequence.measurement_points)
        self.progress_label.config(text=f"0 / {total}")
        self.progress_bar['maximum'] = total
        self.progress_bar['value'] = 0

        self.start_time = datetime.now()
        self.update_elapsed_time()

    def on_point_complete(self, point):
        """Callback: Messpunkt abgeschlossen"""
        self.frame.after(0, lambda: self._update_point_complete(point))

    def _update_point_complete(self, point):
        """UI-Update für Messpunkt"""
        self.current_point_label.config(text=point.name)
        self.log_message(f"Messpunkt abgeschlossen: {point.name}")

        # Zeige Messwerte
        self.display_measurement_values(point.results)

    def on_progress(self, current, total, percentage):
        """Callback: Fortschritt"""
        self.frame.after(0, lambda: self._update_progress(current, total, percentage))

    def _update_progress(self, current, total, percentage):
        """UI-Update für Fortschritt"""
        self.progress_label.config(text=f"{current} / {total}")
        self.progress_bar['value'] = current

    def on_sequence_complete(self, sequence):
        """Callback: Sequenz abgeschlossen"""
        self.frame.after(0, lambda: self._update_sequence_complete(sequence))

    def _update_sequence_complete(self, sequence):
        """UI-Update für Sequenzende"""
        self.status_label.config(text="Abgeschlossen", foreground="green")
        self.log_message(f"Sequenz abgeschlossen: {sequence.name}")
        self.reset_ui()
        messagebox.showinfo("Erfolg", "Messung erfolgreich abgeschlossen!")

    def on_error(self, error):
        """Callback: Fehler aufgetreten"""
        self.frame.after(0, lambda: self._update_error(error))

    def _update_error(self, error):
        """UI-Update für Fehler"""
        self.status_label.config(text="Fehler", foreground="red")
        self.log_message(f"FEHLER: {error}", level="ERROR")
        self.reset_ui()
        messagebox.showerror("Fehler", f"Fehler bei Messung:\n{error}")

    def display_measurement_values(self, results):
        """Zeige aktuelle Messwerte"""
        self.values_tree.delete(*self.values_tree.get_children())

        for plugin_name, plugin_results in results.items():
            if isinstance(plugin_results, dict):
                unit_info = plugin_results.get('unit_info', {})

                for param_name, value in plugin_results.items():
                    if param_name == 'unit_info':
                        continue

                    unit = unit_info.get(param_name, "")

                    if isinstance(value, (int, float)):
                        value_str = f"{value:.4f}"
                    elif isinstance(value, bytes):
                        value_str = f"<Binär: {len(value)} Bytes>"
                    else:
                        value_str = str(value)

                    self.values_tree.insert('', tk.END, values=(
                        param_name,
                        value_str,
                        unit,
                        plugin_name
                    ))

    def log_message(self, message, level="INFO"):
        """Füge Nachricht zum Log hinzu"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"

        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)

        # Farbcodierung
        if level == "ERROR":
            start_idx = self.log_text.index(f"end-{len(log_entry)+1}c")
            end_idx = self.log_text.index("end-1c")
            self.log_text.tag_add("error", start_idx, end_idx)
            self.log_text.tag_config("error", foreground="red")

    def update_elapsed_time(self):
        """Aktualisiere verstrichene Zeit"""
        if self.start_time and self.sequence_manager.is_running():
            elapsed = datetime.now() - self.start_time
            hours, remainder = divmod(elapsed.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.time_label.config(text=time_str)

            # Aktualisiere jede Sekunde
            self.time_update_job = self.frame.after(1000, self.update_elapsed_time)

    def reset_ui(self):
        """Setze UI zurück"""
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="⏸ Pause")
        self.stop_button.config(state=tk.DISABLED)

        if self.time_update_job:
            self.frame.after_cancel(self.time_update_job)
            self.time_update_job = None

