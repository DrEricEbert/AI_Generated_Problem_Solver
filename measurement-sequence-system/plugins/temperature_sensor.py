"""
Beispiel-Plugin: Temperatur-Sensor - MIT PARAMETERN
"""

import random
import time
import logging
from core.plugin_manager import MeasurementPlugin

logger = logging.getLogger(__name__)


class TemperatureSensor(MeasurementPlugin):
    """Simulierter Temperatursensor mit konfigurierbaren Parametern"""

    def __init__(self):
        super().__init__()
        self.name = "TemperatureSensor"
        self.version = "2.0"
        self.description = "Simulierter Temperatursensor mit PT100-Charakteristik und konfigurierbaren Parametern"

        # Parameter-Definitionen
        self._parameter_definitions = {
            'noise_level': {
                'type': 'float',
                'default': 0.1,
                'min': 0.0,
                'max': 5.0,
                'increment': 0.1,
                'unit': '°C',
                'description': 'Rauschpegel der Temperaturmessung'
            },
            'response_time': {
                'type': 'float',
                'default': 0.3,
                'min': 0.0,
                'max': 1.0,
                'increment': 0.05,
                'unit': 's',
                'description': 'Thermische Zeitkonstante (Ansprechzeit)'
            },
            'pt100_enabled': {
                'type': 'bool',
                'default': True,
                'description': 'PT100-Widerstandsmessung aktivieren'
            },
            'sensor_type': {
                'type': 'choice',
                'default': 'PT100',
                'choices': ['PT100', 'PT1000', 'Thermoelement K', 'NTC'],
                'description': 'Typ des Temperatursensors'
            },
            'offset': {
                'type': 'float',
                'default': 0.0,
                'min': -10.0,
                'max': 10.0,
                'increment': 0.1,
                'unit': '°C',
                'description': 'Temperatur-Offset (Kalibrierung)'
            },
            'settling_steps': {
                'type': 'int',
                'default': 3,
                'min': 1,
                'max': 10,
                'description': 'Anzahl der Schritte zur Temperatur-Stabilisierung'
            }
        }

        # Setze Standardwerte
        for param_name, param_def in self._parameter_definitions.items():
            self.parameters[param_name] = param_def['default']

        self.current_temperature = 25.0
        self.target_temperature = 25.0
        self.connected = False

    def initialize(self):
        """Initialisiere Sensor"""
        try:
            logger.info(f"{self.name}: Initialisierung gestartet")
            logger.info(f"{self.name}: Parameter: {self.parameters}")

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
        """Setze Messparameter"""
        if 'temperature' in parameters:
            self.target_temperature = parameters['temperature']
            logger.info(f"{self.name}: Zieltemperatur gesetzt auf {self.target_temperature}°C")

        if 'setpoint' in parameters:
            self.target_temperature = parameters['setpoint']
            logger.info(f"{self.name}: Zieltemperatur gesetzt auf {self.target_temperature}°C")

        # Simuliere Temperaturänderung
        self._simulate_temperature_change()

    def _simulate_temperature_change(self):
        """Simuliere Temperaturänderung mit konfigurierbarer Ansprechzeit"""
        response_time = self.get_parameter_value('response_time', 0.3)
        settling_steps = self.get_parameter_value('settling_steps', 3)

        # Mehrere Schritte zur Stabilisierung
        for _ in range(settling_steps):
            diff = self.target_temperature - self.current_temperature
            self.current_temperature += diff * response_time
            time.sleep(response_time / settling_steps)

    def measure(self) -> dict:
        """Führe Temperaturmessung durch"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Sensor nicht initialisiert")

        # Hole konfigurierte Parameter
        noise_level = self.get_parameter_value('noise_level', 0.1)
        pt100_enabled = self.get_parameter_value('pt100_enabled', True)
        sensor_type = self.get_parameter_value('sensor_type', 'PT100')
        offset = self.get_parameter_value('offset', 0.0)

        # Simuliere Messung mit Rauschen
        noise = random.gauss(0, noise_level)
        measured_temp = self.current_temperature + noise + offset

        result = {
            'temperature': round(measured_temp, 2),
            'target_temperature': self.target_temperature,
            'sensor_type': sensor_type,
            'unit_info': {
                'temperature': '°C',
                'target_temperature': '°C',
                'sensor_type': ''
            }
        }

        # PT100-Widerstand wenn aktiviert
        if pt100_enabled:
            if sensor_type == 'PT100':
                # R = R0 * (1 + A*T + B*T²)
                resistance = 100.0 + 0.385 * measured_temp
                resistance += random.gauss(0, noise_level * 0.01)
            elif sensor_type == 'PT1000':
                resistance = 1000.0 + 3.85 * measured_temp
                resistance += random.gauss(0, noise_level * 0.1)
            else:
                resistance = 0.0

            result['resistance'] = round(resistance, 3)
            result['unit_info']['resistance'] = 'Ohm'

        # Simuliere Messverzögerung
        time.sleep(0.05)

        logger.debug(f"{self.name}: Messung: {measured_temp:.2f}°C")
        return result

    def get_units(self) -> dict:
        """Gibt Einheiten zurück"""
        units = {
            'temperature': '°C',
            'target_temperature': '°C',
            'sensor_type': ''
        }

        if self.get_parameter_value('pt100_enabled', True):
            units['resistance'] = 'Ohm'

        return units
