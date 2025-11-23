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
