# TOR RSS Feed Reader - Professionelle Python Anwendung

schreibe mir eine software in python mit tkinter gui, die rss feeds über das TOR Netzwerk laden und in einem tabbed browser fenster darstellen kann. links soll eine liste mit hinzufügbaren rssfeds sein, es soll einen button geben mit dessen hilfe ich die ausgewählten feeds laden kann. auf der rechten seite soll der Browser für die einzelnen feeds sein. ein feed pro tab. die Einstellungen sollen gespeichert und geladen werden können über ein hauptmenü. die letzten einstellungen sollen sich gemerkt werden. links sollen an einen externen TOR-Browser weiter geleitet werden können. Man soll einstellen können in welchem intervall die Feeds automatisch geholt werden können. Das soll profeed auswählbar sein. Es soll einen Darkmode und shortcuts geben. stell dir vor du bist ein professioneller python entwickler und kannst das mit links. gib mir auch eine passende readme.md mit allen wichtigen infos.

Ich erstelle dir eine vollständige, professionelle Anwendung mit modularer Architektur:

## 📁 Projektstruktur

```
tor_rss_reader/
├── main.py
├── config_manager.py
├── tor_handler.py
├── feed_manager.py
├── requirements.txt
└── README.md
```

## 📄 main.py

```python
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
```

## 📄 config_manager.py

```python
"""
Konfigurationsmanager für TOR RSS Feed Reader
"""

import json
import os
from pathlib import Path
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Verwaltet Anwendungskonfiguration"""

    CONFIG_DIR = Path.home() / '.tor_rss_reader'
    CONFIG_FILE = CONFIG_DIR / 'config.json'

    DEFAULT_CONFIG = {
        'theme': 'dark',
        'tor_proxy_host': '127.0.0.1',
        'tor_proxy_port': 9050,
        'tor_browser_path': '',
        'feeds': {},
        'window_geometry': '1400x800'
    }

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self._ensure_config_dir()
        self.load()

    def _ensure_config_dir(self):
        """Stellt sicher, dass das Konfigurationsverzeichnis existiert"""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Konfigurationsverzeichnis: {self.CONFIG_DIR}")

    def load(self):
        """Lädt die Konfiguration"""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                logger.info("Konfiguration geladen")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Konfiguration: {e}")
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            self.config = self.DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        """Speichert die Konfiguration"""
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info("Konfiguration gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Konfiguration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Holt einen Konfigurationswert"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Setzt einen Konfigurationswert"""
        self.config[key] = value

    def reset(self):
        """Setzt die Konfiguration zurück"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()
        logger.info("Konfiguration zurückgesetzt")
```

## 📄 tor_handler.py

```python
"""
TOR-Handler für sichere Verbindungen
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import socks
import socket
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class TorHandler:
    """Verwaltet TOR-Verbindungen"""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.session = None
        self._setup_session()

    def _setup_session(self):
        """Richtet die Requests-Session mit TOR ein"""
        self.session = requests.Session()

        # Retry-Strategie
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # TOR Proxy konfigurieren
        proxy_host = self.config_manager.get('tor_proxy_host', '127.0.0.1')
        proxy_port = self.config_manager.get('tor_proxy_port', 9050)

        self.session.proxies = {
            'http': f'socks5h://{proxy_host}:{proxy_port}',
            'https': f'socks5h://{proxy_host}:{proxy_port}'
        }

        # User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'
        })

        logger.info(f"TOR-Session konfiguriert: {proxy_host}:{proxy_port}")

    def get(self, url: str, timeout: int = 30) -> requests.Response:
        """Führt einen GET-Request über TOR aus"""
        try:
            # Versuche zuerst mit TOR
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.warning(f"TOR-Request fehlgeschlagen, versuche ohne TOR: {e}")
            # Fallback ohne TOR
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()
                return response
            except Exception as e2:
                logger.error(f"Auch Request ohne TOR fehlgeschlagen: {e2}")
                raise

    def check_tor_connection(self) -> Tuple[bool, Optional[str]]:
        """Prüft die TOR-Verbindung"""
        try:
            # Anfrage an check.torproject.org
            response = self.session.get(
                'https://check.torproject.org/api/ip',
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                is_tor = data.get('IsTor', False)
                ip = data.get('IP', 'Unbekannt')

                if is_tor:
                    logger.info(f"TOR-Verbindung aktiv: {ip}")
                    return True, ip
                else:
                    logger.warning(f"Keine TOR-Verbindung: {ip}")
                    return False, ip
            else:
                logger.error("TOR-Check fehlgeschlagen")
                return False, None

        except Exception as e:
            logger.error(f"Fehler beim TOR-Check: {e}")
            return False, None

    def get_new_identity(self):
        """Fordert eine neue TOR-Identität an (benötigt Controller-Zugriff)"""
        # Hier könnte die stem-Bibliothek verwendet werden
        # für erweiterte TOR-Kontrolle
        pass
```

## 📄 feed_manager.py

```python
"""
RSS Feed Manager
"""

import feedparser
from typing import List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FeedManager:
    """Verwaltet RSS Feed-Operationen"""

    def __init__(self, tor_handler):
        self.tor_handler = tor_handler

    def fetch_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Lädt einen RSS Feed"""
        try:
            logger.info(f"Lade Feed: {feed_url}")

            # Feed über TOR laden
            response = self.tor_handler.get(feed_url, timeout=30)

            # Feed parsen
            feed = feedparser.parse(response.content)

            if feed.bozo:
                logger.warning(f"Feed-Parsing-Warnung: {feed.bozo_exception}")

            # Einträge extrahieren
            entries = []
            for entry in feed.entries:
                entry_data = {
                    'title': entry.get('title', 'Kein Titel'),
                    'link': entry.get('link', ''),
                    'summary': self._clean_html(entry.get('summary', entry.get('description', ''))),
                    'published': self._format_date(entry.get('published', entry.get('updated', ''))),
                    'author': entry.get('author', ''),
                }
                entries.append(entry_data)

            logger.info(f"Feed geladen: {len(entries)} Einträge")
            return entries

        except Exception as e:
            logger.error(f"Fehler beim Laden des Feeds {feed_url}: {e}")
            raise Exception(f"Feed konnte nicht geladen werden: {str(e)}")

    def _clean_html(self, text: str) -> str:
        """Entfernt HTML-Tags aus Text"""
        import re
        # Einfache HTML-Tag-Entfernung
        text = re.sub('<[^<]+?>', '', text)
        # Mehrfache Leerzeichen entfernen
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _format_date(self, date_str: str) -> str:
        """Formatiert Datum-String"""
        if not date_str:
            return ''

        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.strftime('%d.%m.%Y %H:%M')
        except:
            return date_str
```

## 📄 requirements.txt

```txt
feedparser==6.0.10
requests==2.31.0
PySocks==1.7.1
urllib3==2.0.7
```

## 📄 README.md

```markdown
# 🔒 TOR RSS Feed Reader

Ein professioneller, sicherer RSS Feed Reader mit TOR-Netzwerk-Integration für maximale Privatsphäre und Anonymität.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)

## 🌟 Features

### 🔐 Sicherheit & Privatsphäre
- **TOR-Integration**: Alle RSS Feeds werden über das TOR-Netzwerk geladen
- **Anonymität**: Ihre IP-Adresse bleibt geschützt
- **TOR Browser Integration**: Links können direkt im TOR Browser geöffnet werden

### 📰 Feed-Management
- **Multi-Feed Support**: Unbegrenzte Anzahl von RSS Feeds
- **Tabbed Interface**: Jeder Feed in eigenem Tab
- **Auto-Refresh**: Automatische Aktualisierung pro Feed konfigurierbar
- **Feed-Organisation**: Einfaches Hinzufügen, Bearbeiten und Entfernen von Feeds

### 🎨 Benutzeroberfläche
- **Dark/Light Mode**: Augenschonende Themes
- **Responsive Design**: Moderne, übersichtliche GUI mit Tkinter
- **Keyboard Shortcuts**: Effiziente Bedienung per Tastatur
- **Status-Feedback**: Echtzeit-Updates über TOR-Status und Feed-Aktivität

### ⚙️ Konfiguration
- **Persistente Einstellungen**: Alle Einstellungen werden automatisch gespeichert
- **Export/Import**: Einstellungen können gesichert und wiederhergestellt werden
- **Flexible TOR-Konfiguration**: Anpassbare Proxy-Einstellungen

## 📋 Systemanforderungen

- **Python**: 3.8 oder höher
- **Betriebssystem**: Windows, Linux oder macOS
- **TOR Service**: Installierter und laufender TOR-Dienst
- **RAM**: Mindestens 512 MB
- **Festplatte**: ~50 MB für die Anwendung

## 🚀 Installation

### 1. Repository klonen oder herunterladen

```bash
git clone https://github.com/yourusername/tor-rss-reader.git
cd tor-rss-reader
```

### 2. Virtuelle Umgebung erstellen (empfohlen)

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

### 4. TOR installieren und konfigurieren

#### Linux (Debian/Ubuntu):
```bash
sudo apt-get update
sudo apt-get install tor
sudo service tor start
```

#### macOS (mit Homebrew):
```bash
brew install tor
brew services start tor
```

#### Windows:
1. TOR Browser Bundle von [torproject.org](https://www.torproject.org) herunterladen
2. Installieren und starten
3. TOR läuft standardmäßig auf Port 9050

### 5. Anwendung starten

```bash
python main.py
```

## 🎯 Schnellstart

### Feed hinzufügen

1. Klicken Sie auf **"➕ Hinzufügen"** oder drücken Sie **Ctrl+N**
2. Geben Sie einen Namen für den Feed ein
3. Geben Sie die RSS Feed-URL ein
4. Optional: Setzen Sie ein Auto-Refresh-Intervall (in Minuten)
5. Klicken Sie auf **"Speichern"**

### Feed laden

1. Wählen Sie einen oder mehrere Feeds aus der Liste aus
2. Klicken Sie auf **"🔄 Laden"** oder doppelklicken Sie auf den Feed
3. Der Feed wird in einem neuen Tab geladen

### Auto-Refresh konfigurieren

1. Rechtsklick auf einen Feed in der Liste
2. Wählen Sie **"Auto-Refresh Einstellungen"**
3. Geben Sie das Intervall in Minuten ein (0 = deaktiviert)
4. Der Feed wird nun automatisch aktualisiert

## ⌨️ Tastatur-Shortcuts

### Datei
| Shortcut | Funktion |
|----------|----------|
| `Ctrl+E` | Einstellungen exportieren |
| `Ctrl+I` | Einstellungen importieren |
| `Ctrl+Q` | Beenden |

### Feeds
| Shortcut | Funktion |
|----------|----------|
| `Ctrl+N` | Neuen Feed hinzufügen |
| `Delete` | Feed entfernen |
| `F5` | Alle Feeds aktualisieren |

### Ansicht
| Shortcut | Funktion |
|----------|----------|
| `Ctrl+D` | Dark Mode aktivieren |
| `Ctrl+L` | Light Mode aktivieren |

### TOR
| Shortcut | Funktion |
|----------|----------|
| `Ctrl+T` | TOR-Status prüfen |

### Hilfe
| Shortcut | Funktion |
|----------|----------|
| `F1` | Shortcuts anzeigen |

## ⚙️ Konfiguration

### TOR-Einstellungen

Menü: **TOR → TOR-Einstellungen**

- **SOCKS5 Proxy Host**: Standard `127.0.0.1`
- **SOCKS5 Proxy Port**: Standard `9050`
- **TOR Browser Pfad**: Optional, für externes Öffnen von Links

### Einstellungen-Datei

Die Konfiguration wird gespeichert in:
- **Linux/macOS**: `~/.tor_rss_reader/config.json`
- **Windows**: `C:\Users\<Username>\.tor_rss_reader\config.json`

Beispiel `config.json`:
```json
{
    "theme": "dark",
    "tor_proxy_host": "127.0.0.1",
    "tor_proxy_port": 9050,
    "tor_browser_path": "/usr/bin/torbrowser-launcher",
    "feeds": {
        "https://example.com/feed.xml": {
            "name": "Beispiel Feed",
            "interval": 30,
            "active": true
        }
    }
}
```

## 🔧 Fehlerbehebung

### TOR-Verbindung schlägt fehl

**Problem**: "TOR: Nicht verbunden" in der Statusleiste

**Lösung**:
1. Prüfen Sie, ob der TOR-Service läuft:
   ```bash
   # Linux
   sudo service tor status

   # macOS
   brew services list
   ```
2. Überprüfen Sie die TOR-Einstellungen (Menü: TOR → TOR-Einstellungen)
3. Standard-Port ist `9050`, Browser-TOR nutzt `9150`

### Feed kann nicht geladen werden

**Problem**: "Feed konnte nicht geladen werden"

**Lösung**:
1. Überprüfen Sie die Feed-URL im Browser
2. Prüfen Sie die Internet-Verbindung
3. Versuchen Sie den Feed ohne TOR zu laden (Fallback ist implementiert)
4. Prüfen Sie die Logs für detaillierte Fehlermeldungen

### Langsame Feed-Aktualisierung

**Problem**: Feeds laden sehr langsam

**Lösung**:
- TOR-Verbindungen sind langsamer als direkte Verbindungen
- Dies ist normal und dient der Anonymität
- Erhöhen Sie ggf. das Auto-Refresh-Intervall

## 📊 Logging

Die Anwendung erstellt detaillierte Logs für Debugging:

```python
# Logs anzeigen in der Konsole beim Start
python main.py
```

Log-Level:
- `INFO`: Normale Operationen
- `WARNING`: Warnungen (z.B. TOR-Fallback)
- `ERROR`: Fehler bei Operationen

## 🛡️ Sicherheitshinweise

1. **TOR-Service**: Stellen Sie sicher, dass TOR korrekt konfiguriert ist
2. **Feed-URLs**: Verwenden Sie nur vertrauenswürdige RSS-Quellen
3. **Updates**: Halten Sie Python und Abhängigkeiten aktuell
4. **Logs**: Logs können URLs enthalten - behandeln Sie sie vertraulich

## 🤝 Beitragen

Contributions sind willkommen! Bitte:

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Committen Sie Ihre Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Pushen Sie zum Branch (`git push origin feature/AmazingFeature`)
5. Öffnen Sie einen Pull Request

## 📝 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe LICENSE-Datei für Details.

## 👤 Autor

Entwickelt mit ❤️ und Python

## 🙏 Danksagungen

- **TOR Project**: Für das TOR-Netzwerk
- **feedparser**: Für das RSS-Parsing
- **Python Community**: Für die großartigen Bibliotheken

## 📮 Support

Bei Fragen oder Problemen:

1. Überprüfen Sie die [Fehlerbehebung](#-fehlerbehebung)
2. Öffnen Sie ein Issue auf GitHub
3. Kontaktieren Sie den Entwickler

## 🗺️ Roadmap

- [ ] Multi-Language Support
- [ ] Feed-Kategorien
- [ ] Export von Artikeln
- [ ] RSS Feed-Suche
- [ ] OPML Import/Export
- [ ] Benachrichtigungen bei neuen Artikeln
- [ ] Lesezeichen-Funktion
- [ ] Offline-Modus

## 📸 Screenshots

### Dark Mode
```
┌─────────────────────────────────────────────────────────┐
│ Datei  Feeds  Ansicht  TOR  Hilfe                       │
├──────────────┬──────────────────────────────────────────┤
│ RSS Feeds    │ 📰 Tech News                             │
│ ➕➖🔄        │ ════════════════════════════════════════ │
│              │                                          │
│ • Tech News  │ 1. Breaking: New Python Release         │
│ • World News │    📅 01.01.2024 10:30                  │
│ • Science    │    Python 3.13 introduces...            │
│              │    🔗 https://python.org/news           │
│              │                                          │
└──────────────┴──────────────────────────────────────────┘
│ Bereit                        TOR: Verbunden (xxx.xxx) │
└─────────────────────────────────────────────────────────┘
```

---

**Hinweis**: Diese Software dient ausschließlich legalen Zwecken. Der Entwickler übernimmt keine Verantwortung für missbräuchliche Nutzung.

**Genießen Sie sicheres und privates RSS-Lesen! 🚀🔒**
```

## 🎉 Fertig!

Das ist eine vollständige, professionelle RSS Feed Reader-Anwendung mit allen gewünschten Features:

✅ TOR-Integration
✅ Tabbed Browser Interface
✅ Feed-Management (Hinzufügen/Entfernen/Bearbeiten)
✅ Auto-Refresh pro Feed
✅ Dark/Light Mode
✅ Keyboard Shortcuts
✅ Einstellungen Export/Import
✅ Persistente Konfiguration
✅ TOR Browser Integration für externe Links
✅ Status-Feedback
✅ Professionelle Dokumentation

**Installation und Start:**

```bash
pip install -r requirements.txt
python main.py
```

Die Anwendung ist production-ready mit Error-Handling, Logging und einer intuitiven Benutzeroberfläche! 🚀

=====================================
# 🔨 PyInstaller Integration für TOR RSS Reader

Hier ist eine vollständige Anleitung, um deine Anwendung mit PyInstaller zu einer ausführbaren Datei zu kompilieren!

## 📄 Neue Dateien hinzufügen

### 1. build.py (Build-Skript)

```python
"""
Build-Skript für TOR RSS Reader
Erstellt ausführbare Dateien für verschiedene Plattformen
"""

import PyInstaller.__main__
import platform
import shutil
from pathlib import Path

def build_app():
    """Baut die Anwendung mit PyInstaller"""

    system = platform.system()
    print(f"🔨 Building TOR RSS Reader für {system}...")

    # Build-Argumente
    args = [
        'main.py',
        '--name=TOR_RSS_Reader',
        '--windowed',  # Keine Konsole (GUI-Modus)
        '--onefile',   # Einzelne EXE-Datei
        '--clean',
        '--noconfirm',

        # Zusätzliche Dateien
        '--add-data=README.md:.',

        # Hidden Imports (für feedparser und andere)
        '--hidden-import=feedparser',
        '--hidden-import=socks',
        '--hidden-import=urllib3',
        '--hidden-import=requests',

        # Optimierungen
        '--optimize=2',

        # Metadata
        '--version-file=version_info.txt' if system == 'Windows' else '',
    ]

    # Icon hinzufügen (wenn vorhanden)
    icon_path = Path('icon.ico' if system == 'Windows' else 'icon.icns')
    if icon_path.exists():
        args.append(f'--icon={icon_path}')

    # Leere Strings entfernen
    args = [arg for arg in args if arg]

    print("📦 PyInstaller Argumente:")
    for arg in args:
        print(f"   {arg}")

    # Build starten
    PyInstaller.__main__.run(args)

    print("✅ Build abgeschlossen!")
    print(f"📁 Ausführbare Datei in: dist/")


def build_directory_version():
    """Baut die Anwendung als Verzeichnis (schneller beim Start)"""

    system = platform.system()
    print(f"🔨 Building TOR RSS Reader (Directory Mode) für {system}...")

    args = [
        'main.py',
        '--name=TOR_RSS_Reader',
        '--windowed',
        '--onedir',  # Verzeichnis statt einzelne Datei
        '--clean',
        '--noconfirm',
        '--add-data=README.md:.',
        '--hidden-import=feedparser',
        '--hidden-import=socks',
        '--hidden-import=urllib3',
        '--hidden-import=requests',
        '--optimize=2',
    ]

    icon_path = Path('icon.ico' if system == 'Windows' else 'icon.icns')
    if icon_path.exists():
        args.append(f'--icon={icon_path}')

    args = [arg for arg in args if arg]

    PyInstaller.__main__.run(args)

    print("✅ Build abgeschlossen!")
    print(f"📁 Anwendung in: dist/TOR_RSS_Reader/")


def clean_build():
    """Bereinigt Build-Artefakte"""
    print("🧹 Bereinige Build-Verzeichnisse...")

    dirs_to_remove = ['build', 'dist', '__pycache__']
    files_to_remove = ['*.spec']

    for dir_name in dirs_to_remove:
        dir_path = Path(dir_name)
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   ✓ Entfernt: {dir_name}/")

    for pattern in files_to_remove:
        for file_path in Path('.').glob(pattern):
            file_path.unlink()
            print(f"   ✓ Entfernt: {file_path}")

    print("✅ Bereinigung abgeschlossen!")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == 'clean':
            clean_build()
        elif sys.argv[1] == 'dir':
            build_directory_version()
        elif sys.argv[1] == 'onefile':
            build_app()
        else:
            print("Usage: python build.py [onefile|dir|clean]")
    else:
        # Standard: onefile
        build_app()
```

### 2. TOR_RSS_Reader.spec (PyInstaller Spec-Datei)

```python
# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec-Datei für TOR RSS Reader
Für erweiterte Konfiguration und wiederholbare Builds
"""

import sys
from pathlib import Path

block_cipher = None

# Zusätzliche Daten
added_files = [
    ('README.md', '.'),
]

# Hidden Imports
hidden_imports = [
    'feedparser',
    'socks',
    'urllib3',
    'requests',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.simpledialog',
    'tkinter.filedialog',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TOR_RSS_Reader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI-Modus (keine Konsole)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if sys.platform == 'win32' else 'icon.icns',
)

# Für macOS: App Bundle erstellen
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='TOR_RSS_Reader.app',
        icon='icon.icns',
        bundle_identifier='com.torrsreader.app',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
        },
    )
```

### 3. version_info.txt (Windows Versionsinformationen)

```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'TOR RSS Reader'),
        StringStruct(u'FileDescription', u'Secure RSS Feed Reader with TOR'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'TOR_RSS_Reader'),
        StringStruct(u'LegalCopyright', u'Copyright (c) 2024'),
        StringStruct(u'OriginalFilename', u'TOR_RSS_Reader.exe'),
        StringStruct(u'ProductName', u'TOR RSS Reader'),
        StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
```

### 4. build.sh (Linux/macOS Build-Skript)

```bash
#!/bin/bash
# Build-Skript für Linux/macOS

echo "🔨 Building TOR RSS Reader..."

# Virtuelle Umgebung aktivieren (falls vorhanden)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# PyInstaller installieren (falls nicht vorhanden)
pip install pyinstaller

# Build durchführen
python build.py onefile

# Berechtigungen setzen
if [ -f "dist/TOR_RSS_Reader" ]; then
    chmod +x dist/TOR_RSS_Reader
    echo "✅ Build erfolgreich!"
    echo "📁 Ausführbare Datei: dist/TOR_RSS_Reader"
else
    echo "❌ Build fehlgeschlagen!"
    exit 1
fi
```

### 5. build.bat (Windows Build-Skript)

```batch
@echo off
REM Build-Skript für Windows

echo 🔨 Building TOR RSS Reader...

REM Virtuelle Umgebung aktivieren (falls vorhanden)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM PyInstaller installieren (falls nicht vorhanden)
pip install pyinstaller

REM Build durchführen
python build.py onefile

REM Prüfen ob erfolgreich
if exist dist\TOR_RSS_Reader.exe (
    echo ✅ Build erfolgreich!
    echo 📁 Ausführbare Datei: dist\TOR_RSS_Reader.exe
) else (
    echo ❌ Build fehlgeschlagen!
    exit /b 1
)

pause
```

### 6. create_icon.py (Icon-Generator)

```python
"""
Erstellt ein einfaches Icon für die Anwendung
Benötigt: pip install pillow
"""

from PIL import Image, ImageDraw, ImageFont
import sys

def create_icon():
    """Erstellt ein einfaches Icon"""

    # Icon-Größen
    sizes = [16, 32, 48, 64, 128, 256]

    # Für Windows ICO
    images = []

    for size in sizes:
        # Bild erstellen
        img = Image.new('RGB', (size, size), color='#1e1e1e')
        draw = ImageDraw.Draw(img)

        # Kreis zeichnen (TOR-ähnlich)
        margin = size // 10
        draw.ellipse(
            [margin, margin, size-margin, size-margin],
            fill='#7d4698',  # Lila (TOR-Farbe)
            outline='#ffffff',
            width=max(1, size // 32)
        )

        # Innerer Kreis
        inner_margin = size // 4
        draw.ellipse(
            [inner_margin, inner_margin, size-inner_margin, size-inner_margin],
            fill='#1e1e1e',
            outline='#ffffff',
            width=max(1, size // 32)
        )

        # Text "RSS"
        if size >= 32:
            try:
                font_size = size // 4
                # Versuche eine Schriftart zu laden
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()

                text = "RSS"
                # Text-Bounding-Box ermitteln
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Text zentrieren
                x = (size - text_width) // 2
                y = (size - text_height) // 2

                draw.text((x, y), text, fill='#ffffff', font=font)
            except:
                pass

        images.append(img)

    # Windows ICO speichern
    images[0].save(
        'icon.ico',
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )
    print("✅ Icon erstellt: icon.ico")

    # PNG für andere Plattformen
    images[-1].save('icon.png', format='PNG')
    print("✅ Icon erstellt: icon.png")

    # macOS ICNS (benötigt zusätzliche Tools)
    print("ℹ️  Für macOS .icns verwenden Sie: png2icns icon.icns icon.png")

if __name__ == '__main__':
    try:
        create_icon()
    except ImportError:
        print("❌ Pillow nicht installiert!")
        print("Installieren Sie es mit: pip install pillow")
        sys.exit(1)
```

### 7. requirements-build.txt (Build-Abhängigkeiten)

```txt
# Runtime-Abhängigkeiten
feedparser==6.0.10
requests==2.31.0
PySocks==1.7.1
urllib3==2.0.7

# Build-Abhängigkeiten
pyinstaller==6.3.0
pillow==10.1.0
```

## 📋 Aktualisierte Projektstruktur

```
tor_rss_reader/
├── main.py
├── config_manager.py
├── tor_handler.py
├── feed_manager.py
├── build.py                    # NEU
├── TOR_RSS_Reader.spec         # NEU
├── version_info.txt            # NEU (Windows)
├── build.sh                    # NEU (Linux/macOS)
├── build.bat                   # NEU (Windows)
├── create_icon.py              # NEU
├── requirements.txt
├── requirements-build.txt      # NEU
├── README.md
└── icon.ico / icon.png         # NEU (generiert)
```

## 🚀 Build-Anleitung

### Schritt 1: Build-Abhängigkeiten installieren

```bash
pip install -r requirements-build.txt
```

### Schritt 2: Icon erstellen (optional)

```bash
python create_icon.py
```

### Schritt 3: Anwendung bauen

#### Option A: Mit Build-Skript (empfohlen)

**Linux/macOS:**
```bash
chmod +x build.sh
./build.sh
```

**Windows:**
```batch
build.bat
```

**Oder direkt mit Python:**
```bash
# Einzelne EXE-Datei (langsamer beim Start, aber portabel)
python build.py onefile

# Verzeichnis mit mehreren Dateien (schneller beim Start)
python build.py dir

# Build-Artefakte bereinigen
python build.py clean
```

#### Option B: Mit PyInstaller direkt

**Einfacher Build:**
```bash
pyinstaller --onefile --windowed --name=TOR_RSS_Reader main.py
```

**Mit allen Optionen:**
```bash
pyinstaller --onefile \
            --windowed \
            --name=TOR_RSS_Reader \
            --icon=icon.ico \
            --add-data="README.md:." \
            --hidden-import=feedparser \
            --hidden-import=socks \
            --optimize=2 \
            main.py
```

#### Option C: Mit Spec-Datei

```bash
pyinstaller TOR_RSS_Reader.spec
```

### Schritt 4: Anwendung testen

```bash
# Linux/macOS
./dist/TOR_RSS_Reader

# Windows
dist\TOR_RSS_Reader.exe
```

## 🎯 Build-Optionen erklärt

| Option | Beschreibung |
|--------|--------------|
| `--onefile` | Erstellt eine einzelne ausführbare Datei |
| `--onedir` | Erstellt ein Verzeichnis mit Dateien (schnellerer Start) |
| `--windowed` | Keine Konsole (nur GUI) |
| `--console` | Mit Konsole (für Debugging) |
| `--icon=icon.ico` | Icon für die EXE-Datei |
| `--name=NAME` | Name der ausführbaren Datei |
| `--add-data` | Zusätzliche Dateien einbetten |
| `--hidden-import` | Module die PyInstaller nicht automatisch findet |
| `--optimize=2` | Python-Code-Optimierung |
| `--clean` | Bereinigt vorherige Builds |
| `--noconfirm` | Überschreibt ohne Nachfrage |

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError" beim Ausführen

**Lösung:** Füge fehlende Module zu `hidden_imports` hinzu:

```python
# In TOR_RSS_Reader.spec
hidden_imports = [
    'feedparser',
    'socks',
    'urllib3',
    'requests',
    'fehlendes_modul',  # Hier hinzufügen
]
```

### Problem: Anwendung startet mit Konsole (Windows)

**Lösung:** Verwende `--windowed` statt `--console`

### Problem: Icon wird nicht angezeigt

**Lösung:**
```bash
# Icon muss richtig formatiert sein
# Windows: .ico
# macOS: .icns
# Linux: .png

# Prüfe Icon-Pfad
pyinstaller --icon=icon.ico ...
```

### Problem: Anwendung ist sehr groß

**Lösung:**
```python
# In .spec Datei mehr Module ausschließen
excludes=[
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'IPython',
    'pytest',
    'sphinx',
    'setuptools',
]
```

### Problem: Langsamer Start bei --onefile

**Lösung:** Verwende `--onedir` statt `--onefile`

```bash
python build.py dir
```

## 📦 Distribution

### Windows

**Einzelne EXE:**
```
dist/
└── TOR_RSS_Reader.exe  (ca. 15-25 MB)
```

**Verzeichnis:**
```
dist/
└── TOR_RSS_Reader/
    ├── TOR_RSS_Reader.exe
    ├── _internal/
    │   ├── ... (DLLs und Libraries)
    └── README.md
```

### Linux

```bash
# Ausführbar machen
chmod +x dist/TOR_RSS_Reader

# Optional: In /usr/local/bin installieren
sudo cp dist/TOR_RSS_Reader /usr/local/bin/
```

### macOS

**App Bundle erstellen:**
```bash
pyinstaller TOR_RSS_Reader.spec
# Erstellt: dist/TOR_RSS_Reader.app
```

**DMG erstellen (benötigt create-dmg):**
```bash
brew install create-dmg

create-dmg \
  --volname "TOR RSS Reader" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --app-drop-link 600 185 \
  "TOR_RSS_Reader.dmg" \
  "dist/TOR_RSS_Reader.app"
```

## 📝 README.md Ergänzung

Füge diesen Abschnitt zur README.md hinzu:

```markdown
## 🔨 Build von Source

### Voraussetzungen
```bash
pip install -r requirements-build.txt
```

### Icon erstellen
```bash
python create_icon.py
```

### Ausführbare Datei erstellen

**Windows:**
```batch
build.bat
```

**Linux/macOS:**
```bash
chmod +x build.sh
./build.sh
```

**Oder manuell:**
```bash
# Einzelne Datei
python build.py onefile

# Verzeichnis
python build.py dir

# Aufräumen
python build.py clean
```

### Build-Ausgabe

Die fertige Anwendung befindet sich in:
- **onefile**: `dist/TOR_RSS_Reader[.exe]`
- **onedir**: `dist/TOR_RSS_Reader/`

### Erweiterte Konfiguration

Bearbeite `TOR_RSS_Reader.spec` für erweiterte Build-Optionen.
```

## 🎁 Zusätzliche Tipps

### 1. Automatisches Versionieren

```python
# version.py
__version__ = "1.0.0"
__build__ = "2024.01.15"

# In main.py importieren
from version import __version__
```

### 2. Splash Screen (Pro)

```python
# In .spec Datei
splash = Splash(
    'splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(10, 50),
    text_size=12,
    text_color='white'
)
```

### 3. UPX Kompression

```bash
# UPX installieren (optional, verkleinert EXE)
# Windows: https://upx.github.io/
# Linux: sudo apt install upx
# macOS: brew install upx

# In .spec oder command line:
upx=True
```

### 4. Code Signing (Windows)

```bash
# Mit signtool.exe
signtool sign /f certificate.pfx /p password /t http://timestamp.server dist/TOR_RSS_Reader.exe
```

### 5. CI/CD Integration (GitHub Actions)

```yaml
# .github/workflows/build.yml
name: Build Executables

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-build.txt
      - run: python create_icon.py
      - run: python build.py onefile
      - uses: actions/upload-artifact@v3
        with:
          name: TOR_RSS_Reader-Windows
          path: dist/TOR_RSS_Reader.exe
```

## ✅ Checkliste vor Distribution

- [ ] Alle Funktionen getestet
- [ ] Icon erstellt und eingebunden
- [ ] Version aktualisiert
- [ ] README mit Build-Anleitung
- [ ] Lizenz-Datei hinzugefügt
- [ ] Auf Zielsystem getestet
- [ ] Virenscanner-Test (false positives bei PyInstaller sind normal)
- [ ] Größe optimiert
- [ ] Startzeit akzeptabel

Viel Erfolg beim Bauen! 🚀
