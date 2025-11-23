"""
Statistik-Verarbeitungs-Plugin - VOLLSTÄNDIG MIT PARAMETERN
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
    logger.warning("NumPy nicht verfuegbar - Statistik eingeschraenkt")


class StatisticsProcessor(ProcessingPlugin):
    """Statistik-Verarbeitungs-Plugin mit Parametern"""

    def __init__(self):
        super().__init__()
        self.name = "StatisticsProcessor"
        self.version = "3.0"
        self.description = "Berechnet statistische Kennwerte fuer jeden Messwert einzeln mit Parametern"

        # Parameter-Definitionen
        self._parameter_definitions = {
            'window_size': {
                'type': 'int',
                'default': 10,
                'min': 2,
                'max': 100,
                'description': 'Fenstergroesse fuer gleitende Statistiken'
            },
            'enable_percentiles': {
                'type': 'bool',
                'default': True,
                'description': 'Perzentile berechnen (25%, 75%)'
            },
            'enable_moving_avg': {
                'type': 'bool',
                'default': True,
                'description': 'Gleitenden Durchschnitt berechnen'
            },
            'enable_trend': {
                'type': 'bool',
                'default': True,
                'description': 'Trend-Erkennung aktivieren'
            },
            'trend_threshold': {
                'type': 'float',
                'default': 0.1,
                'min': 0.01,
                'max': 1.0,
                'increment': 0.01,
                'description': 'Schwellwert fuer Trend-Erkennung (als Anteil der Std.abw.)'
            },
            'max_history': {
                'type': 'int',
                'default': 1000,
                'min': 10,
                'max': 10000,
                'description': 'Maximale Anzahl gespeicherter Historie-Werte'
            },
            'decimal_places': {
                'type': 'int',
                'default': 6,
                'min': 1,
                'max': 10,
                'description': 'Anzahl Nachkommastellen in Ergebnissen'
            },
            'enable_global_stats': {
                'type': 'bool',
                'default': True,
                'description': 'Globale Statistiken ueber alle Messwerte'
            }
        }

        # Setze Standardwerte
        for param_name, param_def in self._parameter_definitions.items():
            self.parameters[param_name] = param_def['default']

        self.history = {}

    def initialize(self):
        """Initialisiere Prozessor"""
        logger.info(f"{self.name}: Initialisierung")
        logger.info(f"{self.name}: Window Size: {self.get_parameter_value('window_size')}")
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
        return ['numerical_values']

    def process(self, data: dict) -> dict:
        """Verarbeite Daten und berechne Statistiken"""
        if not self.is_initialized:
            self.initialize()

        result = {}

        # Extrahiere alle Messwerte strukturiert
        measurements = self._extract_measurements(data)

        if not measurements:
            logger.warning(f"{self.name}: Keine Messwerte gefunden")
            return result

        # Berechne Statistiken für jeden Messwert einzeln
        for measurement_key, values in measurements.items():
            if not values:
                continue

            # Statistiken für diesen Messwert
            stats = self._calculate_statistics(values, measurement_key)

            # Füge zum Ergebnis hinzu mit Präfix
            for stat_name, stat_value in stats.items():
                result[f"{measurement_key}_{stat_name}"] = stat_value

        # Globale Statistiken wenn aktiviert
        if self.get_parameter_value('enable_global_stats', True):
            all_values = []
            for values in measurements.values():
                all_values.extend(values)

            if all_values:
                decimal_places = self.get_parameter_value('decimal_places', 6)
                result['global_mean'] = round(sum(all_values) / len(all_values), decimal_places)
                result['global_min'] = round(min(all_values), decimal_places)
                result['global_max'] = round(max(all_values), decimal_places)

        logger.debug(f"{self.name}: Statistiken berechnet fuer {len(measurements)} Messwerte")
        return result

    def _extract_measurements(self, data: dict) -> dict:
        """Extrahiere Messwerte strukturiert"""
        measurements = {}

        for plugin_name, plugin_data in data.items():
            if not isinstance(plugin_data, dict):
                continue

            for param_name, param_value in plugin_data.items():
                if param_name == 'unit_info':
                    continue

                key = f"{plugin_name}.{param_name}"

                if isinstance(param_value, (int, float)) and not isinstance(param_value, bool):
                    if key not in measurements:
                        measurements[key] = []
                    measurements[key].append(float(param_value))

        return measurements

    def _calculate_statistics(self, values: list, measurement_key: str) -> dict:
        """Berechne Statistiken für eine Liste von Werten"""
        stats = {}

        if not values:
            return stats

        decimal_places = self.get_parameter_value('decimal_places', 6)

        # Basis-Statistiken
        if NUMPY_AVAILABLE:
            values_array = np.array(values)

            stats['mean'] = float(np.mean(values_array))
            stats['std'] = float(np.std(values_array))
            stats['min'] = float(np.min(values_array))
            stats['max'] = float(np.max(values_array))
            stats['median'] = float(np.median(values_array))
            stats['variance'] = float(np.var(values_array))

            # Percentile wenn aktiviert
            if self.get_parameter_value('enable_percentiles', True) and len(values) >= 4:
                stats['p25'] = float(np.percentile(values_array, 25))
                stats['p75'] = float(np.percentile(values_array, 75))
        else:
            # Fallback ohne NumPy
            stats['mean'] = sum(values) / len(values)
            stats['min'] = min(values)
            stats['max'] = max(values)

            mean = stats['mean']
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            stats['std'] = math.sqrt(variance)
            stats['variance'] = variance

            sorted_values = sorted(values)
            n = len(sorted_values)
            if n % 2 == 0:
                stats['median'] = (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
            else:
                stats['median'] = sorted_values[n//2]

        # Zusätzliche Kennwerte
        stats['count'] = len(values)
        stats['range'] = stats['max'] - stats['min']

        if stats['mean'] != 0:
            stats['cv'] = (stats['std'] / stats['mean'] * 100)
        else:
            stats['cv'] = 0

        stats['current'] = values[-1]

        # Aktualisiere Historie
        self._update_history(measurement_key, values[-1])

        # Gleitender Durchschnitt wenn aktiviert
        if self.get_parameter_value('enable_moving_avg', True):
            window_size = self.get_parameter_value('window_size', 10)

            if measurement_key in self.history:
                recent_values = self.history[measurement_key][-window_size:]
                stats['moving_avg'] = sum(recent_values) / len(recent_values)

                # Trend wenn aktiviert
                if self.get_parameter_value('enable_trend', True) and len(recent_values) >= 2:
                    trend = recent_values[-1] - recent_values[0]
                    stats['trend'] = trend

                    threshold = self.get_parameter_value('trend_threshold', 0.1)

                    if abs(trend) < stats['std'] * threshold:
                        stats['trend_direction'] = 'stable'
                    elif trend > 0:
                        stats['trend_direction'] = 'increasing'
                    else:
                        stats['trend_direction'] = 'decreasing'

        # Runde Ergebnisse
        for key in stats:
            if isinstance(stats[key], float):
                stats[key] = round(stats[key], decimal_places)

        return stats

    def _update_history(self, key: str, value: float):
        """Aktualisiere Verlaufs-Historie"""
        if key not in self.history:
            self.history[key] = []

        self.history[key].append(value)

        # Begrenze Historie-Größe
        max_history = self.get_parameter_value('max_history', 1000)
        if len(self.history[key]) > max_history:
            self.history[key] = self.history[key][-max_history:]
