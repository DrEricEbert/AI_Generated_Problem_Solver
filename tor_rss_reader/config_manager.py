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
