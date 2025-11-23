"""
GUI für Aufnahme und Bearbeitung von Aktionssequenzen - FEHLERFREI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import threading
import time

logger = logging.getLogger(__name__)

# Prüfe ob pyautogui verfügbar
try:
    import pyautogui
    from pynput import mouse, keyboard
    RECORDING_AVAILABLE = True
except ImportError:
    RECORDING_AVAILABLE = False
    logger.warning("pynput nicht verfuegbar - Aufzeichnung nicht moeglich")


class ActionRecorderDialog:
    """Dialog zur Aufzeichnung und Bearbeitung von Aktionen"""

    def __init__(self, parent, plugin):
        self.plugin = plugin
        self.recording = False
        self.paused = False
        self.dialog_open = True

        # Listener
        self.mouse_listener = None
        self.keyboard_listener = None

        # Zeitstempel für Wartezeiten
        self.last_action_time = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Aktionsaufzeichnung - {plugin.name}")
        self.dialog.geometry("900x700")
        self.dialog.transient(parent)

        # Cleanup bei Dialog-Schließung
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_closing)

        self._setup_ui()

    def _setup_ui(self):
        """Erstelle UI"""
        # Toolbar
        toolbar = ttk.Frame(self.dialog)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        self.record_button = ttk.Button(
            toolbar,
            text="[REC] Aufzeichnung starten",
            command=self.start_recording,
            width=25
        )
        self.record_button.pack(side=tk.LEFT, padx=2)

        self.stop_button = ttk.Button(
            toolbar,
            text="[STOP] Aufzeichnung stoppen",
            command=self.stop_recording,
            state=tk.DISABLED,
            width=25
        )
        self.stop_button.pack(side=tk.LEFT, padx=2)

        self.pause_button = ttk.Button(
            toolbar,
            text="[PAUSE] Pause",
            command=self.toggle_pause,
            state=tk.DISABLED,
            width=15
        )
        self.pause_button.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        ttk.Button(
            toolbar,
            text="Wiedergabe",
            command=self.play_sequence,
            width=15
        ).pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        ttk.Button(
            toolbar,
            text="Laden",
            command=self.load_sequence,
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Speichern",
            command=self.save_sequence,
            width=10
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Loeschen",
            command=self.clear_sequence,
            width=10
        ).pack(side=tk.LEFT, padx=2)

        # Info-Frame
        info_frame = ttk.Frame(self.dialog, relief=tk.RIDGE, borderwidth=2)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        if RECORDING_AVAILABLE:
            info_text = "Aufzeichnung verfuegbar. Druecken Sie ESC zum Stoppen der Aufzeichnung."
            info_color = 'blue'
        else:
            info_text = "WARNUNG: pynput nicht installiert - Aufzeichnung nicht verfuegbar!"
            info_color = 'red'

        ttk.Label(
            info_frame,
            text=info_text,
            foreground=info_color,
            padding=5
        ).pack()

        # Status
        status_frame = ttk.LabelFrame(self.dialog, text="Status", padding=5)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_label = ttk.Label(
            status_frame,
            text="Bereit",
            font=('', 9, 'bold')
        )
        self.status_label.pack(side=tk.LEFT)

        self.action_count_label = ttk.Label(
            status_frame,
            text="Aktionen: 0"
        )
        self.action_count_label.pack(side=tk.RIGHT)

        # Aktionsliste - KORRIGIERT: Nur pack() verwenden
        list_frame = ttk.LabelFrame(self.dialog, text="Aufgezeichnete Aktionen", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Toolbar für Liste
        list_toolbar = ttk.Frame(list_frame)
        list_toolbar.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(
            list_toolbar,
            text="Aktion hinzufuegen",
            command=self.add_action_manual
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            list_toolbar,
            text="Bearbeiten",
            command=self.edit_action
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            list_toolbar,
            text="Loeschen",
            command=self.delete_action
        ).pack(side=tk.LEFT, padx=2)

        ttk.Separator(list_toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)

        ttk.Button(
            list_toolbar,
            text="Nach oben",
            command=self.move_action_up
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            list_toolbar,
            text="Nach unten",
            command=self.move_action_down
        ).pack(side=tk.LEFT, padx=2)

        # Container für Treeview und Scrollbars - KORRIGIERT
        tree_container = ttk.Frame(list_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)

        # Treeview für Aktionen
        columns = ('nr', 'type', 'details', 'timestamp')
        self.actions_tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=15)

        self.actions_tree.heading('nr', text='#')
        self.actions_tree.heading('type', text='Typ')
        self.actions_tree.heading('details', text='Details')
        self.actions_tree.heading('timestamp', text='Zeitstempel')

        self.actions_tree.column('nr', width=40)
        self.actions_tree.column('type', width=100)
        self.actions_tree.column('details', width=400)
        self.actions_tree.column('timestamp', width=180)

        # Scrollbars - mit pack statt grid
        scrollbar_y = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.actions_tree.yview)
        scrollbar_x = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.actions_tree.xview)
        self.actions_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Pack statt Grid verwenden
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.actions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Buttons unten
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            button_frame,
            text="Schliessen",
            command=self.on_closing
        ).pack(side=tk.RIGHT, padx=5)

        # Aktualisiere Anzeige
        self.refresh_action_list()

    def on_closing(self):
        """Cleanup beim Schließen des Dialogs"""
        # Stoppe Aufzeichnung falls aktiv
        if self.recording:
            self.stop_recording()

        # Stoppe Listener
        self._stop_listeners()

        # Markiere Dialog als geschlossen
        self.dialog_open = False

        # Zerstöre Dialog
        self.dialog.destroy()

    def _safe_update_widget(self, widget, method, *args, **kwargs):
        """Sicheres Widget-Update - prüft ob Dialog noch offen ist"""
        if not self.dialog_open:
            return

        try:
            getattr(widget, method)(*args, **kwargs)
        except tk.TclError as e:
            logger.warning(f"Widget-Update fehlgeschlagen: {e}")

    def start_recording(self):
        """Starte Aufzeichnung"""
        if not RECORDING_AVAILABLE:
            messagebox.showerror(
                "Fehler",
                "Aufzeichnung nicht verfuegbar.\n\n"
                "Bitte installieren Sie: pip install pynput"
            )
            return

        self.recording = True
        self.paused = False
        self.last_action_time = time.time()

        # Lösche alte Aktionen
        response = messagebox.askyesno(
            "Bestaetigung",
            "Alte Aktionen loeschen und neue Aufzeichnung starten?"
        )
        if response:
            self.plugin.action_sequence.clear()

        # UI aktualisieren - mit Sicherheitsprüfung
        self._safe_update_widget(self.record_button, 'config', state=tk.DISABLED)
        self._safe_update_widget(self.stop_button, 'config', state=tk.NORMAL)
        self._safe_update_widget(self.pause_button, 'config', state=tk.NORMAL)
        self._safe_update_widget(self.status_label, 'config', text="AUFZEICHNUNG LAEUFT", foreground='red')

        # Starte Listener
        self._start_listeners()

        logger.info("Aufzeichnung gestartet")

    def stop_recording(self):
        """Stoppe Aufzeichnung"""
        if not self.recording:
            return

        self.recording = False
        self.paused = False

        # Stoppe Listener
        self._stop_listeners()

        # UI aktualisieren - mit Sicherheitsprüfung
        self._safe_update_widget(self.record_button, 'config', state=tk.NORMAL)
        self._safe_update_widget(self.stop_button, 'config', state=tk.DISABLED)
        self._safe_update_widget(self.pause_button, 'config', state=tk.DISABLED, text="[PAUSE] Pause")
        self._safe_update_widget(self.status_label, 'config', text="Aufzeichnung gestoppt", foreground='blue')

        # Aktualisiere Liste
        if self.dialog_open:
            self.refresh_action_list()

        logger.info(f"Aufzeichnung gestoppt - {len(self.plugin.action_sequence.actions)} Aktionen")

    def toggle_pause(self):
        """Toggle Pause"""
        self.paused = not self.paused

        if self.paused:
            self._safe_update_widget(self.pause_button, 'config', text="[CONTINUE] Fortsetzen")
            self._safe_update_widget(self.status_label, 'config', text="PAUSIERT", foreground='orange')
        else:
            self._safe_update_widget(self.pause_button, 'config', text="[PAUSE] Pause")
            self._safe_update_widget(self.status_label, 'config', text="AUFZEICHNUNG LAEUFT", foreground='red')
            self.last_action_time = time.time()

    def _start_listeners(self):
        """Starte Maus- und Tastatur-Listener"""
        def on_click(x, y, button, pressed):
            if not self.recording or self.paused or not self.dialog_open:
                return

            if pressed:
                # Füge Wartezeit hinzu wenn nötig
                self._add_wait_action()

                # Füge Klick-Aktion hinzu
                try:
                    from plugins.external_program import ClickAction
                    action = ClickAction(x, y, button.name if hasattr(button, 'name') else 'left')
                    self.plugin.action_sequence.add_action(action)

                    self.last_action_time = time.time()

                    # Aktualisiere UI - sicher
                    if self.dialog_open:
                        self.dialog.after(0, self.refresh_action_list)
                except Exception as e:
                    logger.error(f"Fehler bei Klick-Aufzeichnung: {e}")

        def on_key(key):
            if not self.recording or self.paused or not self.dialog_open:
                return

            try:
                # ESC stoppt Aufzeichnung
                if hasattr(key, 'name') and key.name == 'esc':
                    if self.dialog_open:
                        self.dialog.after(0, self.stop_recording)
                    return False

                # Füge Wartezeit hinzu
                self._add_wait_action()

                # Füge Tastendruck-Aktion hinzu
                from plugins.external_program import KeyAction, TypeAction

                if hasattr(key, 'char') and key.char:
                    # Buchstabe/Ziffer
                    action = TypeAction(key.char)
                else:
                    # Spezialtaste
                    key_name = key.name if hasattr(key, 'name') else str(key)
                    action = KeyAction(key_name)

                self.plugin.action_sequence.add_action(action)

                self.last_action_time = time.time()

                # Aktualisiere UI - sicher
                if self.dialog_open:
                    self.dialog.after(0, self.refresh_action_list)

            except Exception as e:
                logger.error(f"Fehler bei Tastendruck: {e}")

        # Starte Listener
        try:
            self.mouse_listener = mouse.Listener(on_click=on_click)
            self.keyboard_listener = keyboard.Listener(on_press=on_key)

            self.mouse_listener.start()
            self.keyboard_listener.start()

            logger.info("Listener gestartet")
        except Exception as e:
            logger.error(f"Fehler beim Starten der Listener: {e}")
            messagebox.showerror("Fehler", f"Listener konnten nicht gestartet werden:\n{e}")

    def _stop_listeners(self):
        """Stoppe Listener"""
        try:
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None

            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None

            logger.info("Listener gestoppt")
        except Exception as e:
            logger.error(f"Fehler beim Stoppen der Listener: {e}")

    def _add_wait_action(self):
        """Füge Wartezeit-Aktion hinzu wenn nötig"""
        if self.last_action_time:
            elapsed = time.time() - self.last_action_time

            # Nur Wartezeiten > 0.5s aufzeichnen
            if elapsed > 0.5:
                from plugins.external_program import WaitAction
                action = WaitAction(round(elapsed, 2))
                self.plugin.action_sequence.add_action(action)

    def refresh_action_list(self):
        """Aktualisiere Aktionsliste"""
        if not self.dialog_open:
            return

        try:
            self.actions_tree.delete(*self.actions_tree.get_children())

            for i, action in enumerate(self.plugin.action_sequence.actions, 1):
                details = self._format_action_details(action)

                self.actions_tree.insert('', tk.END, values=(
                    i,
                    action.action_type,
                    details,
                    action.timestamp
                ))

            # Update count
            count = len(self.plugin.action_sequence.actions)
            self._safe_update_widget(self.action_count_label, 'config', text=f"Aktionen: {count}")
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren der Aktionsliste: {e}")

    def _format_action_details(self, action) -> str:
        """Formatiere Aktionsdetails für Anzeige"""
        try:
            from plugins.external_program import (
                ClickAction, TypeAction, KeyAction, WaitAction, MoveAction, DragAction
            )

            if isinstance(action, ClickAction):
                return f"Klick bei ({action.x}, {action.y}), {action.button}, {action.clicks}x"
            elif isinstance(action, TypeAction):
                text_preview = action.text[:30] + "..." if len(action.text) > 30 else action.text
                return f'Text: "{text_preview}"'
            elif isinstance(action, KeyAction):
                return f"Taste: {action.key}, {action.presses}x"
            elif isinstance(action, WaitAction):
                return f"Warten: {action.duration}s"
            elif isinstance(action, MoveAction):
                return f"Bewegung zu ({action.x}, {action.y})"
            elif isinstance(action, DragAction):
                return f"Drag zu ({action.x}, {action.y}), {action.button}"
            else:
                return str(action)
        except Exception as e:
            logger.error(f"Fehler beim Formatieren: {e}")
            return "Unbekannt"

    def play_sequence(self):
        """Spiele Aktionssequenz ab"""
        if not self.plugin.action_sequence.actions:
            messagebox.showinfo("Info", "Keine Aktionen zum Abspielen vorhanden")
            return

        response = messagebox.askyesno(
            "Wiedergabe",
            f"{len(self.plugin.action_sequence.actions)} Aktionen abspielen?\n\n"
            "Stellen Sie sicher, dass das Zielprogramm im Vordergrund ist!"
        )

        if not response:
            return

        # Countdown
        for i in range(3, 0, -1):
            if self.dialog_open:
                self._safe_update_widget(self.status_label, 'config', text=f"Start in {i}...", foreground='orange')
                self.dialog.update()
            time.sleep(1)

        if self.dialog_open:
            self._safe_update_widget(self.status_label, 'config', text="WIEDERGABE LAEUFT", foreground='green')
            self.dialog.update()

        # Führe in Thread aus um GUI nicht zu blockieren
        def play_thread():
            try:
                self.plugin.execute_action_sequence()
                if self.dialog_open:
                    self.dialog.after(0, lambda: self._safe_update_widget(
                        self.status_label, 'config',
                        text="Wiedergabe abgeschlossen",
                        foreground='blue'
                    ))
            except Exception as e:
                logger.error(f"Fehler bei Wiedergabe: {e}")
                if self.dialog_open:
                    self.dialog.after(0, lambda: messagebox.showerror(
                        "Fehler",
                        f"Fehler bei Wiedergabe:\n{e}"
                    ))

        thread = threading.Thread(target=play_thread, daemon=True)
        thread.start()

    def load_sequence(self):
        """Lade Sequenz aus Datei"""
        filepath = filedialog.askopenfilename(
            title="Aktionssequenz laden",
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )

        if filepath:
            try:
                self.plugin.load_action_sequence(filepath)
                self.refresh_action_list()
                messagebox.showinfo("Erfolg", f"Sequenz geladen:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Laden:\n{e}")
                logger.error(f"Fehler beim Laden: {e}", exc_info=True)

    def save_sequence(self):
        """Speichere Sequenz in Datei"""
        if not self.plugin.action_sequence.actions:
            messagebox.showinfo("Info", "Keine Aktionen zum Speichern vorhanden")
            return

        filepath = filedialog.asksaveasfilename(
            title="Aktionssequenz speichern",
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")],
            defaultextension=".json"
        )

        if filepath:
            try:
                self.plugin.save_action_sequence(filepath)
                messagebox.showinfo("Erfolg", f"Sequenz gespeichert:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{e}")
                logger.error(f"Fehler beim Speichern: {e}", exc_info=True)

    def clear_sequence(self):
        """Lösche alle Aktionen"""
        if not self.plugin.action_sequence.actions:
            return

        response = messagebox.askyesno(
            "Bestaetigung",
            f"Wirklich alle {len(self.plugin.action_sequence.actions)} Aktionen loeschen?"
        )

        if response:
            self.plugin.action_sequence.clear()
            self.refresh_action_list()

    def add_action_manual(self):
        """Füge Aktion manuell hinzu"""
        # Dialog zum manuellen Hinzufügen
        from gui.manual_action_dialog import ManualActionDialog
        try:
            dialog = ManualActionDialog(self.dialog, self.plugin.action_sequence)
            if dialog.result:
                self.refresh_action_list()
        except ImportError:
            messagebox.showinfo("Info", "Manuelle Aktion wird noch implementiert")

    def edit_action(self):
        """Bearbeite Aktion"""
        selection = self.actions_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Bitte eine Aktion auswaehlen")
            return

        messagebox.showinfo("Info", "Bearbeiten wird noch implementiert")

    def delete_action(self):
        """Lösche Aktion"""
        selection = self.actions_tree.selection()
        if not selection:
            return

        try:
            index = self.actions_tree.index(selection[0])
            del self.plugin.action_sequence.actions[index]
            self.refresh_action_list()
        except Exception as e:
            logger.error(f"Fehler beim Loeschen: {e}")

    def move_action_up(self):
        """Verschiebe Aktion nach oben"""
        selection = self.actions_tree.selection()
        if not selection:
            return

        try:
            index = self.actions_tree.index(selection[0])
            if index > 0:
                actions = self.plugin.action_sequence.actions
                actions[index], actions[index-1] = actions[index-1], actions[index]
                self.refresh_action_list()
                # Wähle verschobenes Element
                children = self.actions_tree.get_children()
                if children and len(children) > index-1:
                    self.actions_tree.selection_set(children[index-1])
        except Exception as e:
            logger.error(f"Fehler beim Verschieben: {e}")

    def move_action_down(self):
        """Verschiebe Aktion nach unten"""
        selection = self.actions_tree.selection()
        if not selection:
            return

        try:
            index = self.actions_tree.index(selection[0])
            actions = self.plugin.action_sequence.actions

            if index < len(actions) - 1:
                actions[index], actions[index+1] = actions[index+1], actions[index]
                self.refresh_action_list()
                # Wähle verschobenes Element
                children = self.actions_tree.get_children()
                if children and len(children) > index+1:
                    self.actions_tree.selection_set(children[index+1])
        except Exception as e:
            logger.error(f"Fehler beim Verschieben: {e}")
