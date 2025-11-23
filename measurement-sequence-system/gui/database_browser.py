"""
GUI für Datenbank-Browser
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import json
import csv
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseBrowser:
    """Browser für Messdatenbank"""

    def __init__(self, parent, database_manager):
        self.database_manager = database_manager
        self.frame = ttk.Frame(parent)

        self._setup_ui()
        self.refresh()

    def _setup_ui(self):
        """Erstelle UI"""
        # Toolbar
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            toolbar,
            text="Aktualisieren",
            command=self.refresh
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Exportieren",
            command=self.export_data
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Löschen",
            command=self.delete_sequence
        ).pack(side=tk.LEFT, padx=2)

        # Sequenz-Auswahl
        select_frame = ttk.Frame(self.frame)
        select_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(select_frame, text="Sequenz:").pack(side=tk.LEFT, padx=5)

        self.sequence_combo = ttk.Combobox(select_frame, width=30, state='readonly')
        self.sequence_combo.pack(side=tk.LEFT, padx=5)
        self.sequence_combo.bind('<<ComboboxSelected>>', self.on_sequence_selected)

        # Daten-Treeview
        data_frame = ttk.LabelFrame(self.frame, text="Messdaten", padding=5)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('timestamp', 'point', 'parameter', 'value', 'unit')
        self.data_tree = ttk.Treeview(data_frame, columns=columns, show='headings')

        self.data_tree.heading('timestamp', text='Zeitstempel')
        self.data_tree.heading('point', text='Messpunkt')
        self.data_tree.heading('parameter', text='Parameter')
        self.data_tree.heading('value', text='Wert')
        self.data_tree.heading('unit', text='Einheit')

        self.data_tree.column('timestamp', width=150)
        self.data_tree.column('point', width=120)
        self.data_tree.column('parameter', width=150)
        self.data_tree.column('value', width=100)
        self.data_tree.column('unit', width=80)

        scrollbar_y = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        scrollbar_x = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.data_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')

        data_frame.rowconfigure(0, weight=1)
        data_frame.columnconfigure(0, weight=1)

        # Statistik
        stats_frame = ttk.Frame(self.frame)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_label = ttk.Label(stats_frame, text="Keine Daten")
        self.stats_label.pack(side=tk.LEFT)

    def refresh(self):
        """Aktualisiere Sequenz-Liste"""
        sequences = self.database_manager.get_all_sequences()
        self.sequence_combo['values'] = sequences

        if sequences:
            self.sequence_combo.current(0)
            self.on_sequence_selected(None)

        self.stats_label.config(text=f"Sequenzen in Datenbank: {len(sequences)}")

    def on_sequence_selected(self, event):
        """Sequenz wurde ausgewählt"""
        sequence_name = self.sequence_combo.get()
        if sequence_name:
            self.load_sequence_data(sequence_name)

    def load_sequence_data(self, sequence_name):
        """Lade Sequenzdaten"""
        try:
            self.data_tree.delete(*self.data_tree.get_children())

            data = self.database_manager.get_sequence_data(sequence_name)

            total_values = 0
            for point in data:
                timestamp = point['timestamp']
                point_name = point['point_name']

                for plugin_name, plugin_values in point['values'].items():
                    for param_name, param_data in plugin_values.items():
                        value = param_data.get('value', '-')
                        unit = param_data.get('unit', '')

                        self.data_tree.insert('', tk.END, values=(
                            timestamp,
                            point_name,
                            f"{plugin_name}.{param_name}",
                            f"{value:.4f}" if isinstance(value, float) else value,
                            unit
                        ))
                        total_values += 1

            self.stats_label.config(
                text=f"Sequenz: {sequence_name} | Messpunkte: {len(data)} | Messwerte: {total_values}"
            )

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden:\n{e}")
            logger.error(f"Fehler beim Laden: {e}")

    def export_data(self):
        """Exportiere Daten als CSV"""
        sequence_name = self.sequence_combo.get()
        if not sequence_name:
            messagebox.showinfo("Info", "Bitte Sequenz auswählen")
            return

        filepath = filedialog.asksaveasfilename(
            title="Daten exportieren",
            defaultextension=".csv",
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")]
        )

        if not filepath:
            return

        try:
            data = self.database_manager.get_sequence_data(sequence_name)

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Zeitstempel', 'Messpunkt', 'Parameter', 'Wert', 'Einheit'])

                for point in data:
                    timestamp = point['timestamp']
                    point_name = point['point_name']

                    for plugin_name, plugin_values in point['values'].items():
                        for param_name, param_data in plugin_values.items():
                            value = param_data.get('value', '')
                            unit = param_data.get('unit', '')

                            writer.writerow([
                                timestamp,
                                point_name,
                                f"{plugin_name}.{param_name}",
                                value,
                                unit
                            ])

            messagebox.showinfo("Erfolg", f"Daten exportiert nach:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")
            logger.error(f"Export-Fehler: {e}")

    def delete_sequence(self):
        """Lösche Sequenz aus Datenbank"""
        sequence_name = self.sequence_combo.get()
        if not sequence_name:
            messagebox.showinfo("Info", "Bitte Sequenz auswählen")
            return

        response = messagebox.askyesno(
            "Bestätigung",
            f"Sequenz '{sequence_name}' wirklich löschen?\nAlle Messdaten gehen verloren!"
        )

        if response:
            try:
                self.database_manager.delete_sequence(sequence_name)
                self.refresh()
                messagebox.showinfo("Erfolg", "Sequenz gelöscht")
            except Exception as e:
                messagebox.showerror("Fehler", f"Löschen fehlgeschlagen:\n{e}")
                logger.error(f"Lösch-Fehler: {e}")
