"""
Konfigurations-Manager für persistente Einstellungen
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConfigManager:
    """Verwaltet Anwendungskonfiguration"""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config: Dict[str, Any] = self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Standard-Konfiguration"""
        return {
            'database_path': 'measurements.db',
            'plugin_directory': 'plugins',
            'last_sequence_path': '',
            'window_geometry': '1400x900',
            'auto_save': True,
            'measurement_delay': 0.5,
            'max_history': 1000,
            'plot_settings': {
                'theme': 'default',
                'grid': True,
                'legend': True
            },
            'recent_files': []
        }

    def load(self):
        """Lade Konfiguration aus Datei"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                logger.info("Konfiguration geladen")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Konfiguration: {e}")
        else:
            logger.info("Keine Konfigurationsdatei gefunden, verwende Standardwerte")

    def save(self):
        """Speichere Konfiguration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("Konfiguration gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Konfiguration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Hole Konfigurationswert"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Setze Konfigurationswert"""
        self.config[key] = value

    def add_recent_file(self, filepath: str):
        """Füge Datei zu kürzlich verwendeten hinzu"""
        recent = self.config.get('recent_files', [])
        if filepath in recent:
            recent.remove(filepath)
        recent.insert(0, filepath)
        self.config['recent_files'] = recent[:10]  # Maximal 10
