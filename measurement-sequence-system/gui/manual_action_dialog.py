"""
Dialog zum manuellen Hinzufügen von Aktionen
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)


class ManualActionDialog:
    """Dialog zum manuellen Hinzufügen einer Aktion"""

    def __init__(self, parent, action_sequence):
        self.action_sequence = action_sequence
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Aktion hinzufuegen")
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._setup_ui()
        self.dialog.wait_window()

    def _setup_ui(self):
        """Erstelle UI"""
        # Aktionstyp
        ttk.Label(self.dialog, text="Aktionstyp:", font=('', 10, 'bold')).pack(padx=10, pady=10, anchor=tk.W)

        self.action_type = tk.StringVar(value='wait')

        types_frame = ttk.Frame(self.dialog)
        types_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Radiobutton(types_frame, text="Warten", variable=self.action_type, value='wait', command=self._update_fields).pack(anchor=tk.W)
        ttk.Radiobutton(types_frame, text="Klick", variable=self.action_type, value='click', command=self._update_fields).pack(anchor=tk.W)
        ttk.Radiobutton(types_frame, text="Text eingeben", variable=self.action_type, value='type', command=self._update_fields).pack(anchor=tk.W)
        ttk.Radiobutton(types_frame, text="Taste druecken", variable=self.action_type, value='key', command=self._update_fields).pack(anchor=tk.W)

        # Container für spezifische Felder
        self.fields_frame = ttk.LabelFrame(self.dialog, text="Parameter", padding=10)
        self.fields_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Hinzufuegen", command=self.add_action).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.dialog.destroy).pack(side=tk.RIGHT)

        self._update_fields()

    def _update_fields(self):
        """Aktualisiere Eingabefelder basierend auf Aktionstyp"""
        # Lösche alte Felder
        for widget in self.fields_frame.winfo_children():
            widget.destroy()

        action_type = self.action_type.get()

        if action_type == 'wait':
            ttk.Label(self.fields_frame, text="Dauer (Sekunden):").pack(anchor=tk.W, pady=5)
            self.duration_var = tk.DoubleVar(value=1.0)
            ttk.Spinbox(self.fields_frame, from_=0.1, to=60.0, increment=0.1, textvariable=self.duration_var, width=20).pack(anchor=tk.W)

        elif action_type == 'click':
            ttk.Label(self.fields_frame, text="X-Position:").pack(anchor=tk.W, pady=5)
            self.x_var = tk.IntVar(value=100)
            ttk.Entry(self.fields_frame, textvariable=self.x_var, width=20).pack(anchor=tk.W)

            ttk.Label(self.fields_frame, text="Y-Position:").pack(anchor=tk.W, pady=5)
            self.y_var = tk.IntVar(value=100)
            ttk.Entry(self.fields_frame, textvariable=self.y_var, width=20).pack(anchor=tk.W)

            ttk.Label(self.fields_frame, text="Maustaste:").pack(anchor=tk.W, pady=5)
            self.button_var = tk.StringVar(value='left')
            ttk.Combobox(self.fields_frame, textvariable=self.button_var, values=['left', 'right', 'middle'], state='readonly', width=17).pack(anchor=tk.W)

        elif action_type == 'type':
            ttk.Label(self.fields_frame, text="Text:").pack(anchor=tk.W, pady=5)
            self.text_var = tk.StringVar()
            ttk.Entry(self.fields_frame, textvariable=self.text_var, width=40).pack(anchor=tk.W)

        elif action_type == 'key':
            ttk.Label(self.fields_frame, text="Tastenname:").pack(anchor=tk.W, pady=5)
            self.key_var = tk.StringVar(value='enter')
            common_keys = ['enter', 'tab', 'esc', 'space', 'backspace', 'delete', 'up', 'down', 'left', 'right']
            ttk.Combobox(self.fields_frame, textvariable=self.key_var, values=common_keys, width=17).pack(anchor=tk.W)

    def add_action(self):
        """Füge Aktion hinzu"""
        try:
            from plugins.external_program import WaitAction, ClickAction, TypeAction, KeyAction

            action_type = self.action_type.get()

            if action_type == 'wait':
                action = WaitAction(self.duration_var.get())
            elif action_type == 'click':
                action = ClickAction(self.x_var.get(), self.y_var.get(), self.button_var.get())
            elif action_type == 'type':
                if not self.text_var.get():
                    messagebox.showwarning("Warnung", "Bitte Text eingeben")
                    return
                action = TypeAction(self.text_var.get())
            elif action_type == 'key':
                action = KeyAction(self.key_var.get())
            else:
                return

            self.action_sequence.add_action(action)
            self.result = True
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Hinzufuegen:\n{e}")
            logger.error(f"Fehler: {e}")
