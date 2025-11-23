# Professionelle Messsequenz-Software mit Plugin-System

Ich erstelle für Sie eine umfassende, modulare Lösung. Hier ist die vollständige Software-Architektur:

## 1. Hauptanwendung (main.py)

```python
"""
Messsequenz-Software - Hauptanwendung
Professional Measurement Sequence Management System
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
from pathlib import Path
from gui.main_window import MainWindow
from core.sequence_manager import SequenceManager
from core.plugin_manager import PluginManager
from core.database_manager import DatabaseManager
from core.config_manager import ConfigManager

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('measurement_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class MeasurementApplication:
    """Hauptanwendungsklasse für das Messsystem"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Professionelles Messsequenz-System v1.0")
        self.root.geometry("1400x900")

        # Initialisiere Manager
        self._initialize_managers()

        # Erstelle GUI
        self.main_window = MainWindow(
            self.root,
            self.sequence_manager,
            self.plugin_manager,
            self.database_manager,
            self.config_manager
        )

        # Event-Handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        logger.info("Anwendung erfolgreich gestartet")

    def _initialize_managers(self):
        """Initialisiere alle Manager-Komponenten"""
        try:
            self.config_manager = ConfigManager()
            self.database_manager = DatabaseManager(
                self.config_manager.get('database_path', 'measurements.db')
            )
            self.plugin_manager = PluginManager()
            self.sequence_manager = SequenceManager(
                self.plugin_manager,
                self.database_manager
            )

            # Lade gespeicherte Konfiguration
            self.config_manager.load()

            # Lade Plugins
            self.plugin_manager.load_plugins()

        except Exception as e:
            logger.error(f"Fehler bei der Initialisierung: {e}")
            messagebox.showerror("Fehler", f"Initialisierung fehlgeschlagen: {e}")
            raise

    def on_closing(self):
        """Cleanup beim Schließen der Anwendung"""
        try:
            # Speichere Konfiguration
            self.config_manager.save()

            # Beende laufende Sequenzen
            if self.sequence_manager.is_running():
                response = messagebox.askyesno(
                    "Sequenz läuft",
                    "Eine Messsequenz läuft noch. Trotzdem beenden?"
                )
                if response:
                    self.sequence_manager.stop()
                else:
                    return

            # Cleanup Plugins
            self.plugin_manager.cleanup_all()

            # Schließe Datenbankverbindung
            self.database_manager.close()

            logger.info("Anwendung wird beendet")
            self.root.destroy()

        except Exception as e:
            logger.error(f"Fehler beim Beenden: {e}")
            self.root.destroy()

    def run(self):
        """Starte die Anwendung"""
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = MeasurementApplication()
        app.run()
    except Exception as e:
        logger.critical(f"Kritischer Fehler: {e}", exc_info=True)
        messagebox.showerror("Kritischer Fehler", str(e))
```

## 2. Sequenz-Manager (core/sequence_manager.py)

```python
"""
Sequenz-Manager für Messabläufe
"""

import json
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Callable
import logging

logger = logging.getLogger(__name__)


class MeasurementPoint:
    """Einzelner Messpunkt"""

    def __init__(self, name: str, parameters: Dict[str, Any]):
        self.name = name
        self.parameters = parameters
        self.timestamp = None
        self.results = {}

    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'parameters': self.parameters,
            'timestamp': self.timestamp,
            'results': self.results
        }

    @classmethod
    def from_dict(cls, data: Dict):
        point = cls(data['name'], data['parameters'])
        point.timestamp = data.get('timestamp')
        point.results = data.get('results', {})
        return point


class ParameterRange:
    """Parameterbereich für Messreihen"""

    def __init__(self, parameter_name: str, start: float, end: float,
                 steps: int, unit: str = ""):
        self.parameter_name = parameter_name
        self.start = start
        self.end = end
        self.steps = steps
        self.unit = unit

    def get_values(self) -> List[float]:
        """Generiere Werte im Bereich"""
        if self.steps <= 1:
            return [self.start]
        step_size = (self.end - self.start) / (self.steps - 1)
        return [self.start + i * step_size for i in range(self.steps)]

    def to_dict(self) -> Dict:
        return {
            'parameter_name': self.parameter_name,
            'start': self.start,
            'end': self.end,
            'steps': self.steps,
            'unit': self.unit
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            data['parameter_name'],
            data['start'],
            data['end'],
            data['steps'],
            data.get('unit', '')
        )


class MeasurementSequence:
    """Messsequenz mit Parametern und Messpunkten"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.parameter_ranges: List[ParameterRange] = []
        self.measurement_points: List[MeasurementPoint] = []
        self.active_plugins: List[str] = []
        self.processing_plugins: List[str] = []
        self.metadata = {}

    def add_parameter_range(self, param_range: ParameterRange):
        """Füge Parameterbereich hinzu"""
        self.parameter_ranges.append(param_range)

    def add_measurement_point(self, point: MeasurementPoint):
        """Füge Messpunkt hinzu"""
        self.measurement_points.append(point)

    def generate_measurement_points(self):
        """Generiere Messpunkte aus Parameterbereichen"""
        if not self.parameter_ranges:
            return

        self.measurement_points.clear()

        # Erzeuge kartesisches Produkt aller Parameterbereiche
        import itertools

        ranges_values = [pr.get_values() for pr in self.parameter_ranges]
        range_names = [pr.parameter_name for pr in self.parameter_ranges]

        for i, combination in enumerate(itertools.product(*ranges_values)):
            parameters = dict(zip(range_names, combination))
            point = MeasurementPoint(f"Point_{i+1}", parameters)
            self.measurement_points.append(point)

        logger.info(f"Generierte {len(self.measurement_points)} Messpunkte")

    def to_dict(self) -> Dict:
        """Exportiere als Dictionary"""
        return {
            'name': self.name,
            'description': self.description,
            'parameter_ranges': [pr.to_dict() for pr in self.parameter_ranges],
            'measurement_points': [mp.to_dict() for mp in self.measurement_points],
            'active_plugins': self.active_plugins,
            'processing_plugins': self.processing_plugins,
            'metadata': self.metadata
        }

    def save_to_file(self, filepath: str):
        """Speichere Sequenz als JSON"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Sequenz gespeichert: {filepath}")

    @classmethod
    def from_dict(cls, data: Dict):
        """Lade aus Dictionary"""
        seq = cls(data['name'], data.get('description', ''))
        seq.parameter_ranges = [
            ParameterRange.from_dict(pr) for pr in data.get('parameter_ranges', [])
        ]
        seq.measurement_points = [
            MeasurementPoint.from_dict(mp) for mp in data.get('measurement_points', [])
        ]
        seq.active_plugins = data.get('active_plugins', [])
        seq.processing_plugins = data.get('processing_plugins', [])
        seq.metadata = data.get('metadata', {})
        return seq

    @classmethod
    def load_from_file(cls, filepath: str):
        """Lade Sequenz aus JSON"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Sequenz geladen: {filepath}")
        return cls.from_dict(data)


class SequenceManager:
    """Verwaltet und führt Messsequenzen aus"""

    def __init__(self, plugin_manager, database_manager):
        self.plugin_manager = plugin_manager
        self.database_manager = database_manager
        self.current_sequence: MeasurementSequence = None
        self.is_running_flag = False
        self.is_paused = False
        self.current_point_index = 0
        self.execution_thread = None
        self.callbacks = {
            'on_start': [],
            'on_point_complete': [],
            'on_complete': [],
            'on_error': [],
            'on_progress': []
        }

    def create_sequence(self, name: str, description: str = "") -> MeasurementSequence:
        """Erstelle neue Sequenz"""
        self.current_sequence = MeasurementSequence(name, description)
        return self.current_sequence

    def load_sequence(self, filepath: str):
        """Lade Sequenz aus Datei"""
        self.current_sequence = MeasurementSequence.load_from_file(filepath)
        return self.current_sequence

    def save_sequence(self, filepath: str):
        """Speichere aktuelle Sequenz"""
        if self.current_sequence:
            self.current_sequence.save_to_file(filepath)

    def register_callback(self, event: str, callback: Callable):
        """Registriere Callback für Events"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, *args, **kwargs):
        """Triggere Callbacks"""
        for callback in self.callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback-Fehler ({event}): {e}")

    def start_sequence(self):
        """Starte Sequenzausführung"""
        if not self.current_sequence:
            raise ValueError("Keine Sequenz geladen")

        if self.is_running_flag:
            logger.warning("Sequenz läuft bereits")
            return

        self.is_running_flag = True
        self.is_paused = False
        self.current_point_index = 0

        self.execution_thread = threading.Thread(target=self._execute_sequence)
        self.execution_thread.daemon = True
        self.execution_thread.start()

        logger.info(f"Sequenz gestartet: {self.current_sequence.name}")

    def _execute_sequence(self):
        """Führe Sequenz aus (läuft in separatem Thread)"""
        try:
            self._trigger_callback('on_start', self.current_sequence)

            # Initialisiere Plugins
            for plugin_name in self.current_sequence.active_plugins:
                plugin = self.plugin_manager.get_plugin(plugin_name)
                if plugin:
                    plugin.initialize()

            # Führe Messpunkte aus
            total_points = len(self.current_sequence.measurement_points)

            for idx, point in enumerate(self.current_sequence.measurement_points):
                if not self.is_running_flag:
                    break

                # Pause-Handling
                while self.is_paused and self.is_running_flag:
                    time.sleep(0.1)

                if not self.is_running_flag:
                    break

                self.current_point_index = idx
                self._execute_measurement_point(point)

                # Progress-Callback
                progress = (idx + 1) / total_points * 100
                self._trigger_callback('on_progress', idx + 1, total_points, progress)

            # Cleanup Plugins
            for plugin_name in self.current_sequence.active_plugins:
                plugin = self.plugin_manager.get_plugin(plugin_name)
                if plugin:
                    plugin.cleanup()

            self._trigger_callback('on_complete', self.current_sequence)

        except Exception as e:
            logger.error(f"Fehler bei Sequenzausführung: {e}", exc_info=True)
            self._trigger_callback('on_error', e)
        finally:
            self.is_running_flag = False
            self.is_paused = False

    def _execute_measurement_point(self, point: MeasurementPoint):
        """Führe einzelnen Messpunkt aus"""
        try:
            point.timestamp = datetime.now().isoformat()
            point.results = {}

            logger.info(f"Führe Messpunkt aus: {point.name}")

            # Setze Parameter an Plugins
            for plugin_name in self.current_sequence.active_plugins:
                plugin = self.plugin_manager.get_plugin(plugin_name)
                if plugin and hasattr(plugin, 'set_parameters'):
                    plugin.set_parameters(point.parameters)

            # Warte auf Stabilisierung
            time.sleep(0.5)

            # Führe Messungen durch
            for plugin_name in self.current_sequence.active_plugins:
                plugin = self.plugin_manager.get_plugin(plugin_name)
                if plugin and hasattr(plugin, 'measure'):
                    result = plugin.measure()
                    point.results[plugin_name] = result

            # Verarbeite Daten mit Processing-Plugins
            for proc_plugin_name in self.current_sequence.processing_plugins:
                proc_plugin = self.plugin_manager.get_plugin(proc_plugin_name)
                if proc_plugin and hasattr(proc_plugin, 'process'):
                    processed = proc_plugin.process(point.results)
                    point.results[f"{proc_plugin_name}_processed"] = processed

            # Speichere in Datenbank
            self._save_measurement_to_db(point)

            self._trigger_callback('on_point_complete', point)

        except Exception as e:
            logger.error(f"Fehler bei Messpunkt {point.name}: {e}")
            raise

    def _save_measurement_to_db(self, point: MeasurementPoint):
        """Speichere Messdaten in Datenbank"""
        self.database_manager.save_measurement(
            sequence_name=self.current_sequence.name,
            point_name=point.name,
            timestamp=point.timestamp,
            parameters=point.parameters,
            results=point.results
        )

    def pause(self):
        """Pausiere Sequenz"""
        self.is_paused = True
        logger.info("Sequenz pausiert")

    def resume(self):
        """Setze Sequenz fort"""
        self.is_paused = False
        logger.info("Sequenz fortgesetzt")

    def stop(self):
        """Stoppe Sequenz"""
        self.is_running_flag = False
        self.is_paused = False
        logger.info("Sequenz gestoppt")

    def is_running(self) -> bool:
        """Prüfe ob Sequenz läuft"""
        return self.is_running_flag
```

## 3. Plugin-Manager (core/plugin_manager.py)

```python
"""
Plugin-Manager für Messgeräte und Prozessierung
"""

import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Type
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
            'type': self.get_plugin_type()
        }

    @abstractmethod
    def get_plugin_type(self) -> str:
        """Gibt Plugin-Typ zurück"""
        pass


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

    def cleanup_all(self):
        """Cleanup aller aktiven Plugins"""
        for plugin in self.plugins.values():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Cleanup-Fehler bei {plugin.name}: {e}")
```

## 4. Datenbank-Manager (core/database_manager.py)

```python
"""
Datenbank-Manager für Messergebnisse
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Verwaltet SQLite-Datenbank für Messergebnisse"""

    def __init__(self, db_path: str = "measurements.db"):
        self.db_path = db_path
        self.connection = None
        self._initialize_database()

    def _initialize_database(self):
        """Initialisiere Datenbank und Tabellen"""
        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row

        cursor = self.connection.cursor()

        # Tabelle für Messsequenzen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                metadata TEXT
            )
        """)

        # Tabelle für Messpunkte
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurement_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence_name TEXT NOT NULL,
                point_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                parameters TEXT,
                FOREIGN KEY (sequence_name) REFERENCES sequences(name)
            )
        """)

        # Tabelle für Messwerte
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurement_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                point_id INTEGER NOT NULL,
                parameter_name TEXT NOT NULL,
                value REAL,
                unit TEXT,
                plugin_name TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (point_id) REFERENCES measurement_points(id)
            )
        """)

        # Tabelle für Blob-Daten (z.B. Bilder)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurement_blobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                point_id INTEGER NOT NULL,
                data_type TEXT NOT NULL,
                data BLOB,
                metadata TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (point_id) REFERENCES measurement_points(id)
            )
        """)

        # Indizes für bessere Performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_points_sequence
            ON measurement_points(sequence_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_values_point
            ON measurement_values(point_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON measurement_points(timestamp)
        """)

        self.connection.commit()
        logger.info(f"Datenbank initialisiert: {self.db_path}")

    def save_measurement(self, sequence_name: str, point_name: str,
                        timestamp: str, parameters: Dict, results: Dict):
        """Speichere Messung in Datenbank"""
        cursor = self.connection.cursor()

        try:
            # Speichere Messpunkt
            cursor.execute("""
                INSERT INTO measurement_points
                (sequence_name, point_name, timestamp, parameters)
                VALUES (?, ?, ?, ?)
            """, (
                sequence_name,
                point_name,
                timestamp,
                json.dumps(parameters)
            ))

            point_id = cursor.lastrowid

            # Speichere Messwerte
            for plugin_name, plugin_results in results.items():
                if isinstance(plugin_results, dict):
                    for param_name, value in plugin_results.items():
                        if param_name == 'unit_info':
                            continue

                        unit = ""
                        if 'unit_info' in plugin_results:
                            unit = plugin_results['unit_info'].get(param_name, "")

                        # Unterscheide zwischen numerischen und Blob-Daten
                        if isinstance(value, (int, float)):
                            cursor.execute("""
                                INSERT INTO measurement_values
                                (point_id, parameter_name, value, unit, plugin_name, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (
                                point_id,
                                param_name,
                                float(value),
                                unit,
                                plugin_name,
                                timestamp
                            ))
                        elif isinstance(value, bytes):
                            # Speichere Binärdaten
                            cursor.execute("""
                                INSERT INTO measurement_blobs
                                (point_id, data_type, data, metadata, timestamp)
                                VALUES (?, ?, ?, ?, ?)
                            """, (
                                point_id,
                                param_name,
                                value,
                                json.dumps({'plugin': plugin_name}),
                                timestamp
                            ))

            self.connection.commit()
            logger.debug(f"Messung gespeichert: {point_name}")

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Fehler beim Speichern der Messung: {e}")
            raise

    def get_sequence_data(self, sequence_name: str) -> List[Dict]:
        """Hole alle Daten einer Sequenz"""
        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT mp.id, mp.point_name, mp.timestamp, mp.parameters,
                   mv.parameter_name, mv.value, mv.unit, mv.plugin_name
            FROM measurement_points mp
            LEFT JOIN measurement_values mv ON mp.id = mv.point_id
            WHERE mp.sequence_name = ?
            ORDER BY mp.timestamp, mp.id
        """, (sequence_name,))

        rows = cursor.fetchall()

        # Gruppiere nach Messpunkten
        points = {}
        for row in rows:
            point_id = row['id']
            if point_id not in points:
                points[point_id] = {
                    'point_name': row['point_name'],
                    'timestamp': row['timestamp'],
                    'parameters': json.loads(row['parameters']) if row['parameters'] else {},
                    'values': {}
                }

            if row['parameter_name']:
                plugin_name = row['plugin_name']
                if plugin_name not in points[point_id]['values']:
                    points[point_id]['values'][plugin_name] = {}

                points[point_id]['values'][plugin_name][row['parameter_name']] = {
                    'value': row['value'],
                    'unit': row['unit']
                }

        return list(points.values())

    def get_parameter_history(self, sequence_name: str,
                             parameter_name: str) -> List[Dict]:
        """Hole Verlauf eines Parameters"""
        cursor = self.connection.cursor()

        cursor.execute("""
            SELECT mp.timestamp, mv.value, mv.unit
            FROM measurement_points mp
            JOIN measurement_values mv ON mp.id = mv.point_id
            WHERE mp.sequence_name = ? AND mv.parameter_name = ?
            ORDER BY mp.timestamp
        """, (sequence_name, parameter_name))

        return [dict(row) for row in cursor.fetchall()]

    def get_all_sequences(self) -> List[str]:
        """Liste aller Sequenzen"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT DISTINCT sequence_name
            FROM measurement_points
            ORDER BY sequence_name
        """)
        return [row[0] for row in cursor.fetchall()]

    def delete_sequence(self, sequence_name: str):
        """Lösche Sequenz und alle zugehörigen Daten"""
        cursor = self.connection.cursor()

        try:
            # Hole alle Point-IDs
            cursor.execute("""
                SELECT id FROM measurement_points
                WHERE sequence_name = ?
            """, (sequence_name,))
            point_ids = [row[0] for row in cursor.fetchall()]

            # Lösche Messwerte
            if point_ids:
                placeholders = ','.join('?' * len(point_ids))
                cursor.execute(f"""
                    DELETE FROM measurement_values
                    WHERE point_id IN ({placeholders})
                """, point_ids)

                cursor.execute(f"""
                    DELETE FROM measurement_blobs
                    WHERE point_id IN ({placeholders})
                """, point_ids)

            # Lösche Messpunkte
            cursor.execute("""
                DELETE FROM measurement_points
                WHERE sequence_name = ?
            """, (sequence_name,))

            self.connection.commit()
            logger.info(f"Sequenz gelöscht: {sequence_name}")

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Fehler beim Löschen: {e}")
            raise

    def close(self):
        """Schließe Datenbankverbindung"""
        if self.connection:
            self.connection.close()
            logger.info("Datenbankverbindung geschlossen")
```

## 5. Konfigurations-Manager (core/config_manager.py)

```python
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
```

---

Fortsetzung folgt mit den GUI-Komponenten und Beispiel-Plugins...

## 8. Messsteuerungs-GUI (gui/measurement_control.py)

```python
"""
GUI für Messsteuerung und -überwachung
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class MeasurementControl:
    """Steuerung und Überwachung von Messungen"""

    def __init__(self, parent, sequence_manager):
        self.sequence_manager = sequence_manager
        self.frame = ttk.Frame(parent)

        self._setup_ui()
        self._register_callbacks()

    def _setup_ui(self):
        """Erstelle UI"""
        # Steuerungs-Frame
        control_frame = ttk.LabelFrame(self.frame, text="Steuerung", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Buttons
        button_container = ttk.Frame(control_frame)
        button_container.pack(fill=tk.X)

        self.start_button = ttk.Button(
            button_container,
            text="▶ Start",
            command=self.start_measurement,
            width=15
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = ttk.Button(
            button_container,
            text="⏸ Pause",
            command=self.pause_measurement,
            state=tk.DISABLED,
            width=15
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            button_container,
            text="⏹ Stop",
            command=self.stop_measurement,
            state=tk.DISABLED,
            width=15
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Status-Frame
        status_frame = ttk.LabelFrame(self.frame, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        # Status-Informationen
        info_grid = ttk.Frame(status_frame)
        info_grid.pack(fill=tk.X)

        ttk.Label(info_grid, text="Sequenz:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.sequence_label = ttk.Label(info_grid, text="-", foreground="blue")
        self.sequence_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=10)

        ttk.Label(info_grid, text="Status:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.status_label = ttk.Label(info_grid, text="Bereit", foreground="green")
        self.status_label.grid(row=1, column=1, sticky=tk.W, pady=2, padx=10)

        ttk.Label(info_grid, text="Fortschritt:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.progress_label = ttk.Label(info_grid, text="0 / 0")
        self.progress_label.grid(row=2, column=1, sticky=tk.W, pady=2, padx=10)

        ttk.Label(info_grid, text="Aktueller Punkt:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.current_point_label = ttk.Label(info_grid, text="-")
        self.current_point_label.grid(row=3, column=1, sticky=tk.W, pady=2, padx=10)

        ttk.Label(info_grid, text="Verstrichene Zeit:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.time_label = ttk.Label(info_grid, text="00:00:00")
        self.time_label.grid(row=4, column=1, sticky=tk.W, pady=2, padx=10)

        # Fortschrittsbalken
        self.progress_bar = ttk.Progressbar(
            status_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, pady=10)

        # Log-Frame
        log_frame = ttk.LabelFrame(self.frame, text="Messprotokoll", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Log-Textfeld
        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD)
        log_scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Aktuelle Messwerte
        values_frame = ttk.LabelFrame(self.frame, text="Aktuelle Messwerte", padding=10)
        values_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview für Messwerte
        columns = ('parameter', 'value', 'unit', 'plugin')
        self.values_tree = ttk.Treeview(values_frame, columns=columns, show='headings', height=8)

        self.values_tree.heading('parameter', text='Parameter')
        self.values_tree.heading('value', text='Wert')
        self.values_tree.heading('unit', text='Einheit')
        self.values_tree.heading('plugin', text='Plugin')

        self.values_tree.column('parameter', width=150)
        self.values_tree.column('value', width=100)
        self.values_tree.column('unit', width=80)
        self.values_tree.column('plugin', width=120)

        values_scrollbar = ttk.Scrollbar(values_frame, command=self.values_tree.yview)
        self.values_tree.configure(yscrollcommand=values_scrollbar.set)

        self.values_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        values_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Zeit-Tracking
        self.start_time = None
        self.time_update_job = None

    def _register_callbacks(self):
        """Registriere Callbacks beim SequenceManager"""
        self.sequence_manager.register_callback('on_start', self.on_sequence_start)
        self.sequence_manager.register_callback('on_point_complete', self.on_point_complete)
        self.sequence_manager.register_callback('on_complete', self.on_sequence_complete)
        self.sequence_manager.register_callback('on_error', self.on_error)
        self.sequence_manager.register_callback('on_progress', self.on_progress)

    def start_measurement(self):
        """Starte Messung"""
        if not self.sequence_manager.current_sequence:
            messagebox.showwarning("Warnung", "Keine Sequenz geladen")
            return

        if not self.sequence_manager.current_sequence.measurement_points:
            messagebox.showwarning("Warnung", "Keine Messpunkte definiert")
            return

        if not self.sequence_manager.current_sequence.active_plugins:
            messagebox.showwarning("Warnung", "Keine Plugins ausgewählt")
            return

        try:
            self.sequence_manager.start_sequence()
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.NORMAL)

            self.status_label.config(text="Läuft...", foreground="orange")
            self.log_message("Messung gestartet")

        except Exception as e:
            messagebox.showerror("Fehler", f"Messung konnte nicht gestartet werden:\n{e}")
            logger.error(f"Start-Fehler: {e}")

    def pause_measurement(self):
        """Pausiere/Fortsetzen Messung"""
        if self.sequence_manager.is_paused:
            self.sequence_manager.resume()
            self.pause_button.config(text="⏸ Pause")
            self.status_label.config(text="Läuft...", foreground="orange")
            self.log_message("Messung fortgesetzt")
        else:
            self.sequence_manager.pause()
            self.pause_button.config(text="▶ Fortsetzen")
            self.status_label.config(text="Pausiert", foreground="blue")
            self.log_message("Messung pausiert")

    def stop_measurement(self):
        """Stoppe Messung"""
        response = messagebox.askyesno(
            "Bestätigung",
            "Messung wirklich abbrechen?"
        )
        if response:
            self.sequence_manager.stop()
            self.reset_ui()
            self.log_message("Messung abgebrochen")

    def on_sequence_start(self, sequence):
        """Callback: Sequenz gestartet"""
        self.frame.after(0, lambda: self._update_sequence_start(sequence))

    def _update_sequence_start(self, sequence):
        """UI-Update für Sequenzstart"""
        self.sequence_label.config(text=sequence.name)
        total = len(sequence.measurement_points)
        self.progress_label.config(text=f"0 / {total}")
        self.progress_bar['maximum'] = total
        self.progress_bar['value'] = 0

        self.start_time = datetime.now()
        self.update_elapsed_time()

    def on_point_complete(self, point):
        """Callback: Messpunkt abgeschlossen"""
        self.frame.after(0, lambda: self._update_point_complete(point))

    def _update_point_complete(self, point):
        """UI-Update für Messpunkt"""
        self.current_point_label.config(text=point.name)
        self.log_message(f"Messpunkt abgeschlossen: {point.name}")

        # Zeige Messwerte
        self.display_measurement_values(point.results)

    def on_progress(self, current, total, percentage):
        """Callback: Fortschritt"""
        self.frame.after(0, lambda: self._update_progress(current, total, percentage))

    def _update_progress(self, current, total, percentage):
        """UI-Update für Fortschritt"""
        self.progress_label.config(text=f"{current} / {total}")
        self.progress_bar['value'] = current

    def on_sequence_complete(self, sequence):
        """Callback: Sequenz abgeschlossen"""
        self.frame.after(0, lambda: self._update_sequence_complete(sequence))

    def _update_sequence_complete(self, sequence):
        """UI-Update für Sequenzende"""
        self.status_label.config(text="Abgeschlossen", foreground="green")
        self.log_message(f"Sequenz abgeschlossen: {sequence.name}")
        self.reset_ui()
        messagebox.showinfo("Erfolg", "Messung erfolgreich abgeschlossen!")

    def on_error(self, error):
        """Callback: Fehler aufgetreten"""
        self.frame.after(0, lambda: self._update_error(error))

    def _update_error(self, error):
        """UI-Update für Fehler"""
        self.status_label.config(text="Fehler", foreground="red")
        self.log_message(f"FEHLER: {error}", level="ERROR")
        self.reset_ui()
        messagebox.showerror("Fehler", f"Fehler bei Messung:\n{error}")

    def display_measurement_values(self, results):
        """Zeige aktuelle Messwerte"""
        self.values_tree.delete(*self.values_tree.get_children())

        for plugin_name, plugin_results in results.items():
            if isinstance(plugin_results, dict):
                unit_info = plugin_results.get('unit_info', {})

                for param_name, value in plugin_results.items():
                    if param_name == 'unit_info':
                        continue

                    unit = unit_info.get(param_name, "")

                    if isinstance(value, (int, float)):
                        value_str = f"{value:.4f}"
                    elif isinstance(value, bytes):
                        value_str = f"<Binär: {len(value)} Bytes>"
                    else:
                        value_str = str(value)

                    self.values_tree.insert('', tk.END, values=(
                        param_name,
                        value_str,
                        unit,
                        plugin_name
                    ))

    def log_message(self, message, level="INFO"):
        """Füge Nachricht zum Log hinzu"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"

        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)

        # Farbcodierung
        if level == "ERROR":
            start_idx = self.log_text.index(f"end-{len(log_entry)+1}c")
            end_idx = self.log_text.index("end-1c")
            self.log_text.tag_add("error", start_idx, end_idx)
            self.log_text.tag_config("error", foreground="red")

    def update_elapsed_time(self):
        """Aktualisiere verstrichene Zeit"""
        if self.start_time and self.sequence_manager.is_running():
            elapsed = datetime.now() - self.start_time
            hours, remainder = divmod(elapsed.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.time_label.config(text=time_str)

            # Aktualisiere jede Sekunde
            self.time_update_job = self.frame.after(1000, self.update_elapsed_time)

    def reset_ui(self):
        """Setze UI zurück"""
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED, text="⏸ Pause")
        self.stop_button.config(state=tk.DISABLED)

        if self.time_update_job:
            self.frame.after_cancel(self.time_update_job)
            self.time_update_job = None


```

## 9. Datenvisualisierung (gui/data_visualization.py)

```python
"""
GUI für Datenvisualisierung
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

# Matplotlib-Integration
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib nicht verfügbar - Visualisierung eingeschränkt")

logger = logging.getLogger(__name__)


class DataVisualization:
    """Visualisierung von Messdaten"""

    def __init__(self, parent, database_manager):
        self.database_manager = database_manager
        self.frame = ttk.Frame(parent)

        self.current_sequence = None
        self.current_data = []

        self._setup_ui()

    def _setup_ui(self):
        """Erstelle UI"""
        # Toolbar
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="Sequenz:").pack(side=tk.LEFT, padx=5)

        self.sequence_combo = ttk.Combobox(toolbar, width=30, state='readonly')
        self.sequence_combo.pack(side=tk.LEFT, padx=5)
        self.sequence_combo.bind('<<ComboboxSelected>>', self.on_sequence_selected)

        ttk.Button(
            toolbar,
            text="Aktualisieren",
            command=self.refresh_sequences
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            toolbar,
            text="Plot aktualisieren",
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        # Plot-Optionen
        options_frame = ttk.LabelFrame(self.frame, text="Plot-Optionen", padding=5)
        options_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(options_frame, text="Plot-Typ:").pack(side=tk.LEFT, padx=5)

        self.plot_type = tk.StringVar(value="line")
        ttk.Radiobutton(
            options_frame,
            text="Linie",
            variable=self.plot_type,
            value="line",
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            options_frame,
            text="Scatter",
            variable=self.plot_type,
            value="scatter",
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(
            options_frame,
            text="Bar",
            variable=self.plot_type,
            value="bar",
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Gitter",
            variable=self.grid_var,
            command=self.update_plot
        ).pack(side=tk.LEFT, padx=5)

        # Parameter-Auswahl
        param_frame = ttk.LabelFrame(self.frame, text="Parameter", padding=5)
        param_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(param_frame, text="X-Achse:").grid(row=0, column=0, padx=5, pady=2)
        self.x_param_combo = ttk.Combobox(param_frame, width=25, state='readonly')
        self.x_param_combo.grid(row=0, column=1, padx=5, pady=2)
        self.x_param_combo.bind('<<ComboboxSelected>>', lambda e: self.update_plot())

        ttk.Label(param_frame, text="Y-Achse:").grid(row=1, column=0, padx=5, pady=2)
        self.y_param_combo = ttk.Combobox(param_frame, width=25, state='readonly')
        self.y_param_combo.grid(row=1, column=1, padx=5, pady=2)
        self.y_param_combo.bind('<<ComboboxSelected>>', lambda e: self.update_plot())

        if MATPLOTLIB_AVAILABLE:
            # Matplotlib-Figure
            self.figure = Figure(figsize=(8, 6), dpi=100)
            self.ax = self.figure.add_subplot(111)

            self.canvas = FigureCanvasTkAgg(self.figure, self.frame)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Toolbar
            toolbar_frame = ttk.Frame(self.frame)
            toolbar_frame.pack(fill=tk.X)
            self.mpl_toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
            self.mpl_toolbar.update()
        else:
            # Fallback ohne Matplotlib
            fallback_label = ttk.Label(
                self.frame,
                text="Matplotlib nicht verfügbar.\nBitte installieren Sie matplotlib für Visualisierung.",
                justify=tk.CENTER
            )
            fallback_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Statistik-Frame
        stats_frame = ttk.LabelFrame(self.frame, text="Statistik", padding=5)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_text = tk.Text(stats_frame, height=4, wrap=tk.WORD)
        self.stats_text.pack(fill=tk.X)

        # Lade verfügbare Sequenzen
        self.refresh_sequences()

    def refresh_sequences(self):
        """Aktualisiere Sequenz-Liste"""
        sequences = self.database_manager.get_all_sequences()
        self.sequence_combo['values'] = sequences

        if sequences and not self.current_sequence:
            self.sequence_combo.current(0)
            self.on_sequence_selected(None)

    def on_sequence_selected(self, event):
        """Sequenz wurde ausgewählt"""
        self.current_sequence = self.sequence_combo.get()
        if self.current_sequence:
            self.load_sequence_data()

    def load_sequence_data(self):
        """Lade Daten der ausgewählten Sequenz"""
        try:
            self.current_data = self.database_manager.get_sequence_data(self.current_sequence)
            self.update_parameter_lists()
            self.update_plot()
            logger.info(f"Daten geladen: {self.current_sequence}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Daten:\n{e}")
            logger.error(f"Fehler beim Laden: {e}")

    def update_parameter_lists(self):
        """Aktualisiere Parameter-Listen"""
        if not self.current_data:
            return

        # Sammle alle verfügbaren Parameter
        all_params = set()

        for point in self.current_data:
            # Parameter aus den Eingabeparametern
            all_params.update(point['parameters'].keys())

            # Parameter aus den Messwerten
            for plugin_values in point['values'].values():
                all_params.update(plugin_values.keys())

        params = sorted(list(all_params))

        self.x_param_combo['values'] = params
        self.y_param_combo['values'] = params

        if params:
            if not self.x_param_combo.get():
                self.x_param_combo.current(0)
            if len(params) > 1 and not self.y_param_combo.get():
                self.y_param_combo.current(1)

    def update_plot(self):
        """Aktualisiere Plot"""
        if not MATPLOTLIB_AVAILABLE:
            return

        if not self.current_data:
            return

        x_param = self.x_param_combo.get()
        y_param = self.y_param_combo.get()

        if not x_param or not y_param:
            return

        try:
            # Extrahiere Daten
            x_data = []
            y_data = []

            for point in self.current_data:
                x_val = self._get_parameter_value(point, x_param)
                y_val = self._get_parameter_value(point, y_param)

                if x_val is not None and y_val is not None:
                    x_data.append(x_val)
                    y_data.append(y_val)

            if not x_data or not y_data:
                logger.warning("Keine Daten zum Plotten")
                return

            # Plot erstellen
            self.ax.clear()

            plot_type = self.plot_type.get()

            if plot_type == "line":
                self.ax.plot(x_data, y_data, marker='o', linestyle='-', linewidth=2)
            elif plot_type == "scatter":
                self.ax.scatter(x_data, y_data, s=50, alpha=0.6)
            elif plot_type == "bar":
                self.ax.bar(range(len(x_data)), y_data)
                self.ax.set_xticks(range(len(x_data)))
                self.ax.set_xticklabels([f"{x:.2f}" for x in x_data], rotation=45)

            self.ax.set_xlabel(x_param)
            self.ax.set_ylabel(y_param)
            self.ax.set_title(f"{self.current_sequence}")

            if self.grid_var.get():
                self.ax.grid(True, alpha=0.3)

            self.figure.tight_layout()
            self.canvas.draw()

            # Statistik berechnen
            self.update_statistics(y_data, y_param)

        except Exception as e:
            logger.error(f"Plot-Fehler: {e}")
            messagebox.showerror("Fehler", f"Fehler beim Plotten:\n{e}")

    def _get_parameter_value(self, point, param_name):
        """Hole Parameterwert aus Datenpunkt"""
        # Prüfe Eingabeparameter
        if param_name in point['parameters']:
            return point['parameters'][param_name]

        # Prüfe Messwerte
        for plugin_values in point['values'].values():
            if param_name in plugin_values:
                return plugin_values[param_name]['value']

        return None

    def update_statistics(self, data, param_name):
        """Aktualisiere Statistik-Anzeige"""
        if not data:
            return

        if MATPLOTLIB_AVAILABLE:
            data_array = np.array(data)

            stats = f"Parameter: {param_name}\n"
            stats += f"Anzahl: {len(data)}  |  "
            stats += f"Mittelwert: {np.mean(data_array):.4f}  |  "
            stats += f"Std.abw.: {np.std(data_array):.4f}\n"
            stats += f"Min: {np.min(data_array):.4f}  |  "
            stats += f"Max: {np.max(data_array):.4f}  |  "
            stats += f"Median: {np.median(data_array):.4f}"
        else:
            stats = f"Parameter: {param_name}\n"
            stats += f"Anzahl: {len(data)}  |  "
            stats += f"Min: {min(data):.4f}  |  "
            stats += f"Max: {max(data):.4f}"

        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert('1.0', stats)
```

## 10. Plugin-Manager GUI (gui/plugin_manager_gui.py)

```python
"""
GUI für Plugin-Verwaltung
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

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
            text="Plugin testen",
            command=self.test_plugin
        ).pack(side=tk.LEFT, padx=2)

        # Plugin-Liste
        list_frame = ttk.LabelFrame(self.frame, text="Verfügbare Plugins", padding=5)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('name', 'type', 'version', 'description')
        self.plugin_tree = ttk.Treeview(list_frame, columns=columns, show='headings')

        self.plugin_tree.heading('name', text='Name')
        self.plugin_tree.heading('type', text='Typ')
        self.plugin_tree.heading('version', text='Version')
        self.plugin_tree.heading('description', text='Beschreibung')

        self.plugin_tree.column('name', width=150)
        self.plugin_tree.column('type', width=100)
        self.plugin_tree.column('version', width=80)
        self.plugin_tree.column('description', width=300)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.plugin_tree.yview)
        self.plugin_tree.configure(yscrollcommand=scrollbar.set)

        self.plugin_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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

            # Typ-Übersetzung
            type_map = {
                'measurement': 'Messgerät',
                'processing': 'Verarbeitung',
                'unknown': 'Unbekannt'
            }
            type_text = type_map.get(plugin_type, plugin_type)

            self.plugin_tree.insert('', tk.END, values=(
                name,
                type_text,
                version,
                description
            ))

        self.stats_label.config(text=f"Plugins geladen: {len(plugins)}")

    def show_plugin_info(self):
        """Zeige detaillierte Plugin-Info"""
        selection = self.plugin_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Bitte Plugin auswählen")
            return

        item = self.plugin_tree.item(selection[0])
        plugin_name = item['values'][0]

        plugins = self.plugin_manager.get_available_plugins()
        info = plugins.get(plugin_name, {})

        info_text = f"Plugin: {plugin_name}\n\n"
        info_text += f"Typ: {info.get('type', '-')}\n"
        info_text += f"Version: {info.get('version', '-')}\n"
        info_text += f"Beschreibung: {info.get('description', '-')}\n"

        messagebox.showinfo(f"Plugin-Info: {plugin_name}", info_text)

    def test_plugin(self):
        """Teste Plugin"""
        selection = self.plugin_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Bitte Plugin auswählen")
            return

        item = self.plugin_tree.item(selection[0])
        plugin_name = item['values'][0]

        try:
            plugin = self.plugin_manager.get_plugin(plugin_name)

            if plugin:
                plugin.initialize()
                messagebox.showinfo("Erfolg", f"Plugin {plugin_name} erfolgreich initialisiert")
                plugin.cleanup()
            else:
                messagebox.showerror("Fehler", f"Plugin {plugin_name} konnte nicht geladen werden")

        except Exception as e:
            messagebox.showerror("Fehler", f"Plugin-Test fehlgeschlagen:\n{e}")
            logger.error(f"Plugin-Test Fehler: {e}")
```

## 11. Datenbank-Browser (gui/database_browser.py)

```python
"""
GUI für Datenbank-Browser
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
import json
import csv
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseBrowser:
    """Browser für Messdatenbank"""

    def __init__(self, parent, database_manager):
        self.database_manager = database_manager
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
            text="Exportieren",
            command=self.export_data
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            toolbar,
            text="Löschen",
            command=self.delete_sequence
        ).pack(side=tk.LEFT, padx=2)

        # Sequenz-Auswahl
        select_frame = ttk.Frame(self.frame)
        select_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(select_frame, text="Sequenz:").pack(side=tk.LEFT, padx=5)

        self.sequence_combo = ttk.Combobox(select_frame, width=30, state='readonly')
        self.sequence_combo.pack(side=tk.LEFT, padx=5)
        self.sequence_combo.bind('<<ComboboxSelected>>', self.on_sequence_selected)

        # Daten-Treeview
        data_frame = ttk.LabelFrame(self.frame, text="Messdaten", padding=5)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('timestamp', 'point', 'parameter', 'value', 'unit')
        self.data_tree = ttk.Treeview(data_frame, columns=columns, show='headings')

        self.data_tree.heading('timestamp', text='Zeitstempel')
        self.data_tree.heading('point', text='Messpunkt')
        self.data_tree.heading('parameter', text='Parameter')
        self.data_tree.heading('value', text='Wert')
        self.data_tree.heading('unit', text='Einheit')

        self.data_tree.column('timestamp', width=150)
        self.data_tree.column('point', width=120)
        self.data_tree.column('parameter', width=150)
        self.data_tree.column('value', width=100)
        self.data_tree.column('unit', width=80)

        scrollbar_y = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        scrollbar_x = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.data_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar_y.grid(row=0, column=1, sticky='ns')
        scrollbar_x.grid(row=1, column=0, sticky='ew')

        data_frame.rowconfigure(0, weight=1)
        data_frame.columnconfigure(0, weight=1)

        # Statistik
        stats_frame = ttk.Frame(self.frame)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)

        self.stats_label = ttk.Label(stats_frame, text="Keine Daten")
        self.stats_label.pack(side=tk.LEFT)

    def refresh(self):
        """Aktualisiere Sequenz-Liste"""
        sequences = self.database_manager.get_all_sequences()
        self.sequence_combo['values'] = sequences

        if sequences:
            self.sequence_combo.current(0)
            self.on_sequence_selected(None)

        self.stats_label.config(text=f"Sequenzen in Datenbank: {len(sequences)}")

    def on_sequence_selected(self, event):
        """Sequenz wurde ausgewählt"""
        sequence_name = self.sequence_combo.get()
        if sequence_name:
            self.load_sequence_data(sequence_name)

    def load_sequence_data(self, sequence_name):
        """Lade Sequenzdaten"""
        try:
            self.data_tree.delete(*self.data_tree.get_children())

            data = self.database_manager.get_sequence_data(sequence_name)

            total_values = 0
            for point in data:
                timestamp = point['timestamp']
                point_name = point['point_name']

                for plugin_name, plugin_values in point['values'].items():
                    for param_name, param_data in plugin_values.items():
                        value = param_data.get('value', '-')
                        unit = param_data.get('unit', '')

                        self.data_tree.insert('', tk.END, values=(
                            timestamp,
                            point_name,
                            f"{plugin_name}.{param_name}",
                            f"{value:.4f}" if isinstance(value, float) else value,
                            unit
                        ))
                        total_values += 1

            self.stats_label.config(
                text=f"Sequenz: {sequence_name} | Messpunkte: {len(data)} | Messwerte: {total_values}"
            )

        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden:\n{e}")
            logger.error(f"Fehler beim Laden: {e}")

    def export_data(self):
        """Exportiere Daten als CSV"""
        sequence_name = self.sequence_combo.get()
        if not sequence_name:
            messagebox.showinfo("Info", "Bitte Sequenz auswählen")
            return

        filepath = filedialog.asksaveasfilename(
            title="Daten exportieren",
            defaultextension=".csv",
            filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")]
        )

        if not filepath:
            return

        try:
            data = self.database_manager.get_sequence_data(sequence_name)

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Zeitstempel', 'Messpunkt', 'Parameter', 'Wert', 'Einheit'])

                for point in data:
                    timestamp = point['timestamp']
                    point_name = point['point_name']

                    for plugin_name, plugin_values in point['values'].items():
                        for param_name, param_data in plugin_values.items():
                            value = param_data.get('value', '')
                            unit = param_data.get('unit', '')

                            writer.writerow([
                                timestamp,
                                point_name,
                                f"{plugin_name}.{param_name}",
                                value,
                                unit
                            ])

            messagebox.showinfo("Erfolg", f"Daten exportiert nach:\n{filepath}")

        except Exception as e:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen:\n{e}")
            logger.error(f"Export-Fehler: {e}")

    def delete_sequence(self):
        """Lösche Sequenz aus Datenbank"""
        sequence_name = self.sequence_combo.get()
        if not sequence_name:
            messagebox.showinfo("Info", "Bitte Sequenz auswählen")
            return

        response = messagebox.askyesno(
            "Bestätigung",
            f"Sequenz '{sequence_name}' wirklich löschen?\nAlle Messdaten gehen verloren!"
        )

        if response:
            try:
                self.database_manager.delete_sequence(sequence_name)
                self.refresh()
                messagebox.showinfo("Erfolg", "Sequenz gelöscht")
            except Exception as e:
                messagebox.showerror("Fehler", f"Löschen fehlgeschlagen:\n{e}")
                logger.error(f"Lösch-Fehler: {e}")
```

Fortsetzung mit Beispiel-Plugins folgt...

## 12. Beispiel-Plugins

### 12.1 Temperatur-Messgerät (plugins/temperature_sensor.py)

```python
"""
Beispiel-Plugin: Temperatur-Sensor
Simuliert einen Temperatursensor
"""

import random
import time
import logging
from core.plugin_manager import MeasurementPlugin

logger = logging.getLogger(__name__)


class TemperatureSensor(MeasurementPlugin):
    """Simulated Temperature Sensor Plugin"""

    def __init__(self):
        super().__init__()
        self.name = "TemperatureSensor"
        self.version = "1.0"
        self.description = "Simulierter Temperatursensor mit PT100-Charakteristik"

        self.current_temperature = 25.0
        self.target_temperature = 25.0
        self.noise_level = 0.1

        # Simulierte Hardware-Verbindung
        self.connected = False

    def initialize(self):
        """Initialisiere Sensor"""
        try:
            logger.info(f"{self.name}: Initialisierung gestartet")

            # Simuliere Verbindungsaufbau
            time.sleep(0.2)
            self.connected = True
            self.is_initialized = True

            logger.info(f"{self.name}: Erfolgreich initialisiert")
            return True

        except Exception as e:
            logger.error(f"{self.name}: Initialisierung fehlgeschlagen: {e}")
            return False

    def cleanup(self):
        """Cleanup"""
        logger.info(f"{self.name}: Cleanup")
        self.connected = False
        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        """Setze Parameter (z.B. Soll-Temperatur)"""
        if 'temperature' in parameters:
            self.target_temperature = parameters['temperature']
            logger.info(f"{self.name}: Zieltemperatur gesetzt auf {self.target_temperature}°C")

        if 'setpoint' in parameters:
            self.target_temperature = parameters['setpoint']
            logger.info(f"{self.name}: Zieltemperatur gesetzt auf {self.target_temperature}°C")

        # Simuliere Aufheiz-/Abkühlzeit
        self._simulate_temperature_change()

    def _simulate_temperature_change(self):
        """Simuliere Temperaturänderung"""
        # Einfache exponentielle Annäherung
        diff = self.target_temperature - self.current_temperature
        self.current_temperature += diff * 0.3  # 30% Annäherung pro Schritt

        # Simuliere Settling-Time
        time.sleep(0.1)

    def measure(self) -> dict:
        """Führe Temperaturmessung durch"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Sensor nicht initialisiert")

        # Simuliere Messung mit Rauschen
        noise = random.gauss(0, self.noise_level)
        measured_temp = self.current_temperature + noise

        # Simuliere PT100-Widerstand (R = R0 * (1 + A*T + B*T²))
        # Vereinfachte Formel: R ≈ 100Ω + 0.385Ω/°C * T
        resistance = 100.0 + 0.385 * measured_temp
        resistance += random.gauss(0, 0.01)  # Widerstandsrauschen

        # Simuliere Messverzögerung
        time.sleep(0.05)

        result = {
            'temperature': round(measured_temp, 2),
            'resistance': round(resistance, 3),
            'target_temperature': self.target_temperature,
            'unit_info': {
                'temperature': '°C',
                'resistance': 'Ω',
                'target_temperature': '°C'
            }
        }

        logger.debug(f"{self.name}: Messung: {measured_temp:.2f}°C")
        return result

    def get_units(self) -> dict:
        """Gibt Einheiten zurück"""
        return {
            'temperature': '°C',
            'resistance': 'Ω',
            'target_temperature': '°C'
        }


class TemperatureSensorDual(MeasurementPlugin):
    """Dual-Channel Temperature Sensor"""

    def __init__(self):
        super().__init__()
        self.name = "TemperatureSensorDual"
        self.version = "1.0"
        self.description = "Simulierter Dual-Kanal Temperatursensor"

        self.channel1_temp = 25.0
        self.channel2_temp = 25.0
        self.connected = False

    def initialize(self):
        """Initialisiere Sensor"""
        logger.info(f"{self.name}: Initialisierung")
        time.sleep(0.2)
        self.connected = True
        self.is_initialized = True
        return True

    def cleanup(self):
        """Cleanup"""
        self.connected = False
        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        """Setze Parameter"""
        if 'temp_ch1' in parameters:
            self.channel1_temp = parameters['temp_ch1']
        if 'temp_ch2' in parameters:
            self.channel2_temp = parameters['temp_ch2']

    def measure(self) -> dict:
        """Messung beider Kanäle"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Sensor nicht initialisiert")

        temp1 = self.channel1_temp + random.gauss(0, 0.1)
        temp2 = self.channel2_temp + random.gauss(0, 0.1)

        time.sleep(0.05)

        return {
            'channel1_temperature': round(temp1, 2),
            'channel2_temperature': round(temp2, 2),
            'temperature_difference': round(temp1 - temp2, 2),
            'unit_info': {
                'channel1_temperature': '°C',
                'channel2_temperature': '°C',
                'temperature_difference': 'K'
            }
        }

    def get_units(self) -> dict:
        return {
            'channel1_temperature': '°C',
            'channel2_temperature': '°C',
            'temperature_difference': 'K'
        }
```

### 12.2 Elektrisches Messgerät (plugins/electrical_meter.py)

```python
"""
Beispiel-Plugin: Elektrisches Messgerät
Simuliert Multimeter für Spannung, Strom, Leistung, Widerstand
"""

import random
import time
import logging
import math
from core.plugin_manager import MeasurementPlugin

logger = logging.getLogger(__name__)


class ElectricalMeter(MeasurementPlugin):
    """Simuliertes elektrisches Messgerät"""

    def __init__(self):
        super().__init__()
        self.name = "ElectricalMeter"
        self.version = "1.0"
        self.description = "Simuliertes Multimeter für elektrische Messungen"

        self.voltage = 0.0
        self.current = 0.0
        self.resistance = 1000.0

        self.connected = False

    def initialize(self):
        """Initialisiere Messgerät"""
        try:
            logger.info(f"{self.name}: Initialisierung gestartet")
            time.sleep(0.3)
            self.connected = True
            self.is_initialized = True
            logger.info(f"{self.name}: Erfolgreich initialisiert")
            return True
        except Exception as e:
            logger.error(f"{self.name}: Initialisierung fehlgeschlagen: {e}")
            return False

    def cleanup(self):
        """Cleanup"""
        logger.info(f"{self.name}: Cleanup")
        self.connected = False
        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        """Setze Parameter"""
        if 'voltage' in parameters:
            self.voltage = parameters['voltage']
            logger.info(f"{self.name}: Spannung gesetzt auf {self.voltage}V")

        if 'current' in parameters:
            self.current = parameters['current']
            logger.info(f"{self.name}: Strom gesetzt auf {self.current}A")

        if 'resistance' in parameters:
            self.resistance = parameters['resistance']
            logger.info(f"{self.name}: Widerstand gesetzt auf {self.resistance}Ω")

        # Simuliere Einstellzeit
        time.sleep(0.05)

    def measure(self) -> dict:
        """Führe elektrische Messung durch"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Messgerät nicht initialisiert")

        # Simuliere Messung mit Rauschen
        noise_v = random.gauss(0, 0.001)  # 1mV Rauschen
        noise_i = random.gauss(0, 0.0001)  # 0.1mA Rauschen

        measured_voltage = self.voltage + noise_v
        measured_current = self.current + noise_i

        # Berechne Leistung: P = U * I
        power = measured_voltage * measured_current

        # Berechne Widerstand: R = U / I (wenn Strom > 0)
        if abs(measured_current) > 0.001:
            calculated_resistance = measured_voltage / measured_current
        else:
            calculated_resistance = self.resistance + random.gauss(0, 1)

        # Simuliere Messverzögerung
        time.sleep(0.08)

        result = {
            'voltage': round(measured_voltage, 4),
            'current': round(measured_current, 5),
            'power': round(power, 5),
            'resistance': round(calculated_resistance, 2),
            'unit_info': {
                'voltage': 'V',
                'current': 'A',
                'power': 'W',
                'resistance': 'Ω'
            }
        }

        logger.debug(f"{self.name}: U={measured_voltage:.3f}V, I={measured_current:.4f}A, P={power:.4f}W")
        return result

    def get_units(self) -> dict:
        return {
            'voltage': 'V',
            'current': 'A',
            'power': 'W',
            'resistance': 'Ω'
        }


class PowerSupply(MeasurementPlugin):
    """Simulierte programmierbare Spannungsquelle"""

    def __init__(self):
        super().__init__()
        self.name = "PowerSupply"
        self.version = "1.0"
        self.description = "Programmierbare Spannungsquelle mit Strombegrenzung"

        self.set_voltage = 0.0
        self.set_current_limit = 1.0
        self.output_enabled = False

        self.actual_voltage = 0.0
        self.actual_current = 0.0
        self.connected = False

    def initialize(self):
        """Initialisiere Spannungsquelle"""
        logger.info(f"{self.name}: Initialisierung")
        time.sleep(0.2)
        self.connected = True
        self.is_initialized = True
        self.output_enabled = False
        return True

    def cleanup(self):
        """Cleanup - Ausgang ausschalten"""
        logger.info(f"{self.name}: Cleanup - Ausgang wird ausgeschaltet")
        self.output_enabled = False
        self.set_voltage = 0.0
        self.connected = False
        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        """Setze Parameter"""
        if 'voltage' in parameters:
            self.set_voltage = max(0, min(30, parameters['voltage']))  # Limit 0-30V
            logger.info(f"{self.name}: Ausgangsspannung gesetzt auf {self.set_voltage}V")

        if 'current_limit' in parameters:
            self.set_current_limit = max(0, min(3, parameters['current_limit']))  # Limit 0-3A
            logger.info(f"{self.name}: Strombegrenzung gesetzt auf {self.set_current_limit}A")

        if 'output_enable' in parameters:
            self.output_enabled = bool(parameters['output_enable'])
            logger.info(f"{self.name}: Ausgang {'aktiviert' if self.output_enabled else 'deaktiviert'}")

        # Simuliere Einstellzeit
        time.sleep(0.1)

        # Simuliere Spannungsrampe
        if self.output_enabled:
            self.actual_voltage = self.set_voltage * 0.9 + random.gauss(0, 0.01)
            # Simuliere Last-abhängigen Strom
            self.actual_current = self.actual_voltage / 10.0 + random.gauss(0, 0.001)
            self.actual_current = min(self.actual_current, self.set_current_limit)
        else:
            self.actual_voltage = 0.0
            self.actual_current = 0.0

    def measure(self) -> dict:
        """Messe Ausgangswerte"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Spannungsquelle nicht initialisiert")

        # Simuliere kleine Schwankungen
        voltage = self.actual_voltage + random.gauss(0, 0.005)
        current = self.actual_current + random.gauss(0, 0.0005)

        # Berechne Leistung
        power = voltage * current

        # Status-Flags
        cv_mode = abs(voltage - self.set_voltage) < 0.1  # Constant Voltage
        cc_mode = abs(current - self.set_current_limit) < 0.01  # Constant Current

        time.sleep(0.05)

        return {
            'output_voltage': round(voltage, 4),
            'output_current': round(current, 5),
            'output_power': round(power, 5),
            'set_voltage': self.set_voltage,
            'current_limit': self.set_current_limit,
            'cv_mode': 1 if cv_mode else 0,
            'cc_mode': 1 if cc_mode else 0,
            'output_enabled': 1 if self.output_enabled else 0,
            'unit_info': {
                'output_voltage': 'V',
                'output_current': 'A',
                'output_power': 'W',
                'set_voltage': 'V',
                'current_limit': 'A',
                'cv_mode': '',
                'cc_mode': '',
                'output_enabled': ''
            }
        }

    def get_units(self) -> dict:
        return {
            'output_voltage': 'V',
            'output_current': 'A',
            'output_power': 'W',
            'set_voltage': 'V',
            'current_limit': 'A'
        }
```

### 12.3 Kamera-Plugin (plugins/camera_plugin.py)

```python
"""
Beispiel-Plugin: Kamera
Simuliert Kamera für Bildaufnahme
"""

import random
import time
import logging
import io
from core.plugin_manager import MeasurementPlugin

logger = logging.getLogger(__name__)

# Optionale PIL/Pillow für Bildverarbeitung
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow nicht verfügbar - Kamera-Plugin eingeschränkt")


class CameraPlugin(MeasurementPlugin):
    """Simulierte Kamera für Bildaufnahme"""

    def __init__(self):
        super().__init__()
        self.name = "CameraPlugin"
        self.version = "1.0"
        self.description = "Simulierte Kamera für Bildaufnahme und -analyse"

        self.resolution = (640, 480)
        self.exposure_time = 100  # ms
        self.gain = 1.0

        self.connected = False

    def initialize(self):
        """Initialisiere Kamera"""
        try:
            logger.info(f"{self.name}: Initialisierung gestartet")

            if not PIL_AVAILABLE:
                logger.warning(f"{self.name}: PIL nicht verfügbar - Bildgenerierung eingeschränkt")

            time.sleep(0.3)
            self.connected = True
            self.is_initialized = True

            logger.info(f"{self.name}: Erfolgreich initialisiert")
            return True

        except Exception as e:
            logger.error(f"{self.name}: Initialisierung fehlgeschlagen: {e}")
            return False

    def cleanup(self):
        """Cleanup"""
        logger.info(f"{self.name}: Cleanup")
        self.connected = False
        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        """Setze Kamera-Parameter"""
        if 'exposure' in parameters:
            self.exposure_time = max(1, min(1000, parameters['exposure']))
            logger.info(f"{self.name}: Belichtungszeit gesetzt auf {self.exposure_time}ms")

        if 'gain' in parameters:
            self.gain = max(0.1, min(10.0, parameters['gain']))
            logger.info(f"{self.name}: Verstärkung gesetzt auf {self.gain}")

        if 'resolution' in parameters:
            res = parameters['resolution']
            if isinstance(res, (list, tuple)) and len(res) == 2:
                self.resolution = tuple(res)
                logger.info(f"{self.name}: Auflösung gesetzt auf {self.resolution}")

    def measure(self) -> dict:
        """Führe Bildaufnahme durch"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Kamera nicht initialisiert")

        # Simuliere Belichtungszeit
        time.sleep(self.exposure_time / 1000.0)

        # Generiere Testbild
        image_data = self._generate_test_image()

        # Analysiere Bild
        analysis = self._analyze_image(image_data)

        result = {
            'image': image_data,
            'mean_intensity': analysis['mean_intensity'],
            'std_intensity': analysis['std_intensity'],
            'width': self.resolution[0],
            'height': self.resolution[1],
            'exposure_time': self.exposure_time,
            'gain': self.gain,
            'unit_info': {
                'mean_intensity': '',
                'std_intensity': '',
                'width': 'px',
                'height': 'px',
                'exposure_time': 'ms',
                'gain': ''
            }
        }

        logger.debug(f"{self.name}: Bild aufgenommen ({self.resolution[0]}x{self.resolution[1]})")
        return result

    def _generate_test_image(self):
        """Generiere Testbild"""
        if PIL_AVAILABLE:
            # Erstelle Testbild mit PIL
            img = Image.new('RGB', self.resolution, color=(128, 128, 128))
            draw = ImageDraw.Draw(img)

            # Zeichne Testmuster
            # Gradient
            for y in range(self.resolution[1]):
                intensity = int(255 * y / self.resolution[1])
                draw.line([(0, y), (self.resolution[0]//3, y)],
                         fill=(intensity, intensity, intensity))

            # Rechtecke
            draw.rectangle([50, 50, 150, 150], outline=(255, 0, 0), width=3)
            draw.rectangle([200, 100, 300, 200], outline=(0, 255, 0), width=3)

            # Text
            try:
                draw.text((10, 10), f"Exp: {self.exposure_time}ms", fill=(255, 255, 0))
            except:
                pass  # Font nicht verfügbar

            # Konvertiere zu Bytes
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return buf.getvalue()
        else:
            # Fallback: Dummy-Daten
            return b'SIMULATED_IMAGE_DATA'

    def _analyze_image(self, image_data):
        """Analysiere Bild"""
        if PIL_AVAILABLE and len(image_data) > 100:
            try:
                img = Image.open(io.BytesIO(image_data))

                # Konvertiere zu Graustufen
                gray = img.convert('L')
                pixels = list(gray.getdata())

                # Berechne Statistiken
                mean = sum(pixels) / len(pixels)
                variance = sum((x - mean) ** 2 for x in pixels) / len(pixels)
                std = variance ** 0.5

                return {
                    'mean_intensity': round(mean, 2),
                    'std_intensity': round(std, 2)
                }
            except:
                pass

        # Fallback
        return {
            'mean_intensity': 128.0 + random.gauss(0, 5),
            'std_intensity': 30.0 + random.gauss(0, 2)
        }

    def get_units(self) -> dict:
        return {
            'mean_intensity': '',
            'std_intensity': '',
            'width': 'px',
            'height': 'px',
            'exposure_time': 'ms',
            'gain': ''
        }
```

### 12.4 Statistik-Verarbeitungs-Plugin (plugins/statistics_processor.py)

```python
"""
Beispiel-Plugin: Statistik-Verarbeitung
Berechnet statistische Kennwerte aus Messdaten
"""

import logging
import math
from core.plugin_manager import ProcessingPlugin

logger = logging.getLogger(__name__)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy nicht verfügbar - Statistik eingeschränkt")


class StatisticsProcessor(ProcessingPlugin):
    """Statistik-Verarbeitungs-Plugin"""

    def __init__(self):
        super().__init__()
        self.name = "StatisticsProcessor"
        self.version = "1.0"
        self.description = "Berechnet statistische Kennwerte aus Messdaten"

        self.history = {}  # Speichert Verlauf für gleitende Statistiken
        self.window_size = 10

    def initialize(self):
        """Initialisiere Prozessor"""
        logger.info(f"{self.name}: Initialisierung")
        self.history.clear()
        self.is_initialized = True
        return True

    def cleanup(self):
        """Cleanup"""
        logger.info(f"{self.name}: Cleanup")
        self.history.clear()
        self.is_initialized = False

    def get_required_inputs(self) -> list:
        """Benötigte Eingaben"""
        return ['numerical_values']  # Beliebige numerische Werte

    def process(self, data: dict) -> dict:
        """Verarbeite Daten und berechne Statistiken"""
        if not self.is_initialized:
            self.initialize()

        result = {}

        # Sammle alle numerischen Werte
        numerical_values = self._extract_numerical_values(data)

        if not numerical_values:
            logger.warning(f"{self.name}: Keine numerischen Werte gefunden")
            return result

        # Berechne Basis-Statistiken
        if NUMPY_AVAILABLE:
            values_array = np.array(numerical_values)
            result['mean'] = float(np.mean(values_array))
            result['std'] = float(np.std(values_array))
            result['min'] = float(np.min(values_array))
            result['max'] = float(np.max(values_array))
            result['median'] = float(np.median(values_array))
            result['variance'] = float(np.var(values_array))

            # Percentile
            result['p25'] = float(np.percentile(values_array, 25))
            result['p75'] = float(np.percentile(values_array, 75))

        else:
            # Fallback ohne NumPy
            result['mean'] = sum(numerical_values) / len(numerical_values)
            result['min'] = min(numerical_values)
            result['max'] = max(numerical_values)

            # Standardabweichung
            mean = result['mean']
            variance = sum((x - mean) ** 2 for x in numerical_values) / len(numerical_values)
            result['std'] = math.sqrt(variance)
            result['variance'] = variance

            # Median
            sorted_values = sorted(numerical_values)
            n = len(sorted_values)
            if n % 2 == 0:
                result['median'] = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
            else:
                result['median'] = sorted_values[n//2]

        # Zusätzliche Kennwerte
        result['count'] = len(numerical_values)
        result['range'] = result['max'] - result['min']
        result['coefficient_of_variation'] = (result['std'] / result['mean'] * 100) if result['mean'] != 0 else 0

        # Aktualisiere Historie für gleitende Statistiken
        self._update_history('values', numerical_values)

        # Gleitender Durchschnitt
        if 'values' in self.history:
            recent_values = self.history['values'][-self.window_size:]
            result['moving_average'] = sum(recent_values) / len(recent_values)

        # Runde Ergebnisse
        for key in result:
            if isinstance(result[key], float):
                result[key] = round(result[key], 4)

        logger.debug(f"{self.name}: Statistiken berechnet für {len(numerical_values)} Werte")
        return result

    def _extract_numerical_values(self, data: dict) -> list:
        """Extrahiere alle numerischen Werte aus verschachtelten Daten"""
        values = []

        for key, value in data.items():
            if isinstance(value, dict):
                # Rekursiv in verschachtelten Dicts suchen
                for sub_key, sub_value in value.items():
                    if sub_key == 'unit_info':
                        continue
                    if isinstance(sub_value, (int, float)) and not isinstance(sub_value, bool):
                        values.append(float(sub_value))
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                values.append(float(value))

        return values

    def _update_history(self, key: str, values: list):
        """Aktualisiere Verlaufs-Historie"""
        if key not in self.history:
            self.history[key] = []

        self.history[key].extend(values)

        # Begrenze Historie-Größe
        max_history = 1000
        if len(self.history[key]) > max_history:
            self.history[key] = self.history[key][-max_history:]


class TrendAnalyzer(ProcessingPlugin):
    """Trend-Analyse für Zeitreihen"""

    def __init__(self):
        super().__init__()
        self.name = "TrendAnalyzer"
        self.version = "1.0"
        self.description = "Analysiert Trends in Messdaten"

        self.data_history = []

    def initialize(self):
        """Initialisiere"""
        logger.info(f"{self.name}: Initialisierung")
        self.data_history.clear()
        self.is_initialized = True
        return True

    def cleanup(self):
        """Cleanup"""
        self.data_history.clear()
        self.is_initialized = False

    def get_required_inputs(self) -> list:
        return ['numerical_values']

    def process(self, data: dict) -> dict:
        """Analysiere Trends"""
        # Extrahiere ersten numerischen Wert als Hauptwert
        numerical_values = self._extract_numerical_values(data)

        if not numerical_values:
            return {}

        current_value = numerical_values[0]
        self.data_history.append(current_value)

        # Begrenze Historie
        if len(self.data_history) > 100:
            self.data_history = self.data_history[-100:]

        result = {}

        if len(self.data_history) >= 2:
            # Berechne Trend (einfache lineare Regression)
            if NUMPY_AVAILABLE and len(self.data_history) >= 3:
                x = np.arange(len(self.data_history))
                y = np.array(self.data_history)

                # Lineare Regression: y = mx + b
                coeffs = np.polyfit(x, y, 1)
                slope = coeffs[0]

                result['trend_slope'] = round(slope, 6)
                result['trend_direction'] = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'

                # R² als Maß für Linearität
                y_pred = np.polyval(coeffs, x)
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                result['r_squared'] = round(r_squared, 4)
            else:
                # Einfacher Trend: Vergleich letzter Wert mit Durchschnitt
                avg = sum(self.data_history) / len(self.data_history)
                result['trend_direction'] = 'increasing' if current_value > avg else 'decreasing'

            # Änderungsrate
            change = current_value - self.data_history[-2]
            result['change_rate'] = round(change, 4)
            result['change_percent'] = round((change / self.data_history[-2] * 100), 2) if self.data_history[-2] != 0 else 0

        return result

    def _extract_numerical_values(self, data: dict) -> list:
        """Extrahiere numerische Werte"""
        values = []
        for key, value in data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if sub_key == 'unit_info':
                        continue
                    if isinstance(sub_value, (int, float)) and not isinstance(sub_value, bool):
                        values.append(float(sub_value))
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                values.append(float(value))
        return values
```

### 12.5 Bildverarbeitungs-Plugin (plugins/image_processor.py)

```python
"""
Beispiel-Plugin: Bildverarbeitung
Analysiert Kamerabilder
"""

import logging
import io
from core.plugin_manager import ProcessingPlugin

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageFilter, ImageStat
    import numpy as np
    IMAGE_PROCESSING_AVAILABLE = True
except ImportError:
    IMAGE_PROCESSING_AVAILABLE = False
    logger.warning("PIL/NumPy nicht verfügbar - Bildverarbeitung nicht möglich")


class ImageProcessor(ProcessingPlugin):
    """Bildverarbeitungs-Plugin"""

    def __init__(self):
        super().__init__()
        self.name = "ImageProcessor"
        self.version = "1.0"
        self.description = "Analysiert und verarbeitet Kamerabilder"

    def initialize(self):
        """Initialisiere"""
        logger.info(f"{self.name}: Initialisierung")
        self.is_initialized = True
        return True

    def cleanup(self):
        """Cleanup"""
        self.is_initialized = False

    def get_required_inputs(self) -> list:
        return ['image']

    def process(self, data: dict) -> dict:
        """Verarbeite Bilddaten"""
        if not IMAGE_PROCESSING_AVAILABLE:
            logger.warning(f"{self.name}: Bildverarbeitung nicht verfügbar")
            return {'error': 'PIL/NumPy not available'}

        # Suche Bilddaten
        image_data = None
        for plugin_results in data.values():
            if isinstance(plugin_results, dict) and 'image' in plugin_results:
                image_data = plugin_results['image']
                break

        if not image_data or not isinstance(image_data, bytes):
            logger.warning(f"{self.name}: Keine Bilddaten gefunden")
            return {}

        try:
            # Lade Bild
            img = Image.open(io.BytesIO(image_data))

            # Basis-Analyse
            result = {
                'image_width': img.size[0],
                'image_height': img.size[1],
                'image_mode': img.mode,
                'image_format': img.format if img.format else 'unknown'
            }

            # Konvertiere zu Graustufen für Analyse
            gray = img.convert('L')

            # Statistiken
            stat = ImageStat.Stat(gray)
            result['brightness_mean'] = round(stat.mean[0], 2)
            result['brightness_std'] = round(stat.stddev[0], 2)
            result['brightness_median'] = round(stat.median[0], 2)

            # Histogramm-Analyse
            histogram = gray.histogram()

            # Finde dominanten Intensitätsbereich
            max_bin = histogram.index(max(histogram))
            result['dominant_intensity'] = max_bin

            # Kontrast (Differenz zwischen 95% und 5% Percentile)
            pixels = list(gray.getdata())
            sorted_pixels = sorted(pixels)
            n = len(sorted_pixels)
            p5 = sorted_pixels[int(n * 0.05)]
            p95 = sorted_pixels[int(n * 0.95)]
            result['contrast_range'] = p95 - p5

            # Kantenerkennung
            edges = gray.filter(ImageFilter.FIND_EDGES)
            edge_stat = ImageStat.Stat(edges)
            result['edge_strength'] = round(edge_stat.mean[0], 2)

            # Schärfe-Schätzung (Varianz des Laplace-Filters)
            laplacian = gray.filter(ImageFilter.Kernel((3, 3),
                [-1, -1, -1, -1, 8, -1, -1, -1, -1], 1, 0))
            lap_array = np.array(laplacian)
            result['sharpness'] = round(float(np.var(lap_array)), 2)

            # Blob-Detektion (vereinfacht: Anzahl zusammenhängender Bereiche)
            threshold = gray.point(lambda x: 255 if x > 128 else 0)
            result['binary_white_ratio'] = round(
                sum(1 for p in threshold.getdata() if p > 0) / len(list(threshold.getdata())),
                4
            )

            logger.info(f"{self.name}: Bild analysiert ({img.size[0]}x{img.size[1]})")
            return result

        except Exception as e:
            logger.error(f"{self.name}: Fehler bei Bildverarbeitung: {e}")
            return {'error': str(e)}


class ImageQualityChecker(ProcessingPlugin):
    """Prüft Bildqualität"""

    def __init__(self):
        super().__init__()
        self.name = "ImageQualityChecker"
        self.version = "1.0"
        self.description = "Prüft Bildqualität und erkennt Probleme"

    def initialize(self):
        logger.info(f"{self.name}: Initialisierung")
        self.is_initialized = True
        return True

    def cleanup(self):
        self.is_initialized = False

    def get_required_inputs(self) -> list:
        return ['image']

    def process(self, data: dict) -> dict:
        """Prüfe Bildqualität"""
        if not IMAGE_PROCESSING_AVAILABLE:
            return {'error': 'PIL/NumPy not available'}

        # Suche Bilddaten
        image_data = None
        for plugin_results in data.values():
            if isinstance(plugin_results, dict) and 'image' in plugin_results:
                image_data = plugin_results['image']
                break

        if not image_data:
            return {}

        try:
            img = Image.open(io.BytesIO(image_data))
            gray = img.convert('L')

            stat = ImageStat.Stat(gray)
            mean_brightness = stat.mean[0]
            std_brightness = stat.stddev[0]

            result = {}

            # Überbelichtung
            result['overexposed'] = 1 if mean_brightness > 240 else 0

            # Unterbelichtung
            result['underexposed'] = 1 if mean_brightness < 20 else 0

            # Niedriger Kontrast
            result['low_contrast'] = 1 if std_brightness < 20 else 0

            # Qualitätsscore (0-100)
            quality_score = 100
            if result['overexposed']:
                quality_score -= 30
            if result['underexposed']:
                quality_score -= 30
            if result['low_contrast']:
                quality_score -= 20

            # Bonus für guten Kontrast
            if std_brightness > 40:
                quality_score = min(100, quality_score + 10)

            result['quality_score'] = max(0, quality_score)
            result['quality_rating'] = (
                'excellent' if quality_score >= 90 else
                'good' if quality_score >= 70 else
                'fair' if quality_score >= 50 else
                'poor'
            )

            return result

        except Exception as e:
            logger.error(f"{self.name}: Fehler: {e}")
            return {'error': str(e)}
```

### 12.6 Programmsteuerungs-Plugin (plugins/external_program.py)

```python
"""
Beispiel-Plugin: Externe Programmsteuerung
Steuert externe Programme/Skripte
"""

import subprocess
import logging
import json
import time
from core.plugin_manager import MeasurementPlugin

logger = logging.getLogger(__name__)


class ExternalProgramController(MeasurementPlugin):
    """Steuert externe Programme"""

    def __init__(self):
        super().__init__()
        self.name = "ExternalProgramController"
        self.version = "1.0"
        self.description = "Steuert externe Programme und liest Ausgaben"

        self.program_path = None
        self.working_directory = None
        self.timeout = 30

    def initialize(self):
        """Initialisiere"""
        logger.info(f"{self.name}: Initialisierung")
        self.is_initialized = True
        return True

    def cleanup(self):
        """Cleanup"""
        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        """Setze Parameter"""
        self.current_parameters = parameters
        logger.info(f"{self.name}: Parameter gesetzt: {parameters}")

    def measure(self) -> dict:
        """Führe externes Programm aus und lese Ergebnis"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Nicht initialisiert")

        # Beispiel: Rufe Python-Skript auf
        # In echter Anwendung würde hier ein echtes Programm aufgerufen

        result = self._simulate_external_call()

        return result

    def _simulate_external_call(self):
        """Simuliere Aufruf eines externen Programms"""
        # In realer Anwendung:
        # process = subprocess.run(
        #     [self.program_path, '--param', str(value)],
        #     capture_output=True,
        #     text=True,
        #     timeout=self.timeout,
        #     cwd=self.working_directory
        # )
        # return json.loads(process.stdout)

        # Simulation
        time.sleep(0.2)

        return {
            'program_exit_code': 0,
            'program_output': 'Success',
            'execution_time': 0.2,
            'custom_result': 42.0,
            'unit_info': {
                'execution_time': 's',
                'custom_result': 'units'
            }
        }

    def get_units(self) -> dict:
        return {
            'execution_time': 's',
            'custom_result': 'units'
        }
```

## 13. Package-Initialisierung

### core/__init__.py
```python
"""
Core-Module für Messsequenz-System
"""

from .sequence_manager import SequenceManager, MeasurementSequence, ParameterRange, MeasurementPoint
from .plugin_manager import PluginManager, PluginBase, MeasurementPlugin, ProcessingPlugin
from .database_manager import DatabaseManager
from .config_manager import ConfigManager

__all__ = [
    'SequenceManager',
    'MeasurementSequence',
    'ParameterRange',
    'MeasurementPoint',
    'PluginManager',
    'PluginBase',
    'MeasurementPlugin',
    'ProcessingPlugin',
    'DatabaseManager',
    'ConfigManager'
]
```

### gui/__init__.py
```python
"""
GUI-Module für Messsequenz-System
"""

from .main_window import MainWindow
from .sequence_editor import SequenceEditor
from .measurement_control import MeasurementControl
from .data_visualization import DataVisualization
from .plugin_manager_gui import PluginManagerGUI
from .database_browser import DatabaseBrowser

__all__ = [
    'MainWindow',
    'SequenceEditor',
    'MeasurementControl',
    'DataVisualization',
    'PluginManagerGUI',
    'DatabaseBrowser'
]
```

### plugins/__init__.py
```python
"""
Plugins für Messsequenz-System
"""

# Plugins werden dynamisch geladen
```

Fortsetzung mit requirements.txt, README und Installationsanleitung folgt...



## 14. Requirements und Dependencies (requirements.txt)

```txt
# Messsequenz-System - Python Dependencies
# Kern-Abhängigkeiten

# GUI
tkinter  # Meist in Python enthalten

# Datenbank
# sqlite3 ist in Python Standard-Bibliothek enthalten

# Optionale Abhängigkeiten für erweiterte Funktionalität

# Wissenschaftliche Berechnungen
numpy>=1.21.0
scipy>=1.7.0

# Datenvisualisierung
matplotlib>=3.4.0

# Bildverarbeitung
Pillow>=9.0.0

# Datenverarbeitung
pandas>=1.3.0

# Serielle Kommunikation (für echte Hardware)
pyserial>=3.5

# USB-Geräte
pyusb>=1.2.1

# Netzwerk-Kommunikation
requests>=2.26.0

# Zusätzliche Tools
python-dateutil>=2.8.0
```

## 15. Setup-Script (setup.py)

```python
"""
Setup-Script für Messsequenz-System
"""

from setuptools import setup, find_packages
import os

# Lese README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Lese Requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="measurement-sequence-system",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Professionelles Messsequenz-Verwaltungssystem mit Plugin-Architektur",
    long_description=long_description,
    long_description_content_type="text/markdown",LICENSE
    url="https://github.com/yourusername/measurement-sequence-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'measurement-system=main:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['*.json', '*.ini', '*.txt'],
    },
)
```

## 16. README.md

```markdown
# Professionelles Messsequenz-System

Ein umfassendes, erweiterbares System zur Verwaltung und Durchführung von Messsequenzen mit Plugin-Architektur.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🌟 Features

- **Sequenz-Generator**: Flexible Definition von Messabläufen mit Parameterbereichen
- **Plugin-System**: Erweiterbar durch Messgeräte- und Verarbeitungs-Plugins
- **Persistente Speicherung**: JSON-basierte Sequenzen, SQLite-Datenbank für Messergebnisse
- **Datenvisualisierung**: Integrierte Grafik-Darstellung mit Matplotlib
- **Statistische Auswertung**: Automatische Berechnung von Kennwerten
- **Bildverarbeitung**: Kamera-Integration und Bildanalyse
- **Zeitstempel & Einheiten**: Vollständige Metadaten für alle Messungen

## 📋 Inhaltsverzeichnis

- [Installation](#installation)
- [Schnellstart](#schnellstart)
- [Architektur](#architektur)
- [Plugin-Entwicklung](#plugin-entwicklung)
- [Verwendung](#verwendung)
- [API-Referenz](#api-referenz)
- [Beispiele](#beispiele)
- [Lizenz](#lizenz)

## 🚀 Installation

### Voraussetzungen

- Python 3.8 oder höher
- Tkinter (meist in Python enthalten)

### Standard-Installation

```bash
# Repository klonen
git clone https://github.com/yourusername/measurement-sequence-system.git
cd measurement-sequence-system

# Virtuelle Umgebung erstellen (empfohlen)
python -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python main.py
```

### Installation mit pip

```bash
pip install measurement-sequence-system
measurement-system
```

## ⚡ Schnellstart

### 1. Neue Messsequenz erstellen

```python
from core.sequence_manager import SequenceManager, ParameterRange

# Manager initialisieren
manager = SequenceManager(plugin_manager, database_manager)

# Neue Sequenz erstellen
sequence = manager.create_sequence("Meine Erste Sequenz", "Beschreibung")

# Parameterbereich hinzufügen
param_range = ParameterRange(
    parameter_name="temperature",
    start=20.0,
    end=100.0,
    steps=5,
    unit="°C"
)
sequence.add_parameter_range(param_range)

# Messpunkte generieren
sequence.generate_measurement_points()

# Sequenz speichern
sequence.save_to_file("meine_sequenz.json")
```

### 2. Eigenes Plugin erstellen

```python
from core.plugin_manager import MeasurementPlugin

class MeinSensor(MeasurementPlugin):
    def __init__(self):
        super().__init__()
        self.name = "MeinSensor"
        self.description = "Mein eigener Sensor"

    def initialize(self):
        # Hardware-Initialisierung
        self.is_initialized = True
        return True

    def cleanup(self):
        # Cleanup
        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        # Parameter setzen
        pass

    def measure(self) -> dict:
        # Messung durchführen
        return {
            'value': 42.0,
            'unit_info': {'value': 'units'}
        }

    def get_units(self) -> dict:
        return {'value': 'units'}
```

### 3. Sequenz ausführen

```python
# Sequenz laden
manager.load_sequence("meine_sequenz.json")

# Callbacks registrieren
manager.register_callback('on_point_complete', lambda point: print(f"Punkt fertig: {point.name}"))

# Sequenz starten
manager.start_sequence()
```

## 🏗️ Architektur

```
measurement-sequence-system/
├── main.py                 # Hauptanwendung
├── core/                   # Kern-Module
│   ├── __init__.py
│   ├── sequence_manager.py     # Sequenzverwaltung
│   ├── plugin_manager.py       # Plugin-System
│   ├── database_manager.py     # Datenbank-Verwaltung
│   └── config_manager.py       # Konfiguration
├── gui/                    # GUI-Module
│   ├── __init__.py
│   ├── main_window.py          # Hauptfenster
│   ├── sequence_editor.py      # Sequenz-Editor
│   ├── measurement_control.py  # Messsteuerung
│   ├── data_visualization.py   # Visualisierung
│   ├── plugin_manager_gui.py   # Plugin-Verwaltung
│   └── database_browser.py     # Datenbank-Browser
├── plugins/                # Plugin-Verzeichnis
│   ├── __init__.py
│   ├── temperature_sensor.py   # Beispiel-Plugins
│   ├── electrical_meter.py
│   ├── camera_plugin.py
│   ├── statistics_processor.py
│   └── image_processor.py
├── tests/                  # Unit-Tests
├── docs/                   # Dokumentation
├── examples/               # Beispiele
├── requirements.txt        # Abhängigkeiten
├── setup.py               # Installation
└── README.md              # Diese Datei
```

## 🔌 Plugin-Entwicklung

### Messgeräte-Plugin

Messgeräte-Plugins erben von `MeasurementPlugin`:

```python
from core.plugin_manager import MeasurementPlugin

class MyDevice(MeasurementPlugin):
    def initialize(self):
        """Initialisierung der Hardware"""
        # Verbindung aufbauen
        return True

    def cleanup(self):
        """Aufräumen"""
        # Verbindung schließen
        pass

    def set_parameters(self, parameters: dict):
        """Parameter setzen"""
        # Gerät konfigurieren
        pass

    def measure(self) -> dict:
        """Messung durchführen"""
        # Werte erfassen
        return {
            'value1': 123.45,
            'value2': 67.89,
            'unit_info': {
                'value1': 'V',
                'value2': 'A'
            }
        }

    def get_units(self) -> dict:
        """Einheiten zurückgeben"""
        return {'value1': 'V', 'value2': 'A'}
```

### Verarbeitungs-Plugin

Verarbeitungs-Plugins erben von `ProcessingPlugin`:

```python
from core.plugin_manager import ProcessingPlugin

class MyProcessor(ProcessingPlugin):
    def initialize(self):
        """Initialisierung"""
        return True

    def cleanup(self):
        """Cleanup"""
        pass

    def get_required_inputs(self) -> list:
        """Erforderliche Eingaben"""
        return ['temperature', 'pressure']

    def process(self, data: dict) -> dict:
        """Daten verarbeiten"""
        # Verarbeitung durchführen
        result = {}
        # ... Berechnungen ...
        return result
```

## 📖 Verwendung

### GUI-Modus

Starten Sie die Anwendung:

```bash
python main.py
```

**Workflow:**

1. **Sequenz erstellen**: Datei → Neue Sequenz
2. **Parameterbereiche definieren**: Fügen Sie Parameterbereiche hinzu
3. **Messpunkte generieren**: Klicken Sie auf "Messpunkte generieren"
4. **Plugins auswählen**: Wählen Sie Messgeräte und Verarbeitungs-Plugins
5. **Sequenz speichern**: Datei → Sequenz speichern
6. **Messung starten**: Messung → Starten (F5)
7. **Ergebnisse visualisieren**: Wechseln Sie zum Visualisierungs-Tab

### Programmatische Verwendung

```python
from core.sequence_manager import SequenceManager, MeasurementSequence
from core.plugin_manager import PluginManager
from core.database_manager import DatabaseManager

# Manager initialisieren
plugin_manager = PluginManager()
database_manager = DatabaseManager('measurements.db')
sequence_manager = SequenceManager(plugin_manager, database_manager)

# Plugins laden
plugin_manager.load_plugins()

# Sequenz erstellen und ausführen
sequence = sequence_manager.create_sequence("Test", "Testmessung")

# ... Sequenz konfigurieren ...

# Callback registrieren
def on_complete(seq):
    print(f"Sequenz {seq.name} abgeschlossen!")

sequence_manager.register_callback('on_complete', on_complete)

# Starten
sequence_manager.start_sequence()
```

## 💾 Datenbankschema
LICENSE
### Tabellen

**sequences**
- id (INTEGER PRIMARY KEY)
- name (TEXT)
- description (TEXT)
- created_at (TEXT)
- metadata (TEXT JSON)

**measurement_points**
- id (INTEGER PRIMARY KEY)
- sequence_name (TEXT)
- point_name (TEXT)
- timestamp (TEXT)
- parameters (TEXT JSON)

**measurement_values**
- id (INTEGER PRIMARY KEY)
- point_id (INTEGER)
- parameter_name (TEXT)
- value (REAL)
- unit (TEXT)
- plugin_name (TEXT)
- timestamp (TEXT)

**measurement_blobs**
- id (INTEGER PRIMARY KEY)
- point_id (INTEGER)
- data_type (TEXT)
- data (BLOB)
- metadata (TEXT JSON)
- timestamp (TEXT)

## 📊 Beispiele

### Beispiel 1: Temperatur-Rampe

```python
from core.sequence_manager import ParameterRange

# Temperatur von 20°C bis 100°C in 9 Schritten
temp_range = ParameterRange(
    parameter_name="temperature",
    start=20.0,
    end=100.0,
    steps=9,
    unit="°C"
)

sequence.add_parameter_range(temp_range)
sequence.active_plugins = ['TemperatureSensor', 'ElectricalMeter']
sequence.processing_plugins = ['StatisticsProcessor']
sequence.generate_measurement_points()
```

### Beispiel 2: 2D-Parameter-Sweep

```python
# Temperatur und Spannung variieren
temp_range = ParameterRange("temperature", 25, 75, 5, "°C")
voltage_range = ParameterRange("voltage", 0, 10, 11, "V")

sequence.add_parameter_range(temp_range)
sequence.add_parameter_range(voltage_range)

# Erzeugt 5 x 11 = 55 Messpunkte
sequence.generate_measurement_points()
```

### Beispiel 3: Datenexport

```python
# Daten aus Datenbank laden
data = database_manager.get_sequence_data("Meine Sequenz")

# Als CSV exportieren
import csvLICENSE

with open('export.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Timestamp', 'Parameter', 'Value', 'Unit'])

    for point in data:
        for plugin_name, values in point['values'].items():
            for param, param_data in values.items():
                writer.writerow([
                    point['timestamp'],
                    param,
                    param_data['value'],
                    param_data['unit']
                ])
```

## 🧪 Tests

Tests ausführen:

```bash
# Alle Tests
python -m pytest tests/
LICENSE
# Spezifische Tests
python -m pytest tests/test_sequence_manager.py

# Mit Coverage
python -m pytest --cov=core --cov=gui tests/
```

## 📝 Konfiguration

Die Konfiguration wird in `config.json` gespeichert:

```json
{
    "database_path": "measurements.db",
    "plugin_directory": "plugins",
    "auto_save": true,
    "measurement_delay": 0.5,
    "max_history": 1000,
    "plot_settings": {
        "theme": "default",
        "grid": true,
        "legend": true
    },
    "recent_files": []
}
```

## 🔧 Fehlerbehebung

### Plugin wird nicht geladen

- Prüfen Sie, ob die Plugin-Datei im `plugins/` Verzeichnis liegt
- Überprüfen Sie, ob die Klasse von `MeasurementPlugin` oder `ProcessingPlugin` erbt
- Schauen Sie in die Log-Datei `measurement_system.log`

### Datenbank-Fehler

- Stellen Sie sicher, dass Sie Schreibrechte im Verzeichnis haben
- Löschen Sie ggf. die `measurements.db` Datei und starten Sie neu

### Import-Fehler

```bash
# Installieren Sie fehlende Pakete
pip install -r requirements.txt
```

## 🤝 Beitragen

Contributions sind willkommen! Bitte:

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Committen Sie Ihre Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Pushen Sie zum Branch (`git push origin feature/AmazingFeature`)
5. Öffnen Sie einen Pull Request

## 📜 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe [LICENSE](LICENSE) Datei für Details.

## 👥 Autoren

- **Ihr Name** - *Initial work*

## 🙏 Danksagungen

- Python Community
- Tkinter
- Matplotlib
- NumPy/SciPy
- Pillow

## 📧 Kontakt

Bei Fragen oder Problemen:
- Issue Tracker: https://github.com/yourusername/measurement-sequence-system/issues
- E-Mail: your.email@example.com

---

**Hinweis**: Dies ist eine professionelle Messsequenz-Software für Labor- und Produktionsumgebungen.
```

## 17. Unit-Tests (tests/test_sequence_manager.py)

```python
"""
Unit-Tests für SequenceManager
"""

import unittest
import tempfile
import os
from core.sequence_manager import (
    SequenceManager, MeasurementSequence,
    ParameterRange, MeasurementPoint
)
from core.plugin_manager import PluginManager
from core.database_manager import DatabaseManager


class TestParameterRange(unittest.TestCase):
    """Tests für ParameterRange"""

    def test_create_range(self):
        """Test Erstellung eines Parameterbereichs"""
        pr = ParameterRange("temperature", 0, 100, 5, "°C")

        self.assertEqual(pr.parameter_name, "temperature")
        self.assertEqual(pr.start, 0)
        self.assertEqual(pr.end, 100)
        self.assertEqual(pr.steps, 5)
        self.assertEqual(pr.unit, "°C")

    def test_get_values(self):
        """Test Wert-Generierung"""
        pr = ParameterRange("temp", 0, 100, 5, "°C")
        values = pr.get_values()

        self.assertEqual(len(values), 5)
        self.assertEqual(values[0], 0)
        self.assertEqual(values[-1], 100)
        self.assertAlmostEqual(values[1], 25, places=5)

    def test_single_step(self):
        """Test einzelner Schritt"""
        pr = ParameterRange("temp", 50, 100, 1, "°C")
        values = pr.get_values()

        self.assertEqual(len(values), 1)
        self.assertEqual(values[0], 50)

    def test_to_dict(self):
        """Test Serialisierung"""
        pr = ParameterRange("temp", 0, 100, 5, "°C")
        data = pr.to_dict()

        self.assertIsInstance(data, dict)
        self.assertEqual(data['parameter_name'], "temp")
        self.assertEqual(data['steps'], 5)

    def test_from_dict(self):
        """Test Deserialisierung"""
        data = {
            'parameter_name': 'voltage',
            'start': 0,
            'end': 10,
            'steps': 11,
            'unit': 'V'
        }
        pr = ParameterRange.from_dict(data)

        self.assertEqual(pr.parameter_name, 'voltage')
        self.assertEqual(pr.steps, 11)


class TestMeasurementPoint(unittest.TestCase):
    """Tests für MeasurementPoint"""

    def test_create_point(self):
        """Test Erstellung eines Messpunkts"""
        params = {'temp': 25.0, 'voltage': 5.0}
        point = MeasurementPoint("Point_1", params)

        self.assertEqual(point.name, "Point_1")
        self.assertEqual(point.parameters, params)
        self.assertIsNone(point.timestamp)
        self.assertEqual(point.results, {})

    def test_to_dict(self):
        """Test Serialisierung"""
        point = MeasurementPoint("Point_1", {'temp': 25.0})
        data = point.to_dict()

        self.assertIsInstance(data, dict)
        self.assertEqual(data['name'], "Point_1")
        self.assertEqual(data['parameters']['temp'], 25.0)

    def test_from_dict(self):
        """Test Deserialisierung"""
        data = {
            'name': 'Point_2',
            'parameters': {'voltage': 10.0},
            'timestamp': '2024-01-01T12:00:00',
            'results': {'sensor1': {'value': 42}}
        }
        point = MeasurementPoint.from_dict(data)

        self.assertEqual(point.name, 'Point_2')
        self.assertEqual(point.parameters['voltage'], 10.0)
        self.assertEqual(point.timestamp, '2024-01-01T12:00:00')


class TestMeasurementSequence(unittest.TestCase):
    """Tests für MeasurementSequence"""

    def test_create_sequence(self):
        """Test Sequenz-Erstellung"""
        seq = MeasurementSequence("Test Sequence", "Description")

        self.assertEqual(seq.name, "Test Sequence")
        self.assertEqual(seq.description, "Description")
        self.assertEqual(len(seq.parameter_ranges), 0)
        self.assertEqual(len(seq.measurement_points), 0)

    def test_add_parameter_range(self):
        """Test Hinzufügen von Parameterbereichen"""
        seq = MeasurementSequence("Test")
        pr = ParameterRange("temp", 0, 100, 5, "°C")

        seq.add_parameter_range(pr)

        self.assertEqual(len(seq.parameter_ranges), 1)
        self.assertEqual(seq.parameter_ranges[0].parameter_name, "temp")

    def test_generate_measurement_points_single_range(self):
        """Test Messpunkt-Generierung mit einem Bereich"""
        seq = MeasurementSequence("Test")
        pr = ParameterRange("temp", 0, 100, 5, "°C")
        seq.add_parameter_range(pr)

        seq.generate_measurement_points()

        self.assertEqual(len(seq.measurement_points), 5)
        self.assertEqual(seq.measurement_points[0].parameters['temp'], 0)
        self.assertEqual(seq.measurement_points[-1].parameters['temp'], 100)

    def test_generate_measurement_points_two_ranges(self):
        """Test Messpunkt-Generierung mit zwei Bereichen"""
        seq = MeasurementSequence("Test")
        pr1 = ParameterRange("temp", 20, 40, 3, "°C")
        pr2 = ParameterRange("voltage", 0, 10, 2, "V")

        seq.add_parameter_range(pr1)
        seq.add_parameter_range(pr2)

        seq.generate_measurement_points()

        # 3 x 2 = 6 Kombinationen
        self.assertEqual(len(seq.measurement_points), 6)

        # Prüfe erste und letzte Kombination
        first = seq.measurement_points[0]
        self.assertIn('temp', first.parameters)
        self.assertIn('voltage', first.parameters)

    def test_save_and_load(self):
        """Test Speichern und Laden"""
        seq = MeasurementSequence("Test", "Description")
        pr = ParameterRange("temp", 0, 100, 3, "°C")
        seq.add_parameter_range(pr)
        seq.generate_measurement_points()

        # Temporäre Datei
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            # Speichern
            seq.save_to_file(temp_path)

            # Laden
            loaded_seq = MeasurementSequence.load_from_file(temp_path)

            # Vergleichen
            self.assertEqual(loaded_seq.name, seq.name)
            self.assertEqual(loaded_seq.description, seq.description)
            self.assertEqual(len(loaded_seq.parameter_ranges), 1)
            self.assertEqual(len(loaded_seq.measurement_points), 3)

        finally:
            # Aufräumen
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestSequenceManager(unittest.TestCase):
    """Tests für SequenceManager"""

    def setUp(self):
        """Setup vor jedem Test"""
        self.plugin_manager = PluginManager()

        # Temporäre Datenbank
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.database_manager = DatabaseManager(self.db_path)

        self.sequence_manager = SequenceManager(
            self.plugin_manager,
            self.database_manager
        )

    def tearDown(self):
        """Cleanup nach jedem Test"""
        self.database_manager.close()
        os.close(self.db_fd)
        os.remove(self.db_path)

    def test_create_sequence(self):
        """Test Sequenz-Erstellung"""
        seq = self.sequence_manager.create_sequence("Test", "Description")

        self.assertIsNotNone(seq)
        self.assertEqual(seq.name, "Test")
        self.assertEqual(self.sequence_manager.current_sequence, seq)

    def test_save_and_load_sequence(self):
        """Test Speichern und Laden von Sequenzen"""
        # Erstelle Sequenz
        seq = self.sequence_manager.create_sequence("Test")
        pr = ParameterRange("temp", 0, 100, 3, "°C")
        seq.add_parameter_range(pr)
        seq.generate_measurement_points()

        # Temporäre Datei
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            # Speichern
            self.sequence_manager.save_sequence(temp_path)

            # Neuen Manager erstellen
            new_manager = SequenceManager(
                self.plugin_manager,
                self.database_manager
            )

            # Laden
            loaded_seq = new_manager.load_sequence(temp_path)

            self.assertIsNotNone(loaded_seq)
            self.assertEqual(loaded_seq.name, "Test")

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_callback_registration(self):
        """Test Callback-Registrierung"""
        called = {'flag': False}

        def callback():
            called['flag'] = True

        self.sequence_manager.register_callback('on_complete', callback)
        self.sequence_manager._trigger_callback('on_complete')

        self.assertTrue(called['flag'])


if __name__ == '__main__':
    unittest.main()
```

## 18. Weitere Tests (tests/test_database_manager.py)

```python
"""
Unit-Tests für DatabaseManager
"""

import unittest
import tempfile
import os
from core.database_manager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Tests für DatabaseManager"""

    def setUp(self):
        """Setup vor jedem Test"""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.db_manager = DatabaseManager(self.db_path)

    def tearDown(self):
        """Cleanup nach jedem Test"""
        self.db_manager.close()
        os.close(self.db_fd)
        os.remove(self.db_path)

    def test_database_initialization(self):
        """Test Datenbank-Initialisierung"""
        self.assertIsNotNone(self.db_manager.connection)

        # Prüfe ob Tabellen existieren
        cursor = self.db_manager.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        self.assertIn('measurement_points', tables)
        self.assertIn('measurement_values', tables)
        self.assertIn('measurement_blobs', tables)

    def test_save_measurement(self):
        """Test Speichern von Messungen"""
        self.db_manager.save_measurement(
            sequence_name="Test Sequence",
            point_name="Point_1",
            timestamp="2024-01-01T12:00:00",
            parameters={'temp': 25.0},
            results={
                'sensor1': {
                    'value1': 42.0,
                    'value2': 3.14,
                    'unit_info': {'value1': 'V', 'value2': 'A'}
                }
            }
        )

        # Prüfe ob gespeichert
        data = self.db_manager.get_sequence_data("Test Sequence")

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['point_name'], "Point_1")
        self.assertIn('sensor1', data[0]['values'])

    def test_get_all_sequences(self):
        """Test Abruf aller Sequenzen"""
        # Speichere mehrere Messungen
        for i in range(3):
            self.db_manager.save_measurement(
                sequence_name=f"Sequence_{i}",
                point_name=f"Point_{i}",
                timestamp="2024-01-01T12:00:00",
                parameters={},
                results={}
            )

        sequences = self.db_manager.get_all_sequences()

        self.assertEqual(len(sequences), 3)
        self.assertIn("Sequence_0", sequences)
        self.assertIn("Sequence_2", sequences)

    def test_delete_sequence(self):
        """Test Löschen von Sequenzen"""
        # Speichere Messung
        self.db_manager.save_measurement(
            sequence_name="To Delete",
            point_name="Point_1",
            timestamp="2024-01-01T12:00:00",
            parameters={},
            results={'sensor': {'value': 1.0, 'unit_info': {}}}
        )

        # Prüfe Existenz
        sequences = self.db_manager.get_all_sequences()
        self.assertIn("To Delete", sequences)

        # Lösche
        self.db_manager.delete_sequence("To Delete")

        # Prüfe ob gelöscht
        sequences = self.db_manager.get_all_sequences()
        self.assertNotIn("To Delete", sequences)


if __name__ == '__main__':
    unittest.main()
```

## 19. Beispiel-Skript (examples/example_temperature_sweep.py)

```python
"""
Beispiel: Temperatur-Sweep mit elektrischen Messungen
"""

import sys
import os

# Pfad anpassen um Module zu importieren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.sequence_manager import SequenceManager, ParameterRange
from core.plugin_manager import PluginManager
from core.database_manager import DatabaseManager
import time


def main():
    """Beispiel für automatische Messsequenz"""

    print("=" * 60)
    print("Temperatur-Sweep Beispiel")
    print("=" * 60)

    # Manager initialisieren
    plugin_manager = PluginManager()
    database_manager = DatabaseManager('example_measurements.db')
    sequence_manager = SequenceManager(plugin_manager, database_manager)

    # Plugins laden
    plugin_manager.load_plugins()
    print(f"\nGeladene Plugins: {len(plugin_manager.plugin_classes)}")
    for name in plugin_manager.plugin_classes.keys():
        print(f"  - {name}")

    # Sequenz erstellen
    print("\n1. Erstelle Sequenz...")
    sequence = sequence_manager.create_sequence(
        "Temperatur-Sweep Beispiel",
        "Messung von Spannung und Strom bei verschiedenen Temperaturen"
    )

    # Parameterbereiche definieren
    print("2. Definiere Parameterbereiche...")

    # Temperatur: 25°C bis 75°C in 6 Schritten
    temp_range = ParameterRange(
        parameter_name="temperature",
        start=25.0,
        end=75.0,
        steps=6,
        unit="°C"
    )
    sequence.add_parameter_range(temp_range)

    # Spannung: 0V bis 5V in 3 Schritten
    voltage_range = ParameterRange(
        parameter_name="voltage",
        start=0.0,
        end=5.0,
        steps=3,
        unit="V"
    )
    sequence.add_parameter_range(voltage_range)

    # Messpunkte generieren
    print("3. Generiere Messpunkte...")
    sequence.generate_measurement_points()
    print(f"   -> {len(sequence.measurement_points)} Messpunkte generiert")

    # Plugins auswählen
    print("4. Wähle Plugins...")
    sequence.active_plugins = ['TemperatureSensor', 'ElectricalMeter']
    sequence.processing_plugins = ['StatisticsProcessor']

    # Sequenz speichern
    print("5. Speichere Sequenz...")
    sequence.save_to_file('temperature_sweep.json')
    print("   -> Gespeichert als 'temperature_sweep.json'")

    # Callbacks registrieren
    def on_start(seq):
        print(f"\n{'='*60}")
        print(f"Messung gestartet: {seq.name}")
        print(f"{'='*60}")

    def on_point_complete(point):
        print(f"\n✓ Messpunkt abgeschlossen: {point.name}")
        print(f"  Parameter: {point.parameters}")
        print(f"  Ergebnisse:")
        for plugin_name, results in point.results.items():
            if isinstance(results, dict):
                for key, value in results.items():
                    if key != 'unit_info':
                        print(f"    {plugin_name}.{key} = {value}")

    def on_progress(current, total, percentage):
        print(f"  Fortschritt: {current}/{total} ({percentage:.1f}%)")

    def on_complete(seq):
        print(f"\n{'='*60}")
        print(f"Messung abgeschlossen: {seq.name}")
        print(f"{'='*60}")

    def on_error(error):
        print(f"\n✗ FEHLER: {error}")

    sequence_manager.register_callback('on_start', on_start)
    sequence_manager.register_callback('on_point_complete', on_point_complete)
    sequence_manager.register_callback('on_progress', on_progress)
    sequence_manager.register_callback('on_complete', on_complete)
    sequence_manager.register_callback('on_error', on_error)

    # Sequenz ausführen
    print("\n6. Starte Messung...\n")
    sequence_manager.start_sequence()

    # Warte auf Abschluss
    while sequence_manager.is_running():
        time.sleep(0.5)

    # Ergebnisse anzeigen
    print("\n7. Lade Ergebnisse aus Datenbank...")
    data = database_manager.get_sequence_data(sequence.name)

    print(f"\n{len(data)} Messpunkte in Datenbank:")
    for i, point in enumerate(data[:3]):  # Zeige erste 3
        print(f"\n  Punkt {i+1}: {point['point_name']}")
        print(f"  Zeitstempel: {point['timestamp']}")
        print(f"  Parameter: {point['parameters']}")

    if len(data) > 3:
        print(f"\n  ... und {len(data) - 3} weitere Punkte")

    # Cleanup
    database_manager.close()

    print("\n" + "="*60)
    print("Beispiel abgeschlossen!")
    print("="*60)
    print(f"\nDateien erstellt:")
    print(f"  - temperature_sweep.json (Sequenz-Definition)")
    print(f"  - example_measurements.db (SQLite-Datenbank)")
    print("\nStarten Sie die GUI um Ergebnisse zu visualisieren:")
    print("  python main.py")


if __name__ == "__main__":
    main()
```

## 20. Launcher-Skript (run.py)

```python
"""
Launcher für das Messsequenz-System
"""

import sys
import os
import logging
README.md
# Stelle sicher dass alle Module gefunden werden
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_dependencies():
    """Prüfe ob alle Abhängigkeiten installiert sind"""
    missing = []

    # Prüfe optionale Pakete
    optional = {
        'numpy': 'NumPy',
        'matplotlib': 'Matplotlib',
        'PIL': 'Pillow'
    }

    for module, name in optional.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(name)

    if missing:README.md
        print("Warnung: Folgende optionale Pakete sind nicht installiert:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nEinige Funktionen könnten eingeschränkt sein.")
        print("Installieren Sie mit: pip install -r requirements.txt\n")

        response = input("Trotzdem fortfahren? (j/n): ")
        if response.lower() not in ['j', 'y', 'yes', 'ja']:
            sys.exit(0)


def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("Messsequenz-System v1.0")
    print("=" * 60)
    print()

    # Prüfe Abhängigkeiten
    check_dependencies()

    # Importiere und starte Hauptanwendung
    try:
        from main import MeasurementApplication

        app = MeasurementApplication()README.md
        app.run()

    except KeyboardInterrupt:
        print("\nAnwendung durch Benutzer beendet.")
        sys.exit(0)
    except Exception as e:
        logging.critical(f"Kritischer Fehler: {e}", exc_info=True)
        print(f"\nKRITISCHER FEHLER: {e}")
        print("Siehe measurement_system.log für Details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

## 21. Konfigurations-Beispiel (config.example.json)

```json
{
    "database_path": "measurements.db",
    "plugin_directory": "plugins",
    "last_sequence_path": "",
    "window_geometry": "1400x900",
    "auto_save": true,
    "measurement_delay": 0.5,
    "max_history": 1000,
    "plot_settings": {
        "theme": "default",
        "grid": true,
        "legend": true,
        "dpi": 100,
        "figure_size": [8, 6]
    },
    "recent_files": [],
    "logging": {
        "level": "INFO",
        "file": "measurement_system.log",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "hardware": {
        "timeout": 30,
        "retry_count": 3,
        "serial_port": "COM1",
        "baud_rate": 9600
    }
}
```

## 22. .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Projekt-spezifisch
*.db
*.db-journal
*.log
config.json
measurements/
*.png
*.jpg
*.jpeg

# Aber behalte Beispiele
!examples/*.json
!docs/images/*.png

# OS
.DS_Store
Thumbs.db

# Tests
.pytest_cache/
.coverage
htmlcov/
```

## 23. LICENSE

```
MIT License

Copyright (c) 2024 [Ihr Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 24. Zusammenfassung und Schnellstart-Anleitung

### Installation und Start

```bash
# 1. Repository klonen oder Dateien herunterladen
git clone <repository-url>
cd measurement-sequence-system

# 2. Virtuelle Umgebung erstellen (empfohlen)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Anwendung starten
python run.py

# ODER direkt:
python main.py
```

### Projekt-Struktur erstellen

```bash
# Erstellen Sie folgende Verzeichnisstruktur:
measurement-sequence-system/
├── main.py
├── run.py
├── requirements.txt
├── setup.py
├── README.md
├── LICENSE
├── .gitignore
├── config.example.json
├── core/
│   ├── __init__.py
│   ├── sequence_manager.py
│   ├── plugin_manager.py
│   ├── database_manager.py
│   └── config_manager.py
├── gui/
│   ├── __init__.py
│   ├── main_window.py
│   ├── sequence_editor.py
│   ├── measurement_control.py
│   ├── data_visualization.py
│   ├── plugin_manager_gui.py
│   └── database_browser.py
├── plugins/
│   ├── __init__.py
│   ├── temperature_sensor.py
│   ├── electrical_meter.py
│   ├── camera_plugin.py
│   ├── statistics_processor.py
│   ├── image_processor.py
│   └── external_program.py
├── tests/
│   ├── __init__.py
│   ├── test_sequence_manager.py
│   └── test_database_manager.py
└── examples/
    └── example_temperature_sweep.py
```

**Die Software ist nun vollständig und einsatzbereit!** 🎉

Sie haben ein professionelles, erweiterbares Messsequenz-System mit:
- ✅ Vollständiger GUI
- ✅ Plugin-Architektur
- ✅ Datenbank-Persistenz
- ✅ JSON-Sequenzen
- ✅ Visualisierung
- ✅ Statistik & Bildverarbeitung
- ✅ Umfangreichen Tests
- ✅ Dokumentation


## 5. Beispiel-Sequenzen (examples/example_sequences/)

### examples/example_sequences/simple_temperature.json

```json
{
  "name": "Einfacher Temperatur-Sweep",
  "description": "Grundlegende Temperaturmessung von 20°C bis 80°C",
  "parameter_ranges": [
    {
      "parameter_name": "temperature",
      "start": 20.0,
      "end": 80.0,
      "steps": 7,
      "unit": "°C"
    }
  ],
  "measurement_points": [],
  "active_plugins": [
    "TemperatureSensor",
    "ElectricalMeter"
  ],
  "processing_plugins": [
    "StatisticsProcessor"
  ],
  "metadata": {
    "created": "2024-01-01",
    "author": "System",
    "category": "Temperature Test"
  }
}
```

### examples/example_sequences/voltage_current_sweep.json

```json
{
  "name": "Spannung-Strom Charakterisierung",
  "description": "2D-Sweep über Spannung und Strom zur Charakterisierung",
  "parameter_ranges": [
    {
      "parameter_name": "voltage",
      "start": 0.0,
      "end": 10.0,
      "steps": 11,
      "unit": "V"
    },
    {
      "parameter_name": "current_limit",
      "start": 0.1,
      "end": 1.0,
      "steps": 5,
      "unit": "A"
    }
  ],
  "measurement_points": [],
  "active_plugins": [
    "PowerSupply",
    "ElectricalMeter"
  ],
  "processing_plugins": [
    "StatisticsProcessor",
    "TrendAnalyzer"
  ],
  "metadata": {
    "created": "2024-01-01",
    "author": "System",
    "category": "Power Test"
  }
}
```

### examples/example_sequences/camera_test.json

```json
{
  "name": "Kamera-Bildaufnahme Test",
  "description": "Bildaufnahme mit verschiedenen Belichtungszeiten",
  "parameter_ranges": [
    {
      "parameter_name": "exposure",
      "start": 10,
      "end": 500,
      "steps": 6,
      "unit": "ms"
    },
    {
      "parameter_name": "gain",
      "start": 1.0,
      "end": 5.0,
      "steps": 3,
      "unit": ""
    }
  ],
  "measurement_points": [],
  "active_plugins": [
    "CameraPlugin"
  ],
  "processing_plugins": [
    "ImageProcessor",
    "ImageQualityChecker"
  ],
  "metadata": {
    "created": "2024-01-01",
    "author": "System",
    "category": "Image Acquisition"
  }
}
```

### examples/example_sequences/delay_test.json

```json
{
  "name": "Delay-Plugin Test",
  "description": "Test des nicht-blockierenden Delay-Plugins",
  "parameter_ranges": [
    {
      "parameter_name": "delay",
      "start": 0.5,
      "end": 3.0,
      "steps": 6,
      "unit": "s"
    }
  ],
  "measurement_points": [],
  "active_plugins": [
    "DelayPlugin",
    "TemperatureSensor"
  ],
  "processing_plugins": [],
  "metadata": {
    "created": "2024-01-01",
    "author": "System",
    "category": "Timing Test"
  }
}
```

## 6. Verbesserte Hauptdatei mit vollständiger Integration (main.py)

```python
"""
Messsequenz-Software - Hauptanwendung
Professional Measurement Sequence Management System
VOLLSTÄNDIG IMPLEMENTIERT
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import logging
import sys
import os
from pathlib import Path
from gui.main_window import MainWindow
from core.sequence_manager import SequenceManager
from core.plugin_manager import PluginManager
from core.database_manager import DatabaseManager
from core.config_manager import ConfigManager

# Stelle sicher dass alle Pfade korrekt sind
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


def setup_logging(config_manager):
    """Konfiguriere Logging-System"""
    log_config = config_manager.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_file = log_config.get('file', 'measurement_system.log')
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Konvertiere String zu Log-Level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)


class MeasurementApplication:
    """Hauptanwendungsklasse für das Messsystem"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Professionelles Messsequenz-System v1.0")

        # Style konfigurieren
        self._configure_style()

        # Initialisiere Manager
        self._initialize_managers()

        # Setup Logging
        self.logger = setup_logging(self.config_manager)

        # Erstelle Verzeichnisse falls nicht vorhanden
        self._ensure_directories()

        # Setze Icon (falls vorhanden)
        self._set_icon()

        # Erstelle GUI
        self.main_window = MainWindow(
            self.root,
            self.sequence_manager,
            self.plugin_manager,
            self.database_manager,
            self.config_manager
        )

        # Event-Handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Behandle unbehandelte Exceptions
        self.root.report_callback_exception = self.handle_exception

        self.logger.info("=" * 60)
        self.logger.info("Anwendung erfolgreich gestartet")
        self.logger.info("=" * 60)

        # Zeige Willkommens-Dialog beim ersten Start
        if self.config_manager.get('first_run', True):
            self.root.after(500, self.show_welcome_dialog)

    def _configure_style(self):
        """Konfiguriere TTK-Style"""
        style = ttk.Style()

        # Versuche moderneres Theme zu verwenden
        available_themes = style.theme_names()

        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')

        # Konfiguriere Farben
        style.configure('TButton', padding=6)
        style.configure('TLabel', padding=2)
        style.configure('TFrame', background='#f0f0f0')

    def _initialize_managers(self):
        """Initialisiere alle Manager-Komponenten"""
        try:
            # Config Manager zuerst
            self.config_manager = ConfigManager()
            self.config_manager.load()

            # Database Manager
            db_path = self.config_manager.get('database_path', 'measurements.db')
            self.database_manager = DatabaseManager(db_path)

            # Plugin Manager
            self.plugin_manager = PluginManager()
            plugin_dir = self.config_manager.get('plugin_directory', 'plugins')
            self.plugin_manager.plugin_directory = Path(plugin_dir)

            # Sequence Manager
            self.sequence_manager = SequenceManager(
                self.plugin_manager,
                self.database_manager
            )

            # Lade Plugins
            self.plugin_manager.load_plugins()

            print(f"✓ {len(self.plugin_manager.plugin_classes)} Plugins geladen")

        except Exception as e:
            print(f"✗ Fehler bei der Initialisierung: {e}")
            messagebox.showerror(
                "Initialisierungsfehler",
                f"Die Anwendung konnte nicht initialisiert werden:\n\n{e}\n\n"
                "Bitte überprüfen Sie die Log-Datei für Details."
            )
            raise

    def _ensure_directories(self):
        """Stelle sicher dass alle benötigten Verzeichnisse existieren"""
        directories = [
            'plugins',
            'examples',
            'examples/example_sequences',
            'logs'
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def _set_icon(self):
        """Setze Anwendungs-Icon falls vorhanden"""
        icon_path = Path('icon.ico')
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except:
                pass  # Icon nicht kritisch

    def show_welcome_dialog(self):
        """Zeige Willkommens-Dialog beim ersten Start"""
        welcome_text = """
Willkommen zum Messsequenz-System!

ERSTE SCHRITTE:

1. Beispiel-Sequenz laden:
   Datei → Sequenz öffnen → examples/

2. Neue Sequenz erstellen:
   Datei → Neue Sequenz

3. Plugins durchstöbern:
   Tab "Plugin-Verwaltung"

4. Hilfe anzeigen:
   Hilfe → Dokumentation (F1)

TIPPS:
• Drücken Sie F5 um Plugins zu aktualisieren
• Verwenden Sie Ctrl+S zum Speichern
• Die Datenbank speichert alle Messergebnisse automatisch

Viel Erfolg mit Ihren Messungen!
        """

        dialog = tk.Toplevel(self.root)
        dialog.title("Willkommen")
        dialog.geometry("500x450")
        dialog.transient(self.root)
        dialog.grab_set()

        # Text
        text_frame = ttk.Frame(dialog, padding=20)
        text_frame.pack(fill=tk.BOTH, expand=True)

        text = tk.Text(text_frame, wrap=tk.WORD, height=15)
        scrollbar = ttk.Scrollbar(text_frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.insert('1.0', welcome_text)
        text.configure(state=tk.DISABLED)

        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Checkbox
        show_again_var = tk.BooleanVar(value=True)

        check_frame = ttk.Frame(dialog, padding=(20, 0, 20, 10))
        check_frame.pack(fill=tk.X)

        ttk.Checkbutton(
            check_frame,
            text="Beim nächsten Start wieder anzeigen",
            variable=show_again_var
        ).pack(anchor=tk.W)

        # Button
        def close_welcome():
            self.config_manager.set('first_run', show_again_var.get())
            self.config_manager.save()
            dialog.destroy()

        ttk.Button(
            dialog,
            text="Los geht's!",
            command=close_welcome
        ).pack(pady=10)

        # Zentriere Dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """Behandle unbehandelte Exceptions"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        self.logger.error(
            "Unbehandelte Exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )

        error_msg = f"{exc_type.__name__}: {exc_value}"

        messagebox.showerror(
            "Fehler",
            f"Ein unerwarteter Fehler ist aufgetreten:\n\n{error_msg}\n\n"
            "Details wurden in der Log-Datei gespeichert."
        )

    def on_closing(self):
        """Cleanup beim Schließen der Anwendung"""
        try:
            # Speichere Fenster-Geometrie
            self.main_window.save_window_geometry()

            # Speichere Konfiguration
            self.config_manager.save()

            # Beende laufende Sequenzen
            if self.sequence_manager.is_running():
                response = messagebox.askyesno(
                    "Sequenz läuft",
                    "Eine Messsequenz läuft noch. Trotzdem beenden?"
                )
                if not response:
                    return
                self.sequence_manager.stop()

            # Cleanup Plugins
            self.plugin_manager.cleanup_all()

            # Schließe Datenbankverbindung
            self.database_manager.close()

            self.logger.info("Anwendung wird beendet")
            self.logger.info("=" * 60)

            self.root.destroy()

        except Exception as e:
            self.logger.error(f"Fehler beim Beenden: {e}")
            self.root.destroy()

    def run(self):
        """Starte die Anwendung"""
        # Zentriere Hauptfenster
        self.root.update_idletasks()

        # Hole gespeicherte Geometrie oder zentriere
        geometry = self.config_manager.get('window_geometry', None)
        if not geometry:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()

            window_width = 1400
            window_height = 900

            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2)

            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.root.mainloop()


def check_dependencies():
    """Prüfe ob optionale Abhängigkeiten vorhanden sind"""
    missing = []
    warnings = []

    # Kritische Pakete
    try:
        import tkinter
    except ImportError:
        missing.append('tkinter (Teil von Python)')

    # Optionale Pakete
    optional_packages = {
        'numpy': ('NumPy', 'Statistische Berechnungen eingeschränkt'),
        'matplotlib': ('Matplotlib', 'Datenvisualisierung nicht verfügbar'),
        'PIL': ('Pillow', 'Bildverarbeitung nicht verfügbar'),
        'scipy': ('SciPy', 'Erweiterte Statistik nicht verfügbar')
    }

    for module, (name, warning) in optional_packages.items():
        try:
            __import__(module)
        except ImportError:
            warnings.append(f"{name}: {warning}")

    return missing, warnings


def main():
    """Hauptfunktion"""
    print("=" * 60)
    print("Messsequenz-System v1.0")
    print("=" * 60)
    print()

    # Prüfe Abhängigkeiten
    missing, warnings = check_dependencies()

    if missing:
        print("✗ FEHLER: Folgende kritische Pakete fehlen:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nBitte installieren Sie die fehlenden Pakete.")
        sys.exit(1)

    if warnings:
        print("⚠ Warnung: Einige optionale Pakete fehlen:")
        for warn in warnings:
            print(f"  - {warn}")
        print("\nEinige Funktionen sind möglicherweise eingeschränkt.")
        print("Installieren Sie mit: pip install -r requirements.txt")
        print()

    print("Starte Anwendung...")
    print()

    try:
        app = MeasurementApplication()
        app.run()

    except KeyboardInterrupt:
        print("\n\nAnwendung durch Benutzer beendet.")
        sys.exit(0)

    except Exception as e:
        print(f"\n\n✗ KRITISCHER FEHLER: {e}")
        import traceback
        traceback.print_exc()

        print("\nBitte überprüfen Sie die Log-Datei 'measurement_system.log' für Details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

## 7. Utility-Funktionen (core/utils.py)

```python
"""
Utility-Funktionen für das Messsystem
"""

import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


def export_to_csv(data: List[Dict], filepath: str, include_header: bool = True):
    """
    Exportiere Daten als CSV

    Args:
        data: Liste von Datenpunkten
        filepath: Ziel-Dateipfad
        include_header: Header-Zeile einschließen
    """
    if not data:
        raise ValueError("Keine Daten zum Exportieren")

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        if include_header:
            # Erstelle Header aus dem ersten Datenpunkt
            headers = []
            first_point = data[0]

            # Basis-Felder
            headers.extend(['timestamp', 'point_name'])

            # Parameter
            if 'parameters' in first_point:
                for key in first_point['parameters'].keys():
                    headers.append(f'param_{key}')

            # Messwerte
            if 'values' in first_point:
                for plugin_name, plugin_values in first_point['values'].items():
                    for param_name in plugin_values.keys():
                        headers.append(f'{plugin_name}_{param_name}')

            writer.writerow(headers)

        # Daten
        for point in data:
            row = []
            row.append(point.get('timestamp', ''))
            row.append(point.get('point_name', ''))

            # Parameter
            if 'parameters' in point:
                for value in point['parameters'].values():
                    row.append(value)

            # Messwerte
            if 'values' in point:
                for plugin_values in point['values'].values():
                    for param_data in plugin_values.values():
                        if isinstance(param_data, dict):
                            row.append(param_data.get('value', ''))
                        else:
                            row.append(param_data)

            writer.writerow(row)

    logger.info(f"Daten als CSV exportiert: {filepath}")


def export_to_json(data: Any, filepath: str, pretty: bool = True):
    """
    Exportiere Daten als JSON

    Args:
        data: Zu exportierende Daten
        filepath: Ziel-Dateipfad
        pretty: Formatiert mit Einrückung
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False)

    logger.info(f"Daten als JSON exportiert: {filepath}")


def import_from_json(filepath: str) -> Any:
    """
    Importiere Daten aus JSON

    Args:
        filepath: Quell-Dateipfad

    Returns:
        Geladene Daten
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"Daten aus JSON importiert: {filepath}")
    return data


def format_duration(seconds: float) -> str:
    """
    Formatiere Zeitdauer als lesbaren String

    Args:
        seconds: Sekunden

    Returns:
        Formatierter String (z.B. "2h 15m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"

    minutes = int(seconds // 60)
    secs = int(seconds % 60)

    if minutes < 60:
        return f"{minutes}m {secs}s"

    hours = minutes // 60
    mins = minutes % 60

    return f"{hours}h {mins}m {secs}s"


def format_number(value: float, precision: int = 3, unit: str = "") -> str:
    """
    Formatiere Zahl mit Engineering-Notation

    Args:
        value: Wert
        precision: Nachkommastellen
        unit: Einheit

    Returns:
        Formatierter String
    """
    # Engineering Prefixes
    prefixes = {
        -12: 'p', -9: 'n', -6: 'µ', -3: 'm',
        0: '', 3: 'k', 6: 'M', 9: 'G', 12: 'T'
    }

    if value == 0:
        return f"0 {unit}"

    import math
    exponent = math.floor(math.log10(abs(value)) / 3) * 3
    exponent = max(-12, min(12, exponent))  # Begrenzen

    mantissa = value / (10 ** exponent)
    prefix = prefixes.get(exponent, f'e{exponent}')

    return f"{mantissa:.{precision}f} {prefix}{unit}"


def validate_sequence(sequence_dict: Dict) -> List[str]:
    """
    Validiere Sequenz-Dictionary

    Args:
        sequence_dict: Sequenz als Dictionary

    Returns:
        Liste von Fehlermeldungen (leer wenn gültig)
    """
    errors = []

    # Pflichtfelder
    if 'name' not in sequence_dict or not sequence_dict['name']:
        errors.append("Sequenzname fehlt")

    # Parameterbereiche
    if 'parameter_ranges' in sequence_dict:
        for i, pr in enumerate(sequence_dict['parameter_ranges']):
            if 'parameter_name' not in pr:
                errors.append(f"Parameterbereich {i}: Name fehlt")
            if 'start' not in pr or 'end' not in pr:
                errors.append(f"Parameterbereich {i}: Start/Ende fehlt")
            if 'steps' not in pr or pr['steps'] < 1:
                errors.append(f"Parameterbereich {i}: Ungültige Schrittanzahl")

    # Messpunkte
    if 'measurement_points' in sequence_dict:
        for i, point in enumerate(sequence_dict['measurement_points']):
            if 'name' not in point:
                errors.append(f"Messpunkt {i}: Name fehlt")
            if 'parameters' not in point or not isinstance(point['parameters'], dict):
                errors.append(f"Messpunkt {i}: Ungültige Parameter")

    return errors


def create_backup(filepath: str) -> str:
    """
    Erstelle Backup einer Datei

    Args:
        filepath: Pfad zur Datei

    Returns:
        Pfad zur Backup-Datei
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {filepath}")

    # Erstelle Backup-Namen mit Zeitstempel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.parent / f"{path.stem}_backup_{timestamp}{path.suffix}"

    # Kopiere Datei
    import shutil
    shutil.copy2(filepath, backup_path)

    logger.info(f"Backup erstellt: {backup_path}")
    return str(backup_path)


def clean_old_backups(directory: str, pattern: str = "*_backup_*", keep: int = 5):
    """
    Lösche alte Backup-Dateien

    Args:
        directory: Verzeichnis
        pattern: Datei-Pattern
        keep: Anzahl zu behaltender Backups
    """
    path = Path(directory)
    backups = sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)

    # Lösche alte Backups
    for backup in backups[keep:]:
        backup.unlink()
        logger.info(f"Altes Backup gelöscht: {backup}")


class ProgressTracker:
    """Hilfsklasse für Fortschritts-Tracking"""

    def __init__(self, total: int, callback=None):
        self.total = total
        self.current = 0
        self.callback = callback
        self.start_time = datetime.now()

    def update(self, increment: int = 1):
        """Aktualisiere Fortschritt"""
        self.current += increment

        if self.callback:
            percentage = (self.current / self.total * 100) if self.total > 0 else 0
            elapsed = (datetime.now() - self.start_time).total_seconds()

            # Schätze verbleibende Zeit
            if self.current > 0:
                rate = self.current / elapsed
                remaining = (self.total - self.current) / rate if rate > 0 else 0
            else:
                remaining = 0

            self.callback(self.current, self.total, percentage, elapsed, remaining)

    def reset(self):
        """Setze zurück"""
        self.current = 0
        self.start_time = datetime.now()

    @property
    def percentage(self) -> float:
        """Fortschritt in Prozent"""
        return (self.current / self.total * 100) if self.total > 0 else 0

    @property
    def is_complete(self) -> bool:
        """Prüfe ob abgeschlossen"""
        return self.current >= self.total
```

## 8. Erweitertes Test-Skript (tests/test_complete_system.py)

```python
"""
Vollständiger System-Test
Testet alle Komponenten zusammen
"""

import unittest
import tempfile
import os
import sys
import time
from pathlib import Path

# Pfad anpassen
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.sequence_manager import SequenceManager, MeasurementSequence, ParameterRange
from core.plugin_manager import PluginManager
from core.database_manager import DatabaseManager
from core.config_manager import ConfigManager


class TestCompleteSystem(unittest.TestCase):
    """Vollständiger System-Test"""

    def setUp(self):
        """Setup vor jedem Test"""
        # Temporäre Dateien
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.config_path = os.path.join(self.temp_dir, 'config.json')

        # Manager initialisieren
        self.config_manager = ConfigManager(self.config_path)
        self.database_manager = DatabaseManager(self.db_path)
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()

        self.sequence_manager = SequenceManager(
            self.plugin_manager,
            self.database_manager
        )

    def tearDown(self):
        """Cleanup nach jedem Test"""
        self.database_manager.close()

        # Lösche temporäre Dateien
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_run_simple_sequence(self):
        """Test: Erstelle und führe einfache Sequenz aus"""
        # Erstelle Sequenz
        seq = self.sequence_manager.create_sequence("Test Sequence")

        # Füge Parameterbereich hinzu
        pr = ParameterRange("temperature", 20, 40, 3, "°C")
        seq.add_parameter_range(pr)

        # Generiere Messpunkte
        seq.generate_measurement_points()

        self.assertEqual(len(seq.measurement_points), 3)

        # Wähle Plugins (nur wenn verfügbar)
        available_plugins = self.plugin_manager.get_measurement_plugins()
        if 'TemperatureSensor' in available_plugins:
            seq.active_plugins = ['TemperatureSensor']

            # Callbacks für Tracking
            results = {'completed': False, 'points': 0}

            def on_point(point):
                results['points'] += 1

            def on_complete(sequence):
                results['completed'] = True

            self.sequence_manager.register_callback('on_point_complete', on_point)
            self.sequence_manager.register_callback('on_complete', on_complete)

            # Starte Sequenz
            self.sequence_manager.start_sequence()

            # Warte auf Completion (max 30 Sekunden)
            timeout = 30
            start = time.time()
            while self.sequence_manager.is_running() and (time.time() - start) < timeout:
                time.sleep(0.1)

            # Prüfe Ergebnisse
            self.assertTrue(results['completed'], "Sequenz wurde nicht abgeschlossen")
            self.assertEqual(results['points'], 3, "Nicht alle Punkte wurden gemessen")

            # Prüfe Datenbank
            db_data = self.database_manager.get_sequence_data("Test Sequence")
            self.assertEqual(len(db_data), 3, "Daten nicht in Datenbank")

    def test_save_and_load_sequence(self):
        """Test: Speichere und lade Sequenz"""
        # Erstelle Sequenz
        seq = self.sequence_manager.create_sequence("Save Test", "Description")
        pr1 = ParameterRange("temp", 0, 100, 5, "°C")
        pr2 = ParameterRange("voltage", 0, 10, 3, "V")

        seq.add_parameter_range(pr1)
        seq.add_parameter_range(pr2)
        seq.generate_measurement_points()

        seq.active_plugins = ['TemperatureSensor']
        seq.processing_plugins = ['StatisticsProcessor']

        # Speichere
        save_path = os.path.join(self.temp_dir, 'test_seq.json')
        self.sequence_manager.save_sequence(save_path)

        self.assertTrue(os.path.exists(save_path), "Datei wurde nicht erstellt")

        # Lade in neuen Manager
        new_manager = SequenceManager(self.plugin_manager, self.database_manager)
        loaded_seq = new_manager.load_sequence(save_path)

        # Vergleiche
        self.assertEqual(loaded_seq.name, "Save Test")
        self.assertEqual(loaded_seq.description, "Description")
        self.assertEqual(len(loaded_seq.parameter_ranges), 2)
        self.assertEqual(len(loaded_seq.measurement_points), 15)  # 5 * 3
        self.assertEqual(loaded_seq.active_plugins, ['TemperatureSensor'])
        self.assertEqual(loaded_seq.processing_plugins, ['StatisticsProcessor'])

    def test_plugin_loading(self):
        """Test: Plugin-Loading"""
        plugins = self.plugin_manager.get_available_plugins()

        self.assertGreater(len(plugins), 0, "Keine Plugins geladen")

        # Prüfe ob Standard-Plugins vorhanden
        plugin_names = list(plugins.keys())

        # Mindestens einige Plugins sollten verfügbar sein
        expected_plugins = ['TemperatureSensor', 'ElectricalMeter', 'StatisticsProcessor']
        found = [p for p in expected_plugins if p in plugin_names]

        self.assertGreater(len(found), 0, f"Standard-Plugins nicht gefunden. Verfügbar: {plugin_names}")

    def test_database_operations(self):
        """Test: Datenbank-Operationen"""
        # Speichere Testdaten
        self.database_manager.save_measurement(
            sequence_name="DB Test",
            point_name="Point 1",
            timestamp="2024-01-01T12:00:00",
            parameters={'temp': 25.0},
            results={
                'sensor1': {
                    'value1': 42.0,
                    'value2': 3.14,
                    'unit_info': {'value1': 'V', 'value2': 'A'}
                }
            }
        )

        # Lade Daten
        data = self.database_manager.get_sequence_data("DB Test")

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['point_name'], "Point 1")
        self.assertIn('sensor1', data[0]['values'])

        # Prüfe Sequenz-Liste
        sequences = self.database_manager.get_all_sequences()
        self.assertIn("DB Test", sequences)

        # Lösche Sequenz
        self.database_manager.delete_sequence("DB Test")
        sequences = self.database_manager.get_all_sequences()
        self.assertNotIn("DB Test", sequences)

    def test_config_manager(self):
        """Test: Konfigurations-Manager"""
        # Setze Werte
        self.config_manager.set('test_key', 'test_value')
        self.config_manager.set('test_number', 42)

        # Speichere
        self.config_manager.save()

        # Lade in neue Instanz
        new_config = ConfigManager(self.config_path)
        new_config.load()

        # Prüfe Werte
        self.assertEqual(new_config.get('test_key'), 'test_value')
        self.assertEqual(new_config.get('test_number'), 42)

    def test_delay_plugin(self):
        """Test: Delay-Plugin (nicht-blockierend)"""
        available = self.plugin_manager.get_measurement_plugins()

        if 'DelayPlugin' not in available:
            self.skipTest("DelayPlugin nicht verfügbar")

        # Erstelle Sequenz mit Delay
        seq = self.sequence_manager.create_sequence("Delay Test")
        pr = ParameterRange("delay", 0.1, 0.3, 3, "s")
        seq.add_parameter_range(pr)
        seq.generate_measurement_points()
        seq.active_plugins = ['DelayPlugin']

        # Starte
        start_time = time.time()

        completed = {'flag': False}
        def on_complete(s):
            completed['flag'] = True

        self.sequence_manager.register_callback('on_complete', on_complete)
        self.sequence_manager.start_sequence()

        # Warte
        timeout = 10
        while self.sequence_manager.is_running() and (time.time() - start_time) < timeout:
            time.sleep(0.05)

        elapsed = time.time() - start_time

        # Prüfe
        self.assertTrue(completed['flag'], "Delay-Sequenz nicht abgeschlossen")

        # Gesamtzeit sollte ca. 0.1 + 0.2 + 0.3 = 0.6s sein (plus Overhead)
        self.assertLess(elapsed, 2.0, "Delay zu lang")


class TestPluginSystem(unittest.TestCase):
    """Tests für Plugin-System"""

    def setUp(self):
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()

    def test_plugin_types(self):
        """Test: Plugin-Typen werden korrekt erkannt"""
        meas_plugins = self.plugin_manager.get_measurement_plugins()
        proc_plugins = self.plugin_manager.get_processing_plugins()

        # Listen sollten disjunkt sein
        overlap = set(meas_plugins) & set(proc_plugins)
        self.assertEqual(len(overlap), 0, "Plugins in beiden Kategorien")

    def test_plugin_instantiation(self):
        """Test: Plugins können instanziiert werden"""
        available = self.plugin_manager.get_available_plugins()

        for plugin_name in available.keys():
            try:
                plugin = self.plugin_manager.get_plugin(plugin_name)
                self.assertIsNotNone(plugin, f"Plugin {plugin_name} konnte nicht instanziiert werden")

                # Test initialize/cleanup
                result = plugin.initialize()
                self.assertTrue(result, f"Plugin {plugin_name} Initialisierung fehlgeschlagen")

                plugin.cleanup()

            except Exception as e:
                self.fail(f"Plugin {plugin_name} verursachte Exception: {e}")


def run_tests():
    """Führe alle Tests aus"""
    # Test-Suite erstellen
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Füge Tests hinzu
    suite.addTests(loader.loadTestsFromTestCase(TestCompleteSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestPluginSystem))

    # Führe aus
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
```

## 9. Erweiterte Installationsanleitung (INSTALL.md)

```markdown
# Installationsanleitung

## Systemanforderungen

### Minimal
- Python 3.8 oder höher
- 100 MB freier Festplattenspeicher
- 512 MB RAM

### Empfohlen
- Python 3.10 oder höher
- 500 MB freier Festplattenspeicher
- 2 GB RAM
- Bildschirmauflösung: 1280x720 oder höher

## Installation

### Option 1: Schnellinstallation (Windows)

1. **Python installieren** (falls nicht vorhanden)
   - Download: https://www.python.org/downloads/
   - Bei Installation "Add Python to PATH" aktivieren

2. **Projekt herunterladen**
   ```bash
   # Mit Git
   git clone https://github.com/yourusername/measurement-sequence-system.git
   cd measurement-sequence-system

   # ODER: ZIP herunterladen und entpacken
   ```

3. **Installation ausführen**
   ```bash
   # Doppelklick auf: install.bat
   # ODER in Kommandozeile:
   install.bat
   ```

4. **Anwendung starten**
   ```bash
   # Doppelklick auf: run.bat
   # ODER in Kommandozeile:
   run.bat
   ```

### Option 2: Manuelle Installation (alle Betriebssysteme)

1. **Python installieren**
   - Siehe oben oder Paketmanager Ihres Systems

2. **Projekt herunterladen**
   ```bash
   git clone https://github.com/yourusername/measurement-sequence-system.git
   cd measurement-sequence-system
   ```

3. **Virtuelle Umgebung erstellen** (empfohlen)
   ```bash
   python -m venv venv

   # Aktivieren:
   # Windows:
   venv\Scripts\activate

   # Linux/macOS:
   source venv/bin/activate
   ```

4. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```

5. **Anwendung starten**
   ```bash
   python main.py
   ```

### Option 3: Entwickler-Installation

```bash
# Mit editierbarer Installation
pip install -e .

# Zusätzliche Entwickler-Tools
pip install pytest pytest-cov black flake8
```

## Installations-Skripte

### install.bat (Windows)

```batch
@echo off
echo ========================================
echo Messsequenz-System - Installation
echo ========================================
echo.

REM Prüfe Python
python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden!
    echo Bitte installieren Sie Python von https://www.python.org
    pause
    exit /b 1
)

echo Python gefunden.
echo.

REM Erstelle virtuelle Umgebung
echo Erstelle virtuelle Umgebung...
python -m venv venv
if errorlevel 1 (
    echo FEHLER: Virtuelle Umgebung konnte nicht erstellt werden
    pause
    exit /b 1
)

echo Aktiviere virtuelle Umgebung...
call venv\Scripts\activate.bat

echo Installiere Abhängigkeiten...
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo WARNUNG: Einige Pakete konnten nicht installiert werden
    echo Die Anwendung funktioniert möglicherweise eingeschränkt
)

echo.
echo ========================================
echo Installation abgeschlossen!
echo ========================================
echo.
echo Starten Sie die Anwendung mit: run.bat
echo.
pause
```

### run.bat (Windows)

```batch
@echo off
echo Starte Messsequenz-System...
echo.

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python main.py

if errorlevel 1 (
    echo.
    echo FEHLER beim Starten der Anwendung
    echo Siehe measurement_system.log für Details
    pause
)
```

### install.sh (Linux/macOS)

```bash
#!/bin/bash

echo "========================================"
echo "Messsequenz-System - Installation"
echo "========================================"
echo

# Prüfe Python
if ! command -v python3 &> /dev/null; then
    echo "FEHLER: Python 3 nicht gefunden!"
    echo "Bitte installieren Sie Python 3.8 oder höher"
    exit 1
fi

echo "Python gefunden: $(python3 --version)"
echo

# Erstelle virtuelle Umgebung
echo "Erstelle virtuelle Umgebung..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "FEHLER: Virtuelle Umgebung konnte nicht erstellt werden"
    exit 1
fi

echo "Aktiviere virtuelle Umgebung..."
source venv/bin/activate

echo "Installiere Abhängigkeiten..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "WARNUNG: Einige Pakete konnten nicht installiert werden"
    echo "Die Anwendung funktioniert möglicherweise eingeschränkt"
fi

echo
echo "========================================"
echo "Installation abgeschlossen!"
echo "========================================"
echo
echo "Starten Sie die Anwendung mit: ./run.sh"
echo

# Mache run.sh ausführbar
chmod +x run.sh
```

### run.sh (Linux/macOS)

```bash
#!/bin/bash

echo "Starte Messsequenz-System..."
echo

if [ -f venv/bin/activate ]; then
    source venv/bin/activate
fi

python3 main.py

if [ $? -ne 0 ]; then
    echo
    echo "FEHLER beim Starten der Anwendung"
    echo "Siehe measurement_system.log für Details"
    read -p "Drücken Sie Enter zum Beenden..."
fi
```

## Fehlerbehebung

### Problem: "tkinter not found"

**Lösung (Ubuntu/Debian):**
```bash
sudo apt-get install python3-tk
```

**Lösung (Fedora):**
```bash
sudo dnf install python3-tkinter
```

**Lösung (macOS):**
```bash
# Tkinter sollte mit Python mitgeliefert werden
# Falls nicht, Python über Homebrew neu installieren:
brew install python-tk
```

### Problem: "pip not found"

**Lösung:**
```bash
python -m ensurepip --upgrade
```

### Problem: Matplotlib zeigt keine Plots

**Lösung (Linux):**
```bash
sudo apt-get install python3-matplotlib
# oder
pip install --upgrade matplotlib
```

### Problem: Berechtigungsfehler beim Schreiben

**Lösung:**
- Starten Sie die Anwendung mit Administrator-/Root-Rechten ODER
- Verschieben Sie das Projekt in ein Verzeichnis mit Schreibrechten

## Deinstallation

```bash
# Lösche virtuelle Umgebung
rm -rf venv  # Linux/macOS
# oder
rmdir /s venv  # Windows

# Lösche Datenbank und Logs (optional)
rm measurements.db measurement_system.log config.json
```

## Nächste Schritte

Nach erfolgreicher Installation:

1. Starten Sie die Anwendung
2. Lesen Sie die Hilfe (F1)
3. Öffnen Sie eine Beispiel-Sequenz
4. Erstellen Sie Ihre erste eigene Sequenz

Weitere Informationen in der [README.md](README.md)
```

## 10. Batch/Shell Skripte wie oben beschrieben erstellen

Erstellen Sie die Dateien direkt im Hauptverzeichnis:
- `install.bat`
- `run.bat`
- `install.sh`
- `run.sh`

---

**Die Software ist nun vollständig implementiert mit:**

✅ **Vollständiger GUI** mit allen Funktionen
✅ **Plugin-Auswahl** mit Checkboxen und Info-Buttons
✅ **Nicht-blockierendes Delay-Plugin**
✅ **Einstellungs-Dialog**
✅ **Datenbank-Export**
✅ **Beispiel-Sequenzen**
✅ **Vollständige Tests**
✅ **Installations-Skripte**
✅ **Utility-Funktionen**
✅ **Umfangreiche Dokumentation**

Sie können die Software jetzt direkt nutzen oder weiter anpassen!
