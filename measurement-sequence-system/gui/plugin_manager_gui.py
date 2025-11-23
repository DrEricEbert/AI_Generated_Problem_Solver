"""
GUI für Plugin-Verwaltung - VOLLSTÄNDIG AKTUALISIERT
Mit Action Recorder Integration
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from gui.plugin_config_dialog import PluginConfigDialog

logger = logging.getLogger(__name__)


class PluginManagerGUI:
    """GUI zur Verwaltung von Plugins"""

    def __init__(self, parent, plugin_manager):
        self.plugin_manager = plugin_manager
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
            text="Plugin-Info",
            command=self.show_plugin_info
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Parameter konfigurieren",
            command=self.configure_plugin
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Aktionen aufzeichnen",
            command=self.open_action_recorder
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Plugin testen",
            command=self.test_plugin
        ).pack(side=tk.LEFT, padx=2)

        # Plugin-Liste
        list_frame = ttk.LabelFrame(self.frame, text="Verfuegbare Plugins", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('name', 'type', 'version', 'parameters', 'description')
        self.plugin_tree = ttk.Treeview(list_frame, columns=columns, show='headings')

        self.plugin_tree.heading('name', text='Name')
        self.plugin_tree.heading('type', text='Typ')
        self.plugin_tree.heading('version', text='Version')
        self.plugin_tree.heading('parameters', text='Parameter')
        self.plugin_tree.heading('description', text='Beschreibung')

        self.plugin_tree.column('name', width=180)
        self.plugin_tree.column('type', width=100)
        self.plugin_tree.column('version', width=80)
        self.plugin_tree.column('parameters', width=80)
        self.plugin_tree.column('description', width=350)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.plugin_tree.yview)
        self.plugin_tree.configure(yscrollcommand=scrollbar.set)

        self.plugin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Doppelklick zum Konfigurieren
        self.plugin_tree.bind('<Double-1>', lambda e: self.configure_plugin())

        # Statistik
        stats_frame = ttk.Frame(self.frame)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_label = ttk.Label(stats_frame, text="Plugins geladen: 0")
        self.stats_label.pack(side=tk.LEFT)

    def refresh(self):
        """Aktualisiere Plugin-Liste"""
        self.plugin_tree.delete(*self.plugin_tree.get_children())

        plugins = self.plugin_manager.get_available_plugins()

        for name, info in plugins.items():
            plugin_type = info.get('type', 'unknown')
            version = info.get('version', '-')
            description = info.get('description', '-')
            has_params = info.get('has_parameters', False)
            param_count = info.get('parameter_count', 0)

            # Typ-Übersetzung
            type_map = {
                'measurement': 'Messgeraet',
                'processing': 'Verarbeitung',
                'unknown': 'Unbekannt'
            }
            type_text = type_map.get(plugin_type, plugin_type)

            # Parameter-Info
            if has_params:
                param_text = f"Ja ({param_count})"
            else:
                param_text = "Nein"

            self.plugin_tree.insert('', tk.END, values=(
                name,
                type_text,
                version,
                param_text,
                description
            ))

        self.stats_label.config(text=f"Plugins geladen: {len(plugins)}")

    def show_plugin_info(self):
        """Zeige detaillierte Plugin-Info"""
        selection = self.plugin_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Bitte Plugin auswaehlen")
            return

        item = self.plugin_tree.item(selection[0])
        plugin_name = item['values'][0]

        plugins = self.plugin_manager.get_available_plugins()
        info = plugins.get(plugin_name, {})

        # Erstelle Plugin-Instanz um Parameter zu holen
        try:
            plugin = self.plugin_manager.get_plugin(plugin_name)
            param_defs = plugin.get_parameter_definitions()
            current_params = plugin.get_all_parameters()
        except:
            param_defs = {}
            current_params = {}

        info_text = f"Plugin: {plugin_name}\n\n"
        info_text += f"Typ: {info.get('type', '-')}\n"
        info_text += f"Version: {info.get('version', '-')}\n"
        info_text += f"Beschreibung: {info.get('description', '-')}\n\n"

        if param_defs:
            info_text += "PARAMETER:\n"
            info_text += "-" * 40 + "\n"
            for param_name, param_def in param_defs.items():
                info_text += f"\n{param_name}:\n"
                info_text += f"  Typ: {param_def.get('type', '?')}\n"
                info_text += f"  Standard: {param_def.get('default', '?')}\n"
                if 'min' in param_def:
                    info_text += f"  Min: {param_def['min']}\n"
                if 'max' in param_def:
                    info_text += f"  Max: {param_def['max']}\n"
                if 'unit' in param_def:
                    info_text += f"  Einheit: {param_def['unit']}\n"
                if 'description' in param_def:
                    info_text += f"  Beschreibung: {param_def['description']}\n"

                # Aktueller Wert
                if param_name in current_params:
                    info_text += f"  Aktuell: {current_params[param_name]}\n"
        else:
            info_text += "\nKeine konfigurierbaren Parameter"

        # Erstelle Info-Fenster
        info_window = tk.Toplevel(self.frame)
        info_window.title(f"Plugin-Info: {plugin_name}")
        info_window.geometry("500x600")

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

    def configure_plugin(self):
        """Öffne Parameter-Konfigurations-Dialog"""
        selection = self.plugin_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Bitte Plugin auswaehlen")
            return

        item = self.plugin_tree.item(selection[0])
        plugin_name = item['values'][0]

        try:
            # Hole oder erstelle Plugin-Instanz
            plugin = self.plugin_manager.get_plugin(plugin_name)

            # Prüfe ob Plugin Parameter hat
            param_defs = plugin.get_parameter_definitions()

            if not param_defs:
                messagebox.showinfo(
                    "Info",
                    f"Plugin '{plugin_name}' hat keine konfigurierbaren Parameter."
                )
                return

            # Öffne Konfigurations-Dialog
            dialog = PluginConfigDialog(self.frame, plugin)

            if dialog.result:
                # Parameter wurden geändert - speichere
                self.plugin_manager.save_plugin_config(plugin_name)
                messagebox.showinfo(
                    "Erfolg",
                    f"Parameter fuer Plugin '{plugin_name}' gespeichert."
                )
                self.refresh()

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler bei Plugin-Konfiguration:\n{e}")
            logger.error(f"Plugin-Konfiguration fehlgeschlagen: {e}", exc_info=True)

    def open_action_recorder(self):
        """Öffne Aktionsaufzeichnung für ExternalProgramController"""
        selection = self.plugin_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Bitte Plugin auswaehlen")
            return

        item = self.plugin_tree.item(selection[0])
        plugin_name = item['values'][0]

        # Prüfe ob es ExternalProgramController ist
        if plugin_name != "ExternalProgramController":
            messagebox.showinfo(
                "Info",
                "Aktionsaufzeichnung ist nur fuer ExternalProgramController verfuegbar."
            )
            return

        try:
            # Hole Plugin-Instanz
            plugin = self.plugin_manager.get_plugin(plugin_name)

            # Initialisiere Plugin falls noch nicht geschehen
            if not plugin.is_initialized:
                plugin.initialize()

            # Öffne Recorder-Dialog
            from gui.action_recorder_dialog import ActionRecorderDialog
            ActionRecorderDialog(self.frame, plugin)

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Oeffnen des Recorders:\n{e}")
            logger.error(f"Action Recorder Fehler: {e}", exc_info=True)

    def test_plugin(self):
        """Teste Plugin"""
        selection = self.plugin_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Bitte Plugin auswaehlen")
            return

        item = self.plugin_tree.item(selection[0])
        plugin_name = item['values'][0]

        try:
            plugin = self.plugin_manager.get_plugin(plugin_name)

            if plugin:
                # Initialisiere
                result = plugin.initialize()

                if result:
                    messagebox.showinfo(
                        "Erfolg",
                        f"Plugin '{plugin_name}' erfolgreich initialisiert.\n\n"
                        f"Typ: {plugin.get_plugin_type()}\n"
                        f"Version: {plugin.version}"
                    )

                    # Cleanup
                    plugin.cleanup()
                else:
                    messagebox.showerror(
                        "Fehler",
                        f"Plugin '{plugin_name}' Initialisierung fehlgeschlagen"
                    )
            else:
                messagebox.showerror(
                    "Fehler",
                    f"Plugin '{plugin_name}' konnte nicht geladen werden"
                )

        except Exception as e:
            messagebox.showerror("Fehler", f"Plugin-Test fehlgeschlagen:\n{e}")
            logger.error(f"Plugin-Test Fehler: {e}", exc_info=True)
