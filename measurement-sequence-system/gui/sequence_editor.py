"""
GUI für Sequenz-Editor - VOLLSTÄNDIG
Alle Icons als Text, vollständig funktionsfähig
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import json
from core.sequence_manager import ParameterRange, MeasurementPoint

logger = logging.getLogger(__name__)


class SequenceEditor:
    """Editor für Messsequenzen"""

    def __init__(self, parent, sequence_manager, plugin_manager):
        self.sequence_manager = sequence_manager
        self.plugin_manager = plugin_manager
        self.frame = ttk.Frame(parent)

        # Tracking für Änderungen
        self.has_changes = False

        self._setup_ui()

    def _setup_ui(self):
        """Erstelle UI"""
        # Sequenz-Info
        info_frame = ttk.LabelFrame(self.frame, text="Sequenz-Informationen", padding=10)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(info_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_entry = ttk.Entry(info_frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, pady=2)
        self.name_entry.bind('<KeyRelease>', lambda e: self._mark_changed())

        ttk.Label(info_frame, text="Beschreibung:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.desc_entry = ttk.Entry(info_frame, width=40)
        self.desc_entry.grid(row=1, column=1, sticky=tk.EW, pady=2)
        self.desc_entry.bind('<KeyRelease>', lambda e: self._mark_changed())

        info_frame.columnconfigure(1, weight=1)

        # Buttons OBEN, damit sie immer sichtbar sind
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            button_frame,
            text="Neue Sequenz",
            command=self.new_sequence,
            width=20
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            button_frame,
            text=">> Messpunkte generieren <<",
            command=self.generate_points,
            width=30
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            button_frame,
            text="Vorschau",
            command=self.preview_sequence,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        # Separator
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=5)

        # Notebook für Parameter und Messpunkte
        notebook = ttk.Notebook(self.frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab: Parameterbereiche
        param_frame = ttk.Frame(notebook)
        notebook.add(param_frame, text="Parameterbereiche")
        self._setup_parameter_tab(param_frame)

        # Tab: Messpunkte
        points_frame = ttk.Frame(notebook)
        notebook.add(points_frame, text="Messpunkte")
        self._setup_points_tab(points_frame)

        # Tab: Plugin-Auswahl
        plugins_frame = ttk.Frame(notebook)
        notebook.add(plugins_frame, text="Plugin-Auswahl")
        self._setup_plugins_tab(plugins_frame)

    def _setup_parameter_tab(self, parent):
        """Setup Parameter-Tab"""
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            toolbar,
            text="[+] Hinzufuegen",
            command=self.add_parameter_range,
            width=18
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Bearbeiten",
            command=self.edit_parameter_range,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="[-] Loeschen",
            command=self.delete_parameter_range,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        ttk.Button(
            toolbar,
            text="Nach oben",
            command=self.move_parameter_up,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Nach unten",
            command=self.move_parameter_down,
            width=12
        ).pack(side=tk.LEFT, padx=2)

        # Hilfetext
        help_frame = ttk.Frame(parent)
        help_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        ttk.Label(
            help_frame,
            text="Tipp: Doppelklick auf einen Eintrag zum Bearbeiten",
            foreground='gray',
            font=('', 8)
        ).pack(side=tk.LEFT)

        # Liste der Parameterbereiche
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('name', 'start', 'end', 'steps', 'unit')
        self.param_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)

        self.param_tree.heading('name', text='Parameter')
        self.param_tree.heading('start', text='Start')
        self.param_tree.heading('end', text='Ende')
        self.param_tree.heading('steps', text='Schritte')
        self.param_tree.heading('unit', text='Einheit')

        self.param_tree.column('name', width=150)
        self.param_tree.column('start', width=80)
        self.param_tree.column('end', width=80)
        self.param_tree.column('steps', width=80)
        self.param_tree.column('unit', width=80)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.param_tree.yview)
        self.param_tree.configure(yscrollcommand=scrollbar.set)

        self.param_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Doppelklick zum Bearbeiten
        self.param_tree.bind('<Double-1>', lambda e: self.edit_parameter_range())

        # Info-Label
        self.param_info_label = ttk.Label(
            parent,
            text="Keine Parameterbereiche definiert",
            foreground='gray'
        )
        self.param_info_label.pack(pady=5)

    def _setup_points_tab(self, parent):
        """Setup Messpunkte-Tab"""
        # Toolbar
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            toolbar,
            text="[+] Manuell hinzufuegen",
            command=self.add_measurement_point,
            width=22
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Bearbeiten",
            command=self.edit_measurement_point,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="[-] Loeschen",
            command=self.delete_measurement_point,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        ttk.Button(
            toolbar,
            text="Alle loeschen",
            command=self.clear_all_points,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        ttk.Label(toolbar, text="  |  ").pack(side=tk.LEFT)

        self.points_count_label = ttk.Label(
            toolbar,
            text="Anzahl Punkte: 0",
            font=('', 9, 'bold')
        )
        self.points_count_label.pack(side=tk.LEFT, padx=5)

        # Info-Box
        info_frame = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=2)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(
            info_frame,
            text="WICHTIG: Messpunkte werden automatisch aus Parameterbereichen generiert.\n"
                 "Klicken Sie auf 'Messpunkte generieren' nachdem Sie Parameterbereiche definiert haben.",
            foreground='blue',
            padding=10,
            wraplength=500
        ).pack()

        # Liste der Messpunkte
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('name', 'parameters')
        self.points_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)

        self.points_tree.heading('name', text='Name')
        self.points_tree.heading('parameters', text='Parameter')

        self.points_tree.column('name', width=150)
        self.points_tree.column('parameters', width=400)

        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.points_tree.yview)
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.points_tree.xview)
        self.points_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.points_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')

        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        # Doppelklick zum Bearbeiten
        self.points_tree.bind('<Double-1>', lambda e: self.edit_measurement_point())

    def _setup_plugins_tab(self, parent):
        """Setup Plugin-Auswahl-Tab mit Checkboxen"""
        # Scrollbarer Container
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Beschreibung
        desc_frame = ttk.Frame(main_frame, relief=tk.RIDGE, borderwidth=2)
        desc_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            desc_frame,
            text="PLUGIN-AUSWAHL",
            font=('', 11, 'bold'),
            padding=5
        ).pack(anchor=tk.W)

        ttk.Label(
            desc_frame,
            text="Waehlen Sie die Plugins aus, die in dieser Sequenz verwendet werden sollen.\n"
                 "Messgeraete-Plugins fuehren Messungen durch, Verarbeitungs-Plugins analysieren die Daten.",
            foreground='gray',
            padding=(5, 0, 5, 5),
            wraplength=500
        ).pack(anchor=tk.W)

        # Paned Window für beide Plugin-Typen
        paned = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Frame für Messgeräte-Plugins
        measurement_frame = ttk.LabelFrame(paned, text="Messgeraete-Plugins", padding=10)
        paned.add(measurement_frame, weight=1)

        # Toolbar für Messgeräte
        meas_toolbar = ttk.Frame(measurement_frame)
        meas_toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(
            meas_toolbar,
            text="Alle",
            command=lambda: self._select_all_plugins('measurement'),
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            meas_toolbar,
            text="Keine",
            command=lambda: self._deselect_all_plugins('measurement'),
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            meas_toolbar,
            text="Info",
            command=lambda: self._show_plugin_info('measurement'),
            width=10
        ).pack(side=tk.LEFT, padx=2)

        self.meas_count_label = ttk.Label(
            meas_toolbar,
            text="0 ausgewaehlt",
            foreground='blue'
        )
        self.meas_count_label.pack(side=tk.RIGHT, padx=5)

        # Scrollbare Liste mit Checkboxen für Messgeräte
        meas_canvas_frame = ttk.Frame(measurement_frame)
        meas_canvas_frame.pack(fill=tk.BOTH, expand=True)

        meas_canvas = tk.Canvas(meas_canvas_frame, height=150, highlightthickness=0)
        meas_scrollbar = ttk.Scrollbar(meas_canvas_frame, orient=tk.VERTICAL, command=meas_canvas.yview)
        self.meas_plugins_frame = ttk.Frame(meas_canvas)

        meas_canvas.configure(yscrollcommand=meas_scrollbar.set)

        meas_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        meas_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        meas_canvas_window = meas_canvas.create_window((0, 0), window=self.meas_plugins_frame, anchor=tk.NW)

        # Update scroll region
        def update_meas_scroll(event=None):
            meas_canvas.configure(scrollregion=meas_canvas.bbox("all"))
            width = meas_canvas.winfo_width()
            meas_canvas.itemconfig(meas_canvas_window, width=width)

        self.meas_plugins_frame.bind('<Configure>', update_meas_scroll)
        meas_canvas.bind('<Configure>', update_meas_scroll)

        # Frame für Verarbeitungs-Plugins
        processing_frame = ttk.LabelFrame(paned, text="Verarbeitungs-Plugins", padding=10)
        paned.add(processing_frame, weight=1)

        # Toolbar für Verarbeitung
        proc_toolbar = ttk.Frame(processing_frame)
        proc_toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(
            proc_toolbar,
            text="Alle",
            command=lambda: self._select_all_plugins('processing'),
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            proc_toolbar,
            text="Keine",
            command=lambda: self._deselect_all_plugins('processing'),
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            proc_toolbar,
            text="Info",
            command=lambda: self._show_plugin_info('processing'),
            width=10
        ).pack(side=tk.LEFT, padx=2)

        self.proc_count_label = ttk.Label(
            proc_toolbar,
            text="0 ausgewaehlt",
            foreground='blue'
        )
        self.proc_count_label.pack(side=tk.RIGHT, padx=5)

        # Scrollbare Liste mit Checkboxen für Verarbeitung
        proc_canvas_frame = ttk.Frame(processing_frame)
        proc_canvas_frame.pack(fill=tk.BOTH, expand=True)

        proc_canvas = tk.Canvas(proc_canvas_frame, height=150, highlightthickness=0)
        proc_scrollbar = ttk.Scrollbar(proc_canvas_frame, orient=tk.VERTICAL, command=proc_canvas.yview)
        self.proc_plugins_frame = ttk.Frame(proc_canvas)

        proc_canvas.configure(yscrollcommand=proc_scrollbar.set)

        proc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        proc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        proc_canvas_window = proc_canvas.create_window((0, 0), window=self.proc_plugins_frame, anchor=tk.NW)

        # Update scroll region
        def update_proc_scroll(event=None):
            proc_canvas.configure(scrollregion=proc_canvas.bbox("all"))
            width = proc_canvas.winfo_width()
            proc_canvas.itemconfig(proc_canvas_window, width=width)

        self.proc_plugins_frame.bind('<Configure>', update_proc_scroll)
        proc_canvas.bind('<Configure>', update_proc_scroll)

        # Dictionary für Plugin-Checkboxen
        self.measurement_plugin_vars = {}
        self.processing_plugin_vars = {}

        # Plugins laden
        self.refresh_plugin_lists()

    def refresh_plugin_lists(self):
        """Aktualisiere Plugin-Listen mit Checkboxen"""
        # Lösche alte Checkboxen
        for widget in self.meas_plugins_frame.winfo_children():
            widget.destroy()
        for widget in self.proc_plugins_frame.winfo_children():
            widget.destroy()

        self.measurement_plugin_vars.clear()
        self.processing_plugin_vars.clear()

        # Messgeräte-Plugins
        meas_plugins = self.plugin_manager.get_measurement_plugins()

        if not meas_plugins:
            ttk.Label(
                self.meas_plugins_frame,
                text="Keine Messgeraete-Plugins verfuegbar",
                foreground='gray'
            ).pack(anchor=tk.W, pady=5, padx=5)
        else:
            for plugin_name in sorted(meas_plugins):
                var = tk.BooleanVar()
                var.trace('w', lambda *args: self._update_plugin_counts())
                self.measurement_plugin_vars[plugin_name] = var

                # Frame für Checkbox und Info
                plugin_frame = ttk.Frame(self.meas_plugins_frame)
                plugin_frame.pack(fill=tk.X, pady=2, padx=5)

                cb = ttk.Checkbutton(
                    plugin_frame,
                    text=plugin_name,
                    variable=var,
                    command=self._mark_changed
                )
                cb.pack(side=tk.LEFT)

                # Info-Button
                info_btn = ttk.Button(
                    plugin_frame,
                    text="[i]",
                    width=4,
                    command=lambda pn=plugin_name: self._show_single_plugin_info(pn)
                )
                info_btn.pack(side=tk.RIGHT, padx=2)

        # Verarbeitungs-Plugins
        proc_plugins = self.plugin_manager.get_processing_plugins()

        if not proc_plugins:
            ttk.Label(
                self.proc_plugins_frame,
                text="Keine Verarbeitungs-Plugins verfuegbar",
                foreground='gray'
            ).pack(anchor=tk.W, pady=5, padx=5)
        else:
            for plugin_name in sorted(proc_plugins):
                var = tk.BooleanVar()
                var.trace('w', lambda *args: self._update_plugin_counts())
                self.processing_plugin_vars[plugin_name] = var

                # Frame für Checkbox und Info
                plugin_frame = ttk.Frame(self.proc_plugins_frame)
                plugin_frame.pack(fill=tk.X, pady=2, padx=5)

                cb = ttk.Checkbutton(
                    plugin_frame,
                    text=plugin_name,
                    variable=var,
                    command=self._mark_changed
                )
                cb.pack(side=tk.LEFT)

                # Info-Button
                info_btn = ttk.Button(
                    plugin_frame,
                    text="[i]",
                    width=4,
                    command=lambda pn=plugin_name: self._show_single_plugin_info(pn)
                )
                info_btn.pack(side=tk.RIGHT, padx=2)

        self._update_plugin_counts()

    def _update_plugin_counts(self):
        """Aktualisiere Anzahl ausgewählter Plugins"""
        meas_count = sum(1 for var in self.measurement_plugin_vars.values() if var.get())
        proc_count = sum(1 for var in self.processing_plugin_vars.values() if var.get())

        self.meas_count_label.config(text=f"{meas_count} ausgewaehlt")
        self.proc_count_label.config(text=f"{proc_count} ausgewaehlt")

    def _select_all_plugins(self, plugin_type):
        """Wähle alle Plugins eines Typs"""
        if plugin_type == 'measurement':
            for var in self.measurement_plugin_vars.values():
                var.set(True)
        else:
            for var in self.processing_plugin_vars.values():
                var.set(True)
        self._mark_changed()

    def _deselect_all_plugins(self, plugin_type):
        """Wähle keine Plugins eines Typs"""
        if plugin_type == 'measurement':
            for var in self.measurement_plugin_vars.values():
                var.set(False)
        else:
            for var in self.processing_plugin_vars.values():
                var.set(False)
        self._mark_changed()

    def _show_plugin_info(self, plugin_type):
        """Zeige Info über alle Plugins eines Typs"""
        if plugin_type == 'measurement':
            plugins = self.plugin_manager.get_measurement_plugins()
            title = "Messgeraete-Plugins"
        else:
            plugins = self.plugin_manager.get_processing_plugins()
            title = "Verarbeitungs-Plugins"

        if not plugins:
            messagebox.showinfo("Info", f"Keine {title} verfuegbar")
            return

        info_text = f"{title}:\n\n"

        available_plugins = self.plugin_manager.get_available_plugins()

        for plugin_name in sorted(plugins):
            plugin_info = available_plugins.get(plugin_name, {})
            description = plugin_info.get('description', 'Keine Beschreibung')
            version = plugin_info.get('version', '?')

            info_text += f"* {plugin_name} (v{version})\n"
            info_text += f"  {description}\n\n"

        # Erstelle Info-Fenster
        info_window = tk.Toplevel(self.frame)
        info_window.title(title)
        info_window.geometry("600x450")

        text = tk.Text(info_window, wrap=tk.WORD, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(info_window, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.insert('1.0', info_text)
        text.configure(state=tk.DISABLED)

        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(
            info_window,
            text="Schliessen",
            command=info_window.destroy
        ).pack(pady=5)

    def _show_single_plugin_info(self, plugin_name):
        """Zeige Info über ein einzelnes Plugin"""
        available_plugins = self.plugin_manager.get_available_plugins()
        plugin_info = available_plugins.get(plugin_name, {})

        info_text = f"Plugin: {plugin_name}\n\n"
        info_text += f"Version: {plugin_info.get('version', '?')}\n"
        info_text += f"Typ: {plugin_info.get('type', '?')}\n\n"
        info_text += f"Beschreibung:\n{plugin_info.get('description', 'Keine Beschreibung')}"

        messagebox.showinfo(f"Plugin-Info: {plugin_name}", info_text)

    def _mark_changed(self):
        """Markiere dass Änderungen vorgenommen wurden"""
        self.has_changes = True

    def new_sequence(self):
        """Erstelle neue Sequenz"""
        if self.has_changes:
            response = messagebox.askyesnocancel(
                "Ungespeicherte Aenderungen",
                "Es gibt ungespeicherte Aenderungen. Trotzdem fortfahren?"
            )
            if not response:
                return

        name = self.name_entry.get() or "Neue Sequenz"
        description = self.desc_entry.get()

        self.sequence_manager.create_sequence(name, description)
        self.clear_ui()
        self.has_changes = False
        logger.info(f"Neue Sequenz erstellt: {name}")
        messagebox.showinfo("Erfolg", "Neue Sequenz erstellt")

    def add_parameter_range(self):
        """Füge Parameterbereich hinzu"""
        dialog = ParameterRangeDialog(self.frame)
        if dialog.result:
            param_range = ParameterRange(**dialog.result)
            if self.sequence_manager.current_sequence:
                self.sequence_manager.current_sequence.add_parameter_range(param_range)
                self.refresh_parameter_list()
                self._mark_changed()

    def edit_parameter_range(self):
        """Bearbeite Parameterbereich"""
        selection = self.param_tree.selection()
        if not selection:
            messagebox.showwarning("Warnung", "Bitte einen Parameter auswaehlen")
            return

        index = self.param_tree.index(selection[0])
        if self.sequence_manager.current_sequence:
            param_range = self.sequence_manager.current_sequence.parameter_ranges[index]

            # Dialog mit Vorausfüllung
            dialog = ParameterRangeDialog(self.frame, {
                'parameter_name': param_range.parameter_name,
                'start': param_range.start,
                'end': param_range.end,
                'steps': param_range.steps,
                'unit': param_range.unit
            })

            if dialog.result:
                # Ersetze Parameter
                self.sequence_manager.current_sequence.parameter_ranges[index] = ParameterRange(**dialog.result)
                self.refresh_parameter_list()
                self._mark_changed()

    def delete_parameter_range(self):
        """Lösche Parameterbereich"""
        selection = self.param_tree.selection()
        if not selection:
            return

        response = messagebox.askyesno(
            "Bestaetigung",
            "Parameterbereich wirklich loeschen?"
        )
        if not response:
            return

        index = self.param_tree.index(selection[0])
        if self.sequence_manager.current_sequence:
            del self.sequence_manager.current_sequence.parameter_ranges[index]
            self.refresh_parameter_list()
            self._mark_changed()

    def move_parameter_up(self):
        """Verschiebe Parameter nach oben"""
        selection = self.param_tree.selection()
        if not selection:
            return

        index = self.param_tree.index(selection[0])
        if index > 0 and self.sequence_manager.current_sequence:
            ranges = self.sequence_manager.current_sequence.parameter_ranges
            ranges[index], ranges[index-1] = ranges[index-1], ranges[index]
            self.refresh_parameter_list()
            # Wähle verschobenes Element
            self.param_tree.selection_set(self.param_tree.get_children()[index-1])
            self._mark_changed()

    def move_parameter_down(self):
        """Verschiebe Parameter nach unten"""
        selection = self.param_tree.selection()
        if not selection:
            return

        index = self.param_tree.index(selection[0])
        if self.sequence_manager.current_sequence:
            ranges = self.sequence_manager.current_sequence.parameter_ranges
            if index < len(ranges) - 1:
                ranges[index], ranges[index+1] = ranges[index+1], ranges[index]
                self.refresh_parameter_list()
                # Wähle verschobenes Element
                self.param_tree.selection_set(self.param_tree.get_children()[index+1])
                self._mark_changed()

    def generate_points(self):
        """Generiere Messpunkte aus Parameterbereichen"""
        if not self.sequence_manager.current_sequence:
            messagebox.showwarning(
                "Warnung",
                "Keine Sequenz aktiv.\n\nBitte erstellen Sie zuerst eine neue Sequenz."
            )
            return

        if not self.sequence_manager.current_sequence.parameter_ranges:
            messagebox.showwarning(
                "Warnung",
                "Keine Parameterbereiche definiert.\n\n"
                "Bitte fuegen Sie im Tab 'Parameterbereiche' mindestens einen Bereich hinzu."
            )
            return

        # Bestätigung wenn bereits Punkte existieren
        if self.sequence_manager.current_sequence.measurement_points:
            response = messagebox.askyesno(
                "Bestaetigung",
                f"Es existieren bereits {len(self.sequence_manager.current_sequence.measurement_points)} Messpunkte.\n\n"
                "Diese werden durch neue Punkte ersetzt. Fortfahren?"
            )
            if not response:
                return

        try:
            self.sequence_manager.current_sequence.generate_measurement_points()
            self.refresh_points_list()
            self._mark_changed()

            num_points = len(self.sequence_manager.current_sequence.measurement_points)

            messagebox.showinfo(
                "Erfolg",
                f"{num_points} Messpunkte erfolgreich generiert!\n\n"
                f"Die Messpunkte sind im Tab 'Messpunkte' sichtbar."
            )
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Generieren der Messpunkte:\n\n{e}")
            logger.error(f"Fehler beim Generieren: {e}", exc_info=True)

    def add_measurement_point(self):
        """Füge manuellen Messpunkt hinzu"""
        dialog = MeasurementPointDialog(self.frame)
        if dialog.result:
            point = MeasurementPoint(dialog.result['name'], dialog.result['parameters'])
            if self.sequence_manager.current_sequence:
                self.sequence_manager.current_sequence.add_measurement_point(point)
                self.refresh_points_list()
                self._mark_changed()

    def edit_measurement_point(self):
        """Bearbeite Messpunkt"""
        selection = self.points_tree.selection()
        if not selection:
            messagebox.showwarning("Warnung", "Bitte einen Messpunkt auswaehlen")
            return

        index = self.points_tree.index(selection[0])
        if self.sequence_manager.current_sequence:
            point = self.sequence_manager.current_sequence.measurement_points[index]

            # Dialog mit Vorausfüllung
            dialog = MeasurementPointDialog(self.frame, {
                'name': point.name,
                'parameters': point.parameters
            })

            if dialog.result:
                # Ersetze Punkt
                self.sequence_manager.current_sequence.measurement_points[index] = MeasurementPoint(
                    dialog.result['name'],
                    dialog.result['parameters']
                )
                self.refresh_points_list()
                self._mark_changed()

    def delete_measurement_point(self):
        """Lösche Messpunkt"""
        selection = self.points_tree.selection()
        if not selection:
            return

        response = messagebox.askyesno(
            "Bestaetigung",
            "Messpunkt wirklich loeschen?"
        )
        if not response:
            return

        index = self.points_tree.index(selection[0])
        if self.sequence_manager.current_sequence:
            del self.sequence_manager.current_sequence.measurement_points[index]
            self.refresh_points_list()
            self._mark_changed()

    def clear_all_points(self):
        """Lösche alle Messpunkte"""
        if not self.sequence_manager.current_sequence:
            return

        if not self.sequence_manager.current_sequence.measurement_points:
            messagebox.showinfo("Info", "Keine Messpunkte vorhanden")
            return

        response = messagebox.askyesno(
            "Bestaetigung",
            f"Wirklich alle {len(self.sequence_manager.current_sequence.measurement_points)} Messpunkte loeschen?"
        )
        if response:
            self.sequence_manager.current_sequence.measurement_points.clear()
            self.refresh_points_list()
            self._mark_changed()

    def preview_sequence(self):
        """Zeige Sequenz-Vorschau"""
        if not self.sequence_manager.current_sequence:
            messagebox.showinfo("Info", "Keine Sequenz aktiv")
            return

        seq = self.sequence_manager.current_sequence

        # Erstelle Vorschau-Fenster
        preview_window = tk.Toplevel(self.frame)
        preview_window.title(f"Vorschau: {seq.name}")
        preview_window.geometry("700x600")

        # Text mit Scrollbar
        text_frame = ttk.Frame(preview_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text = tk.Text(text_frame, wrap=tk.WORD, padx=10, pady=10, font=('Courier', 10))
        scrollbar = ttk.Scrollbar(text_frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        # Erstelle Vorschau-Text
        preview_text = f"{'='*60}\n"
        preview_text += f"SEQUENZ: {seq.name}\n"
        preview_text += f"{'='*60}\n\n"

        if seq.description:
            preview_text += f"Beschreibung: {seq.description}\n\n"

        preview_text += f"{'-'*60}\n"
        preview_text += f"PARAMETERBEREICHE ({len(seq.parameter_ranges)}):\n"
        preview_text += f"{'-'*60}\n"

        if seq.parameter_ranges:
            for i, pr in enumerate(seq.parameter_ranges, 1):
                values = pr.get_values()
                preview_text += f"{i}. {pr.parameter_name}:\n"
                preview_text += f"   Bereich: {pr.start} bis {pr.end} {pr.unit}\n"
                preview_text += f"   Schritte: {pr.steps}\n"
                preview_text += f"   Werte: {', '.join([f'{v:.2f}' for v in values])}\n\n"
        else:
            preview_text += "   (keine definiert)\n\n"

        preview_text += f"{'-'*60}\n"
        preview_text += f"MESSPUNKTE ({len(seq.measurement_points)}):\n"
        preview_text += f"{'-'*60}\n"

        if seq.measurement_points:
            for i, point in enumerate(seq.measurement_points[:20], 1):  # Zeige max 20
                params = ", ".join([f"{k}={v}" for k, v in point.parameters.items()])
                preview_text += f"{i:3d}. {point.name}: {params}\n"

            if len(seq.measurement_points) > 20:
                preview_text += f"   ... und {len(seq.measurement_points) - 20} weitere\n"
        else:
            preview_text += "   (keine definiert - bitte generieren)\n"

        preview_text += f"\n{'-'*60}\n"
        preview_text += "AUSGEWAEHLTE PLUGINS:\n"
        preview_text += f"{'-'*60}\n"

        # Hole ausgewählte Plugins
        selected_meas = self.get_selected_measurement_plugins()
        selected_proc = self.get_selected_processing_plugins()

        preview_text += f"\nMessgeraete ({len(selected_meas)}):\n"
        if selected_meas:
            for plugin in selected_meas:
                preview_text += f"  * {plugin}\n"
        else:
            preview_text += "  (keine ausgewaehlt)\n"

        preview_text += f"\nVerarbeitung ({len(selected_proc)}):\n"
        if selected_proc:
            for plugin in selected_proc:
                preview_text += f"  * {plugin}\n"
        else:
            preview_text += "  (keine ausgewaehlt)\n"

        preview_text += f"\n{'='*60}\n"
        preview_text += f"Geschaetzte Messzeit: ca. {len(seq.measurement_points) * 0.5:.1f} Sekunden\n"
        preview_text += f"{'='*60}\n"

        text.insert('1.0', preview_text)
        text.configure(state=tk.DISABLED)

        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Button-Frame
        btn_frame = ttk.Frame(preview_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            btn_frame,
            text="Schliessen",
            command=preview_window.destroy
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            btn_frame,
            text="Als Text exportieren",
            command=lambda: self._export_preview(preview_text)
        ).pack(side=tk.RIGHT, padx=5)

    def _export_preview(self, text):
        """Exportiere Vorschau als Textdatei"""
        filepath = filedialog.asksaveasfilename(
            title="Vorschau exportieren",
            defaultextension=".txt",
            filetypes=[("Textdateien", "*.txt"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            messagebox.showinfo("Erfolg", f"Vorschau exportiert nach:\n{filepath}")

    def refresh_parameter_list(self):
        """Aktualisiere Parameter-Liste"""
        self.param_tree.delete(*self.param_tree.get_children())

        if self.sequence_manager.current_sequence:
            for pr in self.sequence_manager.current_sequence.parameter_ranges:
                self.param_tree.insert('', tk.END, values=(
                    pr.parameter_name,
                    pr.start,
                    pr.end,
                    pr.steps,
                    pr.unit
                ))

            if self.sequence_manager.current_sequence.parameter_ranges:
                self.param_info_label.config(
                    text=f"{len(self.sequence_manager.current_sequence.parameter_ranges)} Parameterbereiche definiert"
                )
            else:
                self.param_info_label.config(text="Keine Parameterbereiche definiert")

    def refresh_points_list(self):
        """Aktualisiere Messpunkte-Liste"""
        self.points_tree.delete(*self.points_tree.get_children())

        if self.sequence_manager.current_sequence:
            for point in self.sequence_manager.current_sequence.measurement_points:
                params_str = ", ".join([f"{k}={v}" for k, v in point.parameters.items()])
                self.points_tree.insert('', tk.END, values=(
                    point.name,
                    params_str
                ))

            # Update count
            count = len(self.sequence_manager.current_sequence.measurement_points)
            self.points_count_label.config(text=f"Anzahl Punkte: {count}")

    def get_selected_measurement_plugins(self):
        """Hole Liste der ausgewählten Messgeräte-Plugins"""
        return [name for name, var in self.measurement_plugin_vars.items() if var.get()]

    def get_selected_processing_plugins(self):
        """Hole Liste der ausgewählten Verarbeitungs-Plugins"""
        return [name for name, var in self.processing_plugin_vars.items() if var.get()]

    def load_current_sequence(self):
        """Lade aktuelle Sequenz in UI"""
        if not self.sequence_manager.current_sequence:
            return

        seq = self.sequence_manager.current_sequence

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, seq.name)

        self.desc_entry.delete(0, tk.END)
        self.desc_entry.insert(0, seq.description)

        self.refresh_parameter_list()
        self.refresh_points_list()

        # Plugins auswählen
        # Erst alle deaktivieren
        for var in self.measurement_plugin_vars.values():
            var.set(False)
        for var in self.processing_plugin_vars.values():
            var.set(False)

        # Dann ausgewählte aktivieren
        for plugin_name in seq.active_plugins:
            if plugin_name in self.measurement_plugin_vars:
                self.measurement_plugin_vars[plugin_name].set(True)

        for plugin_name in seq.processing_plugins:
            if plugin_name in self.processing_plugin_vars:
                self.processing_plugin_vars[plugin_name].set(True)

        self.has_changes = False

    def save_to_sequence_manager(self):
        """Speichere UI-Daten in Sequence Manager"""
        if not self.sequence_manager.current_sequence:
            return

        seq = self.sequence_manager.current_sequence
        seq.name = self.name_entry.get()
        seq.description = self.desc_entry.get()

        # Ausgewählte Plugins
        seq.active_plugins = self.get_selected_measurement_plugins()
        seq.processing_plugins = self.get_selected_processing_plugins()

        self.has_changes = False

    def clear_ui(self):
        """Leere UI"""
        self.name_entry.delete(0, tk.END)
        self.desc_entry.delete(0, tk.END)
        self.param_tree.delete(*self.param_tree.get_children())
        self.points_tree.delete(*self.points_tree.get_children())

        # Deaktiviere alle Plugin-Checkboxen
        for var in self.measurement_plugin_vars.values():
            var.set(False)
        for var in self.processing_plugin_vars.values():
            var.set(False)

        self.points_count_label.config(text="Anzahl Punkte: 0")
        self.param_info_label.config(text="Keine Parameterbereiche definiert")
        self.has_changes = False


class ParameterRangeDialog:
    """Dialog für Parameterbereich-Eingabe"""

    def __init__(self, parent, initial_values=None):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Parameterbereich")
        self.dialog.geometry("450x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Eingabefelder
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        row = 0

        ttk.Label(frame, text="Parameter-Name:", font=('', 9, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.name_entry = ttk.Entry(frame, width=30)
        self.name_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)

        row += 1

        ttk.Label(frame, text="Start-Wert:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.start_entry = ttk.Entry(frame, width=30)
        self.start_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)

        row += 1

        ttk.Label(frame, text="End-Wert:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.end_entry = ttk.Entry(frame, width=30)
        self.end_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)

        row += 1

        ttk.Label(frame, text="Anzahl Schritte:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.steps_entry = ttk.Entry(frame, width=30)
        self.steps_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)

        row += 1

        ttk.Label(frame, text="Einheit:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.unit_entry = ttk.Entry(frame, width=30)
        self.unit_entry.grid(row=row, column=1, pady=5, sticky=tk.EW)

        row += 1

        # Vorausfüllen wenn Werte gegeben
        if initial_values:
            self.name_entry.insert(0, initial_values.get('parameter_name', ''))
            self.start_entry.insert(0, str(initial_values.get('start', '')))
            self.end_entry.insert(0, str(initial_values.get('end', '')))
            self.steps_entry.insert(0, str(initial_values.get('steps', '')))
            self.unit_entry.insert(0, initial_values.get('unit', ''))

        frame.columnconfigure(1, weight=1)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(button_frame, text="OK", command=self.ok, width=10).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.cancel, width=10).pack(side=tk.RIGHT)

        # Enter zum Bestätigen
        self.dialog.bind('<Return>', lambda e: self.ok())
        self.dialog.bind('<Escape>', lambda e: self.cancel())

        # Fokus auf erstes Feld
        self.name_entry.focus()

        self.dialog.wait_window()

    def ok(self):
        try:
            self.result = {
                'parameter_name': self.name_entry.get().strip(),
                'start': float(self.start_entry.get()),
                'end': float(self.end_entry.get()),
                'steps': int(self.steps_entry.get()),
                'unit': self.unit_entry.get().strip()
            }

            # Validierung
            if not self.result['parameter_name']:
                messagebox.showerror("Fehler", "Bitte einen Parameter-Namen eingeben")
                return

            if self.result['steps'] < 1:
                messagebox.showerror("Fehler", "Anzahl Schritte muss mindestens 1 sein")
                return

            self.dialog.destroy()

        except ValueError as e:
            messagebox.showerror("Fehler", "Ungueltige Eingabe. Bitte Zahlen verwenden.")

    def cancel(self):
        self.dialog.destroy()


class MeasurementPointDialog:
    """Dialog für manuellen Messpunkt"""

    def __init__(self, parent, initial_values=None):
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Messpunkt")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Name:", font=('', 9, 'bold')).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=0, column=1, pady=5, sticky=tk.EW)

        ttk.Label(frame, text="Parameter (JSON):", font=('', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.NW, pady=5
        )

        text_frame = ttk.Frame(frame)
        text_frame.grid(row=1, column=1, sticky='nsew', pady=5)

        self.param_text = tk.Text(text_frame, width=40, height=12)
        scrollbar = ttk.Scrollbar(text_frame, command=self.param_text.yview)
        self.param_text.configure(yscrollcommand=scrollbar.set)

        self.param_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Vorausfüllen
        if initial_values:
            self.name_entry.insert(0, initial_values.get('name', ''))
            params_json = json.dumps(initial_values.get('parameters', {}), indent=2)
            self.param_text.insert('1.0', params_json)
        else:
            self.param_text.insert('1.0', '{\n  "param1": 0,\n  "param2": 0\n}')

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(1, weight=1)

        # Hilfetext
        help_label = ttk.Label(
            frame,
            text='Tipp: Geben Sie Parameter im JSON-Format ein, z.B. {"temp": 25, "voltage": 5}',
            foreground='gray',
            wraplength=400
        )
        help_label.grid(row=2, column=0, columnspan=2, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(button_frame, text="OK", command=self.ok, width=10).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.cancel, width=10).pack(side=tk.RIGHT)

        # Fokus
        self.name_entry.focus()

        self.dialog.wait_window()

    def ok(self):
        try:
            name = self.name_entry.get().strip()
            if not name:
                messagebox.showerror("Fehler", "Bitte einen Namen eingeben")
                return

            params_json = self.param_text.get('1.0', tk.END).strip()
            parameters = json.loads(params_json)

            if not isinstance(parameters, dict):
                messagebox.showerror("Fehler", "Parameter muessen ein JSON-Objekt sein")
                return

            self.result = {
                'name': name,
                'parameters': parameters
            }
            self.dialog.destroy()

        except json.JSONDecodeError as e:
            messagebox.showerror("Fehler", f"Ungueltiges JSON-Format:\n{e}")

    def cancel(self):
        self.dialog.destroy()
