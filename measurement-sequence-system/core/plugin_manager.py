"""
Plugin-Manager für Messgeräte und Prozessierung - VOLLSTÄNDIG
Mit Parameter-Dialog Unterstützung
"""

import importlib
import inspect
import logging
import json
from pathlib import Path
from typing import Dict, List, Type, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PluginBase(ABC):
    """Basis-Klasse für alle Plugins"""

    def __init__(self):
        self.name = self.__class__.__name__
        self.version = "1.0"
        self.description = ""
        self.parameters = {}
        self.is_initialized = False

        # Parameter-Definitionen (für automatische Dialog-Generierung)
        self._parameter_definitions = {}

    @abstractmethod
    def initialize(self):
        """Initialisiere Plugin"""
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup beim Beenden"""
        pass

    def get_info(self) -> Dict:
        """Gibt Plugin-Informationen zurück"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'type': self.get_plugin_type(),
            'has_parameters': len(self._parameter_definitions) > 0,
            'parameter_count': len(self._parameter_definitions)
        }

    @abstractmethod
    def get_plugin_type(self) -> str:
        """Gibt Plugin-Typ zurück"""
        pass

    def get_parameter_definitions(self) -> Dict:
        """
        Gibt Parameter-Definitionen zurück für automatische Dialog-Generierung

        Format:
        {
            'parameter_name': {
                'type': 'float|int|str|bool|choice',
                'default': default_value,
                'min': min_value,  # optional für float/int
                'max': max_value,  # optional für float/int
                'choices': [...],  # für type='choice'
                'description': 'Beschreibung',
                'unit': 'Einheit'  # optional
            }
        }
        """
        return self._parameter_definitions

    def set_parameter_value(self, param_name: str, value: Any):
        """Setze einzelnen Parameter-Wert"""
        self.parameters[param_name] = value
        logger.debug(f"{self.name}: Parameter {param_name} = {value}")

    def get_parameter_value(self, param_name: str, default=None):
        """Hole Parameter-Wert"""
        return self.parameters.get(param_name, default)

    def get_all_parameters(self) -> Dict:
        """Hole alle Parameter"""
        return self.parameters.copy()

    def set_all_parameters(self, parameters: Dict):
        """Setze alle Parameter"""
        self.parameters.update(parameters)

    def save_parameters(self, filepath: str):
        """Speichere Parameter in JSON-Datei"""
        config = {
            'plugin_name': self.name,
            'plugin_version': self.version,
            'parameters': self.parameters
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        logger.info(f"{self.name}: Parameter gespeichert in {filepath}")

    def load_parameters(self, filepath: str):
        """Lade Parameter aus JSON-Datei"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if config.get('plugin_name') == self.name:
                self.parameters.update(config.get('parameters', {}))
                logger.info(f"{self.name}: Parameter geladen aus {filepath}")
                return True
            else:
                logger.warning(f"{self.name}: Plugin-Name stimmt nicht überein")
                return False
        except Exception as e:
            logger.error(f"{self.name}: Fehler beim Laden der Parameter: {e}")
            return False


class MeasurementPlugin(PluginBase):
    """Basis-Klasse für Messgeräte-Plugins"""

    def get_plugin_type(self) -> str:
        return "measurement"

    @abstractmethod
    def set_parameters(self, parameters: Dict):
        """Setze Messparameter"""
        pass

    @abstractmethod
    def measure(self) -> Dict:
        """Führe Messung durch und gib Ergebnisse zurück"""
        pass

    @abstractmethod
    def get_units(self) -> Dict[str, str]:
        """Gibt Einheiten der Messwerte zurück"""
        pass


class ProcessingPlugin(PluginBase):
    """Basis-Klasse für Verarbeitungs-Plugins"""

    def get_plugin_type(self) -> str:
        return "processing"

    @abstractmethod
    def process(self, data: Dict) -> Dict:
        """Verarbeite Daten"""
        pass

    @abstractmethod
    def get_required_inputs(self) -> List[str]:
        """Liste der benötigten Eingabedaten"""
        pass


class PluginManager:
    """Verwaltet alle Plugins"""

    def __init__(self):
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_classes: Dict[str, Type[PluginBase]] = {}
        self.plugin_directory = Path("plugins")
        self.plugin_directory.mkdir(exist_ok=True)

        # Plugin-Konfigurationen
        self.plugin_configs_dir = Path("plugin_configs")
        self.plugin_configs_dir.mkdir(exist_ok=True)

    def load_plugins(self):
        """Lade alle Plugins aus dem Plugin-Verzeichnis"""
        logger.info("Lade Plugins...")

        # Lade Python-Module aus Plugin-Verzeichnis
        for plugin_file in self.plugin_directory.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            try:
                module_name = plugin_file.stem
                spec = importlib.util.spec_from_file_location(
                    f"plugins.{module_name}",
                    plugin_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Finde Plugin-Klassen im Modul
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, PluginBase) and
                        obj not in [PluginBase, MeasurementPlugin, ProcessingPlugin]):
                        self.register_plugin_class(name, obj)
                        logger.info(f"Plugin-Klasse registriert: {name}")

            except Exception as e:
                logger.error(f"Fehler beim Laden von {plugin_file}: {e}")

        logger.info(f"{len(self.plugin_classes)} Plugin-Klassen geladen")

    def register_plugin_class(self, name: str, plugin_class: Type[PluginBase]):
        """Registriere Plugin-Klasse"""
        self.plugin_classes[name] = plugin_class

    def create_plugin_instance(self, name: str) -> PluginBase:
        """Erstelle Plugin-Instanz"""
        if name not in self.plugin_classes:
            raise ValueError(f"Plugin nicht gefunden: {name}")

        plugin = self.plugin_classes[name]()
        self.plugins[name] = plugin

        # Versuche gespeicherte Konfiguration zu laden
        config_file = self.plugin_configs_dir / f"{name}.json"
        if config_file.exists():
            plugin.load_parameters(str(config_file))

        return plugin

    def get_plugin(self, name: str) -> PluginBase:
        """Hole Plugin-Instanz"""
        if name not in self.plugins:
            if name in self.plugin_classes:
                return self.create_plugin_instance(name)
            return None
        return self.plugins[name]

    def get_available_plugins(self) -> Dict[str, Dict]:
        """Liste aller verfügbaren Plugins"""
        available = {}
        for name, plugin_class in self.plugin_classes.items():
            try:
                temp_instance = plugin_class()
                available[name] = temp_instance.get_info()
            except:
                available[name] = {'name': name, 'error': 'Cannot instantiate'}
        return available

    def get_measurement_plugins(self) -> List[str]:
        """Liste aller Messgeräte-Plugins"""
        return [
            name for name, cls in self.plugin_classes.items()
            if issubclass(cls, MeasurementPlugin)
        ]

    def get_processing_plugins(self) -> List[str]:
        """Liste aller Verarbeitungs-Plugins"""
        return [
            name for name, cls in self.plugin_classes.items()
            if issubclass(cls, ProcessingPlugin)
        ]

    def save_plugin_config(self, plugin_name: str):
        """Speichere Plugin-Konfiguration"""
        plugin = self.get_plugin(plugin_name)
        if plugin:
            config_file = self.plugin_configs_dir / f"{plugin_name}.json"
            plugin.save_parameters(str(config_file))

    def cleanup_all(self):
        """Cleanup aller aktiven Plugins"""
        for plugin in self.plugins.values():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Cleanup-Fehler bei {plugin.name}: {e}")
