"""
Dialog für Plugin-Parameter-Konfiguration - VOLLSTÄNDIG
Automatische Generierung basierend auf Parameter-Definitionen
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)


class PluginConfigDialog:
    """Dialog zur Konfiguration von Plugin-Parametern"""

    def __init__(self, parent, plugin):
        self.plugin = plugin
        self.result = None
        self.widgets = {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Plugin-Konfiguration: {plugin.name}")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._setup_ui()
        self.dialog.wait_window()

    def _setup_ui(self):
        """Erstelle UI"""
        # Header
        header_frame = ttk.Frame(self.dialog, padding=10)
        header_frame.pack(fill=tk.X)

        ttk.Label(
            header_frame,
            text=f"Plugin: {self.plugin.name}",
            font=('', 12, 'bold')
        ).pack(anchor=tk.W)

        ttk.Label(
            header_frame,
            text=f"Version: {self.plugin.version}",
            foreground='gray'
        ).pack(anchor=tk.W)

        if self.plugin.description:
            ttk.Label(
                header_frame,
                text=self.plugin.description,
                wraplength=500
            ).pack(anchor=tk.W, pady=5)

        ttk.Separator(self.dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Parameter-Frame (scrollbar)
        canvas_frame = ttk.Frame(self.dialog)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)

        self.param_frame = ttk.Frame(canvas)

        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_window = canvas.create_window((0, 0), window=self.param_frame, anchor=tk.NW)

        def configure_scroll(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())

        self.param_frame.bind('<Configure>', configure_scroll)
        canvas.bind('<Configure>', configure_scroll)

        # Erstelle Parameter-Widgets
        self._create_parameter_widgets()

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(
            button_frame,
            text="OK",
            command=self.apply,
            width=10
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Abbrechen",
            command=self.cancel,
            width=10
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Zuruecksetzen",
            command=self.reset,
            width=15
        ).pack(side=tk.LEFT, padx=5)

    def _create_parameter_widgets(self):
        """Erstelle Widgets basierend auf Parameter-Definitionen"""
        param_defs = self.plugin.get_parameter_definitions()
        current_params = self.plugin.get_all_parameters()

        if not param_defs:
            ttk.Label(
                self.param_frame,
                text="Dieses Plugin hat keine konfigurierbaren Parameter.",
                foreground='gray'
            ).pack(pady=20)
            return

        row = 0

        for param_name, param_def in param_defs.items():
            # Frame für diesen Parameter
            param_container = ttk.LabelFrame(
                self.param_frame,
                text=param_name,
                padding=10
            )
            param_container.grid(row=row, column=0, sticky=tk.EW, pady=5, padx=5)
            self.param_frame.columnconfigure(0, weight=1)

            # Beschreibung
            if 'description' in param_def:
                ttk.Label(
                    param_container,
                    text=param_def['description'],
                    foreground='gray',
                    wraplength=500
                ).pack(anchor=tk.W, pady=(0, 5))

            # Widget basierend auf Typ
            param_type = param_def.get('type', 'str')
            default_value = param_def.get('default')
            current_value = current_params.get(param_name, default_value)

            widget_frame = ttk.Frame(param_container)
            widget_frame.pack(fill=tk.X)

            if param_type == 'bool':
                var = tk.BooleanVar(value=current_value if current_value is not None else default_value)
                cb = ttk.Checkbutton(widget_frame, text="Aktiviert", variable=var)
                cb.pack(side=tk.LEFT)
                self.widgets[param_name] = ('bool', var)

            elif param_type == 'choice':
                choices = param_def.get('choices', [])
                var = tk.StringVar(value=current_value if current_value is not None else default_value)

                ttk.Label(widget_frame, text="Wert:").pack(side=tk.LEFT, padx=5)
                combo = ttk.Combobox(
                    widget_frame,
                    textvariable=var,
                    values=choices,
                    state='readonly',
                    width=30
                )
                combo.pack(side=tk.LEFT, padx=5)
                self.widgets[param_name] = ('choice', var)

            elif param_type == 'int':
                var = tk.IntVar(value=current_value if current_value is not None else default_value)

                ttk.Label(widget_frame, text="Wert:").pack(side=tk.LEFT, padx=5)

                min_val = param_def.get('min', -999999)
                max_val = param_def.get('max', 999999)

                spinbox = ttk.Spinbox(
                    widget_frame,
                    from_=min_val,
                    to=max_val,
                    textvariable=var,
                    width=20
                )
                spinbox.pack(side=tk.LEFT, padx=5)

                if 'unit' in param_def:
                    ttk.Label(widget_frame, text=param_def['unit']).pack(side=tk.LEFT, padx=5)

                self.widgets[param_name] = ('int', var)

            elif param_type == 'float':
                var = tk.DoubleVar(value=current_value if current_value is not None else default_value)

                ttk.Label(widget_frame, text="Wert:").pack(side=tk.LEFT, padx=5)

                min_val = param_def.get('min', -999999.0)
                max_val = param_def.get('max', 999999.0)
                increment = param_def.get('increment', 0.1)

                spinbox = ttk.Spinbox(
                    widget_frame,
                    from_=min_val,
                    to=max_val,
                    increment=increment,
                    textvariable=var,
                    width=20
                )
                spinbox.pack(side=tk.LEFT, padx=5)

                if 'unit' in param_def:
                    ttk.Label(widget_frame, text=param_def['unit']).pack(side=tk.LEFT, padx=5)

                self.widgets[param_name] = ('float', var)

            else:  # str
                var = tk.StringVar(value=current_value if current_value is not None else default_value)

                ttk.Label(widget_frame, text="Wert:").pack(side=tk.LEFT, padx=5)
                entry = ttk.Entry(widget_frame, textvariable=var, width=40)
                entry.pack(side=tk.LEFT, padx=5)

                self.widgets[param_name] = ('str', var)

            # Info über Min/Max
            if param_type in ['int', 'float']:
                info_text = ""
                if 'min' in param_def:
                    info_text += f"Min: {param_def['min']}  "
                if 'max' in param_def:
                    info_text += f"Max: {param_def['max']}  "
                if info_text:
                    ttk.Label(
                        param_container,
                        text=info_text,
                        foreground='gray',
                        font=('', 8)
                    ).pack(anchor=tk.W, pady=(5, 0))

            row += 1

    def apply(self):
        """Übernehme Parameter"""
        try:
            # Validiere und sammle Werte
            new_params = {}
            param_defs = self.plugin.get_parameter_definitions()

            for param_name, (param_type, var) in self.widgets.items():
                value = var.get()

                # Validierung
                param_def = param_defs.get(param_name, {})

                if param_type in ['int', 'float']:
                    if 'min' in param_def and value < param_def['min']:
                        messagebox.showerror(
                            "Fehler",
                            f"Parameter '{param_name}': Wert muss >= {param_def['min']} sein"
                        )
                        return

                    if 'max' in param_def and value > param_def['max']:
                        messagebox.showerror(
                            "Fehler",
                            f"Parameter '{param_name}': Wert muss <= {param_def['max']} sein"
                        )
                        return

                new_params[param_name] = value

            # Setze Parameter
            self.plugin.set_all_parameters(new_params)

            self.result = True
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Anwenden der Parameter:\n{e}")
            logger.error(f"Parameter-Fehler: {e}", exc_info=True)

    def cancel(self):
        """Abbrechen"""
        self.result = False
        self.dialog.destroy()

    def reset(self):
        """Setze auf Standardwerte zurück"""
        response = messagebox.askyesno(
            "Bestaetigung",
            "Alle Parameter auf Standardwerte zuruecksetzen?"
        )

        if response:
            param_defs = self.plugin.get_parameter_definitions()

            for param_name, (param_type, var) in self.widgets.items():
                param_def = param_defs.get(param_name, {})
                default = param_def.get('default')

                if default is not None:
                    var.set(default)
