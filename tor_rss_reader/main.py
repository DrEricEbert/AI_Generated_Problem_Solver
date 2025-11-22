"""
TOR RSS Feed Reader
Professionelle RSS Feed Reader Anwendung mit TOR-Unterstützung
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import webbrowser
from datetime import datetime
from typing import Dict, List, Optional
import logging

from config_manager import ConfigManager
from tor_handler import TorHandler
from feed_manager import FeedManager

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RSSFeedReader:
    """Hauptanwendung für den RSS Feed Reader"""

    # Theme Konfigurationen
    THEMES = {
        'light': {
            'bg': '#f0f0f0',
            'fg': '#000000',
            'select_bg': '#0078d7',
            'select_fg': '#ffffff',
            'frame_bg': '#ffffff',
            'text_bg': '#ffffff',
            'text_fg': '#000000',
            'button_bg': '#e1e1e1',
            'header_bg': '#e8e8e8'
        },
        'dark': {
            'bg': '#1e1e1e',
            'fg': '#ffffff',
            'select_bg': '#0078d7',
            'select_fg': '#ffffff',
            'frame_bg': '#2d2d2d',
            'text_bg': '#252525',
            'text_fg': '#e0e0e0',
            'button_bg': '#3c3c3c',
            'header_bg': '#323232'
        }
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TOR RSS Feed Reader v1.0")
        self.root.geometry("1400x800")

        # Manager initialisieren
        self.config_manager = ConfigManager()
        self.tor_handler = TorHandler(self.config_manager)
        self.feed_manager = FeedManager(self.tor_handler)

        # Variablen
        self.current_theme = self.config_manager.get('theme', 'dark')
        self.auto_refresh_jobs: Dict[str, str] = {}
        self.feed_tabs: Dict[str, ttk.Frame] = {}

        # GUI aufbauen
        self._create_menu()
        self._create_ui()
        self._setup_shortcuts()
        self._apply_theme()

        # Gespeicherte Feeds laden
        self._load_saved_feeds()

        # TOR-Status prüfen
        self._check_tor_status()

        logger.info("TOR RSS Feed Reader gestartet")

    def _create_menu(self):
        """Erstellt das Hauptmenü"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Datei-Menü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(
            label="Einstellungen exportieren",
            command=self._export_settings,
            accelerator="Ctrl+E"
        )
        file_menu.add_command(
            label="Einstellungen importieren",
            command=self._import_settings,
            accelerator="Ctrl+I"
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Beenden",
            command=self._quit_app,
            accelerator="Ctrl+Q"
        )

        # Feed-Menü
        feed_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Feeds", menu=feed_menu)
        feed_menu.add_command(
            label="Feed hinzufügen",
            command=self._add_feed_dialog,
            accelerator="Ctrl+N"
        )
        feed_menu.add_command(
            label="Feed entfernen",
            command=self._remove_selected_feed,
            accelerator="Delete"
        )
        feed_menu.add_command(
            label="Alle Feeds aktualisieren",
            command=self._refresh_all_feeds,
            accelerator="F5"
        )

        # Ansicht-Menü
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ansicht", menu=view_menu)
        view_menu.add_command(
            label="Dark Mode",
            command=lambda: self._switch_theme('dark'),
            accelerator="Ctrl+D"
        )
        view_menu.add_command(
            label="Light Mode",
            command=lambda: self._switch_theme('light'),
            accelerator="Ctrl+L"
        )

        # TOR-Menü
        tor_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="TOR", menu=tor_menu)
        tor_menu.add_command(
            label="TOR-Status prüfen",
            command=self._check_tor_status,
            accelerator="Ctrl+T"
        )
        tor_menu.add_command(
            label="TOR-Einstellungen",
            command=self._tor_settings_dialog
        )

        # Hilfe-Menü
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Hilfe", menu=help_menu)
        help_menu.add_command(
            label="Shortcuts",
            command=self._show_shortcuts,
            accelerator="F1"
        )
        help_menu.add_command(label="Über", command=self._show_about)

    def _create_ui(self):
        """Erstellt die Hauptbenutzeroberfläche"""
        # Hauptcontainer
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Linke Seite: Feed-Liste
        self._create_feed_list_panel(main_paned)

        # Rechte Seite: Tabbed Browser
        self._create_browser_panel(main_paned)

        # Statusleiste
        self._create_status_bar()

    def _create_feed_list_panel(self, parent):
        """Erstellt das Feed-Listen-Panel"""
        left_frame = ttk.Frame(parent, width=300)
        parent.add(left_frame, weight=1)

        # Header
        header_frame = ttk.Frame(left_frame)
        header_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(
            header_frame,
            text="RSS Feeds",
            font=('Arial', 12, 'bold')
        ).pack(side=tk.LEFT)

        # Buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            button_frame,
            text="➕ Hinzufügen",
            command=self._add_feed_dialog
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            button_frame,
            text="➖ Entfernen",
            command=self._remove_selected_feed
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            button_frame,
            text="🔄 Laden",
            command=self._load_selected_feeds
        ).pack(side=tk.LEFT, padx=2)

        # Feed-Liste mit Scrollbar
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.feed_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set
        )
        self.feed_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.feed_listbox.yview)

        # Doppelklick zum Laden
        self.feed_listbox.bind('<Double-Button-1>', lambda e: self._load_selected_feeds())

        # Rechtsklick-Menü
        self.feed_context_menu = tk.Menu(self.feed_listbox, tearoff=0)
        self.feed_context_menu.add_command(
            label="Laden",
            command=self._load_selected_feeds
        )
        self.feed_context_menu.add_command(
            label="Bearbeiten",
            command=self._edit_feed_dialog
        )
        self.feed_context_menu.add_command(
            label="Auto-Refresh Einstellungen",
            command=self._set_auto_refresh
        )
        self.feed_context_menu.add_separator()
        self.feed_context_menu.add_command(
            label="Entfernen",
            command=self._remove_selected_feed
        )

        self.feed_listbox.bind('<Button-3>', self._show_feed_context_menu)

    def _create_browser_panel(self, parent):
        """Erstellt das Browser-Panel mit Tabs"""
        right_frame = ttk.Frame(parent)
        parent.add(right_frame, weight=3)

        # Tab-Control
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Willkommens-Tab
        self._create_welcome_tab()

    def _create_welcome_tab(self):
        """Erstellt den Willkommens-Tab"""
        welcome_frame = ttk.Frame(self.notebook)
        self.notebook.add(welcome_frame, text="Willkommen")

        welcome_text = tk.Text(
            welcome_frame,
            wrap=tk.WORD,
            font=('Arial', 10)
        )
        welcome_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        welcome_content = """
🔒 TOR RSS Feed Reader v1.0

Willkommen zum sicheren RSS Feed Reader!

📋 Schnellstart:
1. Fügen Sie RSS Feeds über den "➕ Hinzufügen" Button hinzu
2. Wählen Sie Feeds aus der Liste aus
3. Klicken Sie auf "🔄 Laden" um die Feeds zu laden
4. Jeder Feed wird in einem eigenen Tab angezeigt

🔑 Wichtige Shortcuts:
• Ctrl+N: Neuen Feed hinzufügen
• F5: Alle Feeds aktualisieren
• Ctrl+D: Dark Mode
• Ctrl+L: Light Mode
• Ctrl+T: TOR-Status prüfen
• F1: Alle Shortcuts anzeigen

🌐 TOR-Integration:
Diese Anwendung lädt alle RSS Feeds über das TOR-Netzwerk für
maximale Privatsphäre und Anonymität.

⚙️ Features:
• Automatische Feed-Aktualisierung (konfigurierbar pro Feed)
• Dark/Light Theme
• Externe Links öffnen im TOR Browser
• Einstellungen speichern/laden
• Multi-Feed Support

Viel Spaß beim sicheren Feed-Lesen! 🚀
        """

        welcome_text.insert('1.0', welcome_content)
        welcome_text.config(state=tk.DISABLED)

    def _create_status_bar(self):
        """Erstellt die Statusleiste"""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = ttk.Label(
            self.status_frame,
            text="Bereit",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        self.tor_status_label = ttk.Label(
            self.status_frame,
            text="TOR: Nicht verbunden",
            relief=tk.SUNKEN,
            anchor=tk.E
        )
        self.tor_status_label.pack(side=tk.RIGHT, padx=2)

    def _setup_shortcuts(self):
        """Richtet Tastatur-Shortcuts ein"""
        shortcuts = {
            '<Control-n>': self._add_feed_dialog,
            '<Control-N>': self._add_feed_dialog,
            '<Delete>': self._remove_selected_feed,
            '<F5>': self._refresh_all_feeds,
            '<Control-d>': lambda e: self._switch_theme('dark'),
            '<Control-D>': lambda e: self._switch_theme('dark'),
            '<Control-l>': lambda e: self._switch_theme('light'),
            '<Control-L>': lambda e: self._switch_theme('light'),
            '<Control-t>': lambda e: self._check_tor_status(),
            '<Control-T>': lambda e: self._check_tor_status(),
            '<Control-q>': lambda e: self._quit_app(),
            '<Control-Q>': lambda e: self._quit_app(),
            '<F1>': lambda e: self._show_shortcuts(),
            '<Control-e>': lambda e: self._export_settings(),
            '<Control-E>': lambda e: self._export_settings(),
            '<Control-i>': lambda e: self._import_settings(),
            '<Control-I>': lambda e: self._import_settings(),
        }

        for key, command in shortcuts.items():
            self.root.bind(key, command if callable(command) else lambda e, c=command: c())

    def _apply_theme(self):
        """Wendet das aktuelle Theme an"""
        theme = self.THEMES[self.current_theme]

        # Root-Fenster
        self.root.configure(bg=theme['bg'])

        # Style für ttk-Widgets
        style = ttk.Style()

        if self.current_theme == 'dark':
            style.theme_use('clam')
        else:
            style.theme_use('default')

        # Listbox
        self.feed_listbox.configure(
            bg=theme['frame_bg'],
            fg=theme['fg'],
            selectbackground=theme['select_bg'],
            selectforeground=theme['select_fg']
        )

        # Status-Labels
        self.status_label.configure(background=theme['bg'])
        self.tor_status_label.configure(background=theme['bg'])

        logger.info(f"Theme gewechselt zu: {self.current_theme}")

    def _switch_theme(self, theme: str):
        """Wechselt das Theme"""
        self.current_theme = theme
        self.config_manager.set('theme', theme)
        self.config_manager.save()
        self._apply_theme()

        # Alle Feed-Tabs aktualisieren
        for feed_url in self.feed_tabs:
            self._update_tab_theme(feed_url)

    def _update_tab_theme(self, feed_url: str):
        """Aktualisiert das Theme eines Tabs"""
        if feed_url not in self.feed_tabs:
            return

        theme = self.THEMES[self.current_theme]
        frame = self.feed_tabs[feed_url]

        for widget in frame.winfo_children():
            if isinstance(widget, tk.Text):
                widget.configure(
                    bg=theme['text_bg'],
                    fg=theme['text_fg']
                )

    def _add_feed_dialog(self, event=None):
        """Dialog zum Hinzufügen eines Feeds"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Feed hinzufügen")
        dialog.geometry("500x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Name
        ttk.Label(dialog, text="Feed Name:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        name_entry.focus()

        # URL
        ttk.Label(dialog, text="Feed URL:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        url_entry = ttk.Entry(dialog, width=40)
        url_entry.grid(row=1, column=1, padx=10, pady=10)

        # Auto-Refresh Interval (Minuten)
        ttk.Label(dialog, text="Auto-Refresh (Min):").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        interval_spinbox = ttk.Spinbox(dialog, from_=0, to=1440, width=38)
        interval_spinbox.set(0)  # 0 = deaktiviert
        interval_spinbox.grid(row=2, column=1, padx=10, pady=10)

        def save_feed():
            name = name_entry.get().strip()
            url = url_entry.get().strip()
            interval = int(interval_spinbox.get())

            if not name or not url:
                messagebox.showwarning("Warnung", "Bitte Name und URL eingeben!")
                return

            # Feed hinzufügen
            feeds = self.config_manager.get('feeds', {})
            feeds[url] = {
                'name': name,
                'interval': interval,
                'active': True
            }
            self.config_manager.set('feeds', feeds)
            self.config_manager.save()

            # UI aktualisieren
            self._load_saved_feeds()
            dialog.destroy()

            self.update_status(f"Feed '{name}' hinzugefügt")
            logger.info(f"Feed hinzugefügt: {name} ({url})")

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Speichern", command=save_feed).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

        # Enter zum Speichern
        dialog.bind('<Return>', lambda e: save_feed())

    def _edit_feed_dialog(self):
        """Dialog zum Bearbeiten eines Feeds"""
        selection = self.feed_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Bitte einen Feed auswählen!")
            return

        feed_text = self.feed_listbox.get(selection[0])
        feed_url = self._get_feed_url_from_text(feed_text)

        feeds = self.config_manager.get('feeds', {})
        if feed_url not in feeds:
            return

        feed_data = feeds[feed_url]

        # Dialog erstellen
        dialog = tk.Toplevel(self.root)
        dialog.title("Feed bearbeiten")
        dialog.geometry("500x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Name
        ttk.Label(dialog, text="Feed Name:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.insert(0, feed_data['name'])
        name_entry.grid(row=0, column=1, padx=10, pady=10)

        # URL (readonly)
        ttk.Label(dialog, text="Feed URL:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        url_label = ttk.Label(dialog, text=feed_url, foreground='gray')
        url_label.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)

        # Auto-Refresh Interval
        ttk.Label(dialog, text="Auto-Refresh (Min):").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        interval_spinbox = ttk.Spinbox(dialog, from_=0, to=1440, width=38)
        interval_spinbox.set(feed_data.get('interval', 0))
        interval_spinbox.grid(row=2, column=1, padx=10, pady=10)

        def save_changes():
            feeds[feed_url]['name'] = name_entry.get().strip()
            feeds[feed_url]['interval'] = int(interval_spinbox.get())
            self.config_manager.set('feeds', feeds)
            self.config_manager.save()
            self._load_saved_feeds()
            dialog.destroy()
            self.update_status(f"Feed '{feeds[feed_url]['name']}' aktualisiert")

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Speichern", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _remove_selected_feed(self, event=None):
        """Entfernt die ausgewählten Feeds"""
        selection = self.feed_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Bitte einen Feed auswählen!")
            return

        if not messagebox.askyesno("Bestätigung", "Ausgewählte Feeds wirklich entfernen?"):
            return

        feeds = self.config_manager.get('feeds', {})

        for index in reversed(selection):
            feed_text = self.feed_listbox.get(index)
            feed_url = self._get_feed_url_from_text(feed_text)

            if feed_url in feeds:
                # Auto-Refresh stoppen
                self._cancel_auto_refresh(feed_url)

                # Tab schließen
                if feed_url in self.feed_tabs:
                    for i, tab_id in enumerate(self.notebook.tabs()):
                        if self.notebook.tab(tab_id, 'text') == feeds[feed_url]['name']:
                            self.notebook.forget(i)
                            break
                    del self.feed_tabs[feed_url]

                # Feed entfernen
                del feeds[feed_url]
                logger.info(f"Feed entfernt: {feed_url}")

        self.config_manager.set('feeds', feeds)
        self.config_manager.save()
        self._load_saved_feeds()
        self.update_status("Feed(s) entfernt")

    def _load_saved_feeds(self):
        """Lädt die gespeicherten Feeds in die Liste"""
        self.feed_listbox.delete(0, tk.END)
        feeds = self.config_manager.get('feeds', {})

        for url, data in feeds.items():
            interval_text = f" [{data['interval']}min]" if data.get('interval', 0) > 0 else ""
            self.feed_listbox.insert(tk.END, f"{data['name']}{interval_text}")

    def _get_feed_url_from_text(self, feed_text: str) -> Optional[str]:
        """Extrahiert die Feed-URL aus dem Listbox-Text"""
        feeds = self.config_manager.get('feeds', {})
        feed_name = feed_text.split('[')[0].strip()

        for url, data in feeds.items():
            if data['name'] == feed_name:
                return url
        return None

    def _load_selected_feeds(self):
        """Lädt die ausgewählten Feeds"""
        selection = self.feed_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Bitte mindestens einen Feed auswählen!")
            return

        feeds = self.config_manager.get('feeds', {})

        for index in selection:
            feed_text = self.feed_listbox.get(index)
            feed_url = self._get_feed_url_from_text(feed_text)

            if feed_url:
                self._load_feed_in_tab(feed_url, feeds[feed_url])

    def _load_feed_in_tab(self, feed_url: str, feed_data: dict):
        """Lädt einen Feed in einem Tab"""
        feed_name = feed_data['name']

        # Prüfen ob Tab bereits existiert
        if feed_url in self.feed_tabs:
            # Tab aktivieren
            for i, tab_id in enumerate(self.notebook.tabs()):
                if self.notebook.tab(tab_id, 'text') == feed_name:
                    self.notebook.select(i)
                    break
            # Feed aktualisieren
            self._refresh_feed(feed_url, feed_data)
            return

        # Neuen Tab erstellen
        tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(tab_frame, text=feed_name)
        self.feed_tabs[feed_url] = tab_frame

        # Toolbar
        toolbar = ttk.Frame(tab_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            toolbar,
            text="🔄 Aktualisieren",
            command=lambda: self._refresh_feed(feed_url, feed_data)
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="❌ Schließen",
            command=lambda: self._close_tab(feed_url, feed_name)
        ).pack(side=tk.LEFT, padx=2)

        ttk.Label(
            toolbar,
            text=f"Letztes Update: Nie",
            font=('Arial', 8)
        ).pack(side=tk.RIGHT, padx=5)

        # Content-Frame mit Scrollbar
        content_frame = ttk.Frame(tab_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(content_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        theme = self.THEMES[self.current_theme]
        text_widget = tk.Text(
            content_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            bg=theme['text_bg'],
            fg=theme['text_fg'],
            font=('Arial', 10)
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        # Feed laden
        self._refresh_feed(feed_url, feed_data)

        # Tab aktivieren
        self.notebook.select(tab_frame)

        # Auto-Refresh einrichten
        if feed_data.get('interval', 0) > 0:
            self._setup_auto_refresh(feed_url, feed_data)

    def _refresh_feed(self, feed_url: str, feed_data: dict):
        """Aktualisiert einen Feed"""
        if feed_url not in self.feed_tabs:
            return

        tab_frame = self.feed_tabs[feed_url]

        # Text-Widget finden
        text_widget = None
        update_label = None

        for child in tab_frame.winfo_children():
            if isinstance(child, ttk.Frame):
                for subchild in child.winfo_children():
                    if isinstance(subchild, tk.Text):
                        text_widget = subchild
                    elif isinstance(subchild, ttk.Label) and "Letztes Update" in subchild.cget("text"):
                        update_label = subchild

        if not text_widget:
            return

        # Loading-Anzeige
        text_widget.config(state=tk.NORMAL)
        text_widget.delete('1.0', tk.END)
        text_widget.insert('1.0', f"📡 Lade Feed über TOR...\n\n{feed_url}")
        text_widget.config(state=tk.DISABLED)

        self.update_status(f"Lade Feed: {feed_data['name']}")

        # Feed in Thread laden
        def load_feed():
            try:
                entries = self.feed_manager.fetch_feed(feed_url)

                # UI in Main-Thread aktualisieren
                self.root.after(0, lambda: self._display_feed_content(
                    text_widget, entries, feed_url, feed_data, update_label
                ))

            except Exception as e:
                logger.error(f"Fehler beim Laden des Feeds {feed_url}: {e}")
                self.root.after(0, lambda: self._display_feed_error(
                    text_widget, str(e), feed_data
                ))

        thread = threading.Thread(target=load_feed, daemon=True)
        thread.start()

    def _display_feed_content(self, text_widget, entries, feed_url, feed_data, update_label):
        """Zeigt den Feed-Inhalt an"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete('1.0', tk.END)

        if not entries:
            text_widget.insert('1.0', "Keine Einträge gefunden.")
        else:
            # Feed-Header
            text_widget.insert('1.0', f"📰 {feed_data['name']}\n")
            text_widget.insert(tk.END, f"{'=' * 80}\n\n")

            # Einträge anzeigen
            for i, entry in enumerate(entries[:50], 1):  # Max 50 Einträge
                # Titel
                text_widget.insert(tk.END, f"{i}. ", 'number')
                text_widget.insert(tk.END, f"{entry.get('title', 'Kein Titel')}\n", 'title')

                # Datum
                if 'published' in entry:
                    text_widget.insert(tk.END, f"   📅 {entry['published']}\n", 'date')

                # Zusammenfassung
                if 'summary' in entry:
                    summary = entry['summary'][:200] + "..." if len(entry['summary']) > 200 else entry['summary']
                    text_widget.insert(tk.END, f"   {summary}\n", 'summary')

                # Link
                if 'link' in entry:
                    text_widget.insert(tk.END, f"   🔗 ", 'link_icon')
                    text_widget.insert(tk.END, f"{entry['link']}\n", 'link')

                    # Link anklickbar machen
                    start_index = text_widget.search(entry['link'], '1.0', tk.END)
                    if start_index:
                        end_index = f"{start_index}+{len(entry['link'])}c"
                        text_widget.tag_add(f"link_{i}", start_index, end_index)
                        text_widget.tag_config(f"link_{i}", foreground='blue', underline=True)
                        text_widget.tag_bind(
                            f"link_{i}",
                            "<Button-1>",
                            lambda e, url=entry['link']: self._open_link_in_tor_browser(url)
                        )
                        text_widget.tag_bind(f"link_{i}", "<Enter>", lambda e: text_widget.config(cursor="hand2"))
                        text_widget.tag_bind(f"link_{i}", "<Leave>", lambda e: text_widget.config(cursor=""))

                text_widget.insert(tk.END, "\n" + "-" * 80 + "\n\n")

            # Tags konfigurieren
            text_widget.tag_config('title', font=('Arial', 11, 'bold'))
            text_widget.tag_config('date', foreground='gray', font=('Arial', 8))
            text_widget.tag_config('summary', font=('Arial', 9))
            text_widget.tag_config('number', foreground='blue', font=('Arial', 10, 'bold'))

        text_widget.config(state=tk.DISABLED)

        # Update-Zeit aktualisieren
        if update_label:
            update_label.config(text=f"Letztes Update: {datetime.now().strftime('%H:%M:%S')}")

        self.update_status(f"Feed geladen: {feed_data['name']} ({len(entries)} Einträge)")
        logger.info(f"Feed geladen: {feed_data['name']} ({len(entries)} Einträge)")

    def _display_feed_error(self, text_widget, error, feed_data):
        """Zeigt einen Feed-Ladefehler an"""
        text_widget.config(state=tk.NORMAL)
        text_widget.delete('1.0', tk.END)
        text_widget.insert('1.0', f"❌ Fehler beim Laden des Feeds '{feed_data['name']}':\n\n{error}")
        text_widget.config(state=tk.DISABLED)

        self.update_status(f"Fehler beim Laden: {feed_data['name']}")

    def _open_link_in_tor_browser(self, url: str):
        """Öffnet einen Link im TOR Browser"""
        tor_browser_path = self.config_manager.get('tor_browser_path', '')

        if tor_browser_path:
            try:
                import subprocess
                subprocess.Popen([tor_browser_path, url])
                logger.info(f"Link im TOR Browser geöffnet: {url}")
            except Exception as e:
                logger.error(f"Fehler beim Öffnen des TOR Browsers: {e}")
                messagebox.showerror("Fehler", f"TOR Browser konnte nicht geöffnet werden:\n{e}")
        else:
            # Fallback: Standard-Browser
            if messagebox.askyesno(
                "TOR Browser nicht konfiguriert",
                "TOR Browser-Pfad ist nicht gesetzt.\nLink im Standard-Browser öffnen?"
            ):
                webbrowser.open(url)

    def _close_tab(self, feed_url: str, feed_name: str):
        """Schließt einen Feed-Tab"""
        if feed_url in self.feed_tabs:
            for i, tab_id in enumerate(self.notebook.tabs()):
                if self.notebook.tab(tab_id, 'text') == feed_name:
                    self.notebook.forget(i)
                    break

            del self.feed_tabs[feed_url]
            self._cancel_auto_refresh(feed_url)
            logger.info(f"Tab geschlossen: {feed_name}")

    def _setup_auto_refresh(self, feed_url: str, feed_data: dict):
        """Richtet Auto-Refresh für einen Feed ein"""
        interval = feed_data.get('interval', 0)
        if interval <= 0:
            return

        # Alte Job abbrechen falls vorhanden
        self._cancel_auto_refresh(feed_url)

        # Neue Job erstellen
        def refresh_job():
            self._refresh_feed(feed_url, feed_data)
            # Nächsten Job planen
            job_id = self.root.after(interval * 60 * 1000, refresh_job)
            self.auto_refresh_jobs[feed_url] = job_id

        job_id = self.root.after(interval * 60 * 1000, refresh_job)
        self.auto_refresh_jobs[feed_url] = job_id

        logger.info(f"Auto-Refresh eingerichtet für {feed_data['name']}: {interval} Minuten")

    def _cancel_auto_refresh(self, feed_url: str):
        """Bricht Auto-Refresh für einen Feed ab"""
        if feed_url in self.auto_refresh_jobs:
            self.root.after_cancel(self.auto_refresh_jobs[feed_url])
            del self.auto_refresh_jobs[feed_url]

    def _set_auto_refresh(self):
        """Setzt Auto-Refresh für den ausgewählten Feed"""
        selection = self.feed_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Bitte einen Feed auswählen!")
            return

        feed_text = self.feed_listbox.get(selection[0])
        feed_url = self._get_feed_url_from_text(feed_text)

        feeds = self.config_manager.get('feeds', {})
        if feed_url not in feeds:
            return

        current_interval = feeds[feed_url].get('interval', 0)

        new_interval = simpledialog.askinteger(
            "Auto-Refresh",
            f"Intervall in Minuten (0 = deaktiviert):\n\nAktuell: {current_interval} Minuten",
            initialvalue=current_interval,
            minvalue=0,
            maxvalue=1440
        )

        if new_interval is not None:
            feeds[feed_url]['interval'] = new_interval
            self.config_manager.set('feeds', feeds)
            self.config_manager.save()

            # Auto-Refresh neu einrichten
            if feed_url in self.feed_tabs:
                if new_interval > 0:
                    self._setup_auto_refresh(feed_url, feeds[feed_url])
                else:
                    self._cancel_auto_refresh(feed_url)

            self._load_saved_feeds()
            self.update_status(f"Auto-Refresh aktualisiert: {feeds[feed_url]['name']}")

    def _refresh_all_feeds(self, event=None):
        """Aktualisiert alle geöffneten Feeds"""
        if not self.feed_tabs:
            messagebox.showinfo("Info", "Keine Feeds geöffnet!")
            return

        feeds = self.config_manager.get('feeds', {})
        for feed_url in list(self.feed_tabs.keys()):
            if feed_url in feeds:
                self._refresh_feed(feed_url, feeds[feed_url])

        self.update_status("Alle Feeds werden aktualisiert...")

    def _check_tor_status(self):
        """Prüft den TOR-Status"""
        self.update_status("Prüfe TOR-Verbindung...")

        def check():
            is_connected, ip = self.tor_handler.check_tor_connection()

            def update_ui():
                if is_connected:
                    self.tor_status_label.config(text=f"TOR: Verbunden ({ip})")
                    messagebox.showinfo(
                        "TOR Status",
                        f"✓ TOR-Verbindung aktiv\n\nAktuelle IP: {ip}"
                    )
                    self.update_status("TOR-Verbindung aktiv")
                else:
                    self.tor_status_label.config(text="TOR: Nicht verbunden")
                    messagebox.showwarning(
                        "TOR Status",
                        "✗ Keine TOR-Verbindung\n\n"
                        "Bitte stellen Sie sicher, dass der TOR-Service läuft.\n"
                        "Feeds werden ohne TOR geladen!"
                    )
                    self.update_status("TOR nicht verfügbar")

            self.root.after(0, update_ui)

        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def _tor_settings_dialog(self):
        """Dialog für TOR-Einstellungen"""
        dialog = tk.Toplevel(self.root)
        dialog.title("TOR-Einstellungen")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # TOR Proxy Host
        ttk.Label(dialog, text="SOCKS5 Proxy Host:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        host_entry = ttk.Entry(dialog, width=30)
        host_entry.insert(0, self.config_manager.get('tor_proxy_host', '127.0.0.1'))
        host_entry.grid(row=0, column=1, padx=10, pady=10)

        # TOR Proxy Port
        ttk.Label(dialog, text="SOCKS5 Proxy Port:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        port_entry = ttk.Entry(dialog, width=30)
        port_entry.insert(0, str(self.config_manager.get('tor_proxy_port', 9050)))
        port_entry.grid(row=1, column=1, padx=10, pady=10)

        # TOR Browser Pfad
        ttk.Label(dialog, text="TOR Browser Pfad:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        browser_entry = ttk.Entry(dialog, width=30)
        browser_entry.insert(0, self.config_manager.get('tor_browser_path', ''))
        browser_entry.grid(row=2, column=1, padx=10, pady=10)

        ttk.Label(
            dialog,
            text="(Optional: Pfad zur TOR Browser Executable)",
            font=('Arial', 8),
            foreground='gray'
        ).grid(row=3, column=1, padx=10, sticky=tk.W)

        def save_settings():
            self.config_manager.set('tor_proxy_host', host_entry.get().strip())
            self.config_manager.set('tor_proxy_port', int(port_entry.get().strip()))
            self.config_manager.set('tor_browser_path', browser_entry.get().strip())
            self.config_manager.save()

            # TOR Handler neu initialisieren
            self.tor_handler = TorHandler(self.config_manager)
            self.feed_manager.tor_handler = self.tor_handler

            dialog.destroy()
            messagebox.showinfo("Erfolg", "TOR-Einstellungen gespeichert!")
            self._check_tor_status()

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="Speichern", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def _show_feed_context_menu(self, event):
        """Zeigt das Kontextmenü für Feeds"""
        try:
            self.feed_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.feed_context_menu.grab_release()

    def _export_settings(self):
        """Exportiert die Einstellungen"""
        from tkinter import filedialog
        import json

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.config_manager.config, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Erfolg", "Einstellungen erfolgreich exportiert!")
                logger.info(f"Einstellungen exportiert nach: {filename}")
            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Exportieren:\n{e}")
                logger.error(f"Export-Fehler: {e}")

    def _import_settings(self):
        """Importiert Einstellungen"""
        from tkinter import filedialog
        import json

        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self.config_manager.config = config
                self.config_manager.save()

                messagebox.showinfo(
                    "Erfolg",
                    "Einstellungen erfolgreich importiert!\nAnwendung wird neu geladen."
                )
                logger.info(f"Einstellungen importiert von: {filename}")

                # Anwendung neu laden
                self.root.destroy()
                main()

            except Exception as e:
                messagebox.showerror("Fehler", f"Fehler beim Importieren:\n{e}")
                logger.error(f"Import-Fehler: {e}")

    def _show_shortcuts(self):
        """Zeigt alle Shortcuts an"""
        shortcuts_text = """
🔑 Tastatur-Shortcuts

Datei:
  Ctrl+E          Einstellungen exportieren
  Ctrl+I          Einstellungen importieren
  Ctrl+Q          Beenden

Feeds:
  Ctrl+N          Neuen Feed hinzufügen
  Delete          Feed entfernen
  F5              Alle Feeds aktualisieren

Ansicht:
  Ctrl+D          Dark Mode
  Ctrl+L          Light Mode

TOR:
  Ctrl+T          TOR-Status prüfen

Hilfe:
  F1              Diese Hilfe
        """

        messagebox.showinfo("Tastatur-Shortcuts", shortcuts_text)

    def _show_about(self):
        """Zeigt Über-Dialog"""
        about_text = """
🔒 TOR RSS Feed Reader v1.0

Ein sicherer RSS Feed Reader mit TOR-Integration

Entwickelt mit:
• Python 3
• Tkinter
• feedparser
• requests + PySocks

Features:
✓ TOR-Netzwerk Integration
✓ Multi-Feed Support
✓ Auto-Refresh pro Feed
✓ Dark/Light Theme
✓ Einstellungen Export/Import
✓ Tastatur-Shortcuts

© 2024 - Open Source
        """

        messagebox.showinfo("Über", about_text)

    def update_status(self, message: str):
        """Aktualisiert die Statusleiste"""
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def _quit_app(self):
        """Beendet die Anwendung"""
        if messagebox.askyesno("Beenden", "Anwendung wirklich beenden?"):
            # Alle Auto-Refresh Jobs abbrechen
            for feed_url in list(self.auto_refresh_jobs.keys()):
                self._cancel_auto_refresh(feed_url)

            logger.info("Anwendung wird beendet")
            self.root.quit()


def main():
    """Hauptfunktion"""
    root = tk.Tk()
    app = RSSFeedReader(root)
    root.mainloop()


if __name__ == "__main__":
    main()
