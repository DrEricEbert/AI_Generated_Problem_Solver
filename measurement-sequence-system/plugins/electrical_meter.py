"""
Elektrisches Messgerät - VOLLSTÄNDIG MIT PARAMETERN
"""

import random
import time
import logging
import math
from core.plugin_manager import MeasurementPlugin

logger = logging.getLogger(__name__)


class ElectricalMeter(MeasurementPlugin):
    """Simuliertes elektrisches Messgerät mit Parametern"""

    def __init__(self):
        super().__init__()
        self.name = "ElectricalMeter"
        self.version = "2.0"
        self.description = "Simuliertes Multimeter fuer elektrische Messungen mit konfigurierbaren Parametern"

        # Parameter-Definitionen
        self._parameter_definitions = {
            'voltage_noise': {
                'type': 'float',
                'default': 0.001,
                'min': 0.0,
                'max': 1.0,
                'increment': 0.001,
                'unit': 'V',
                'description': 'Rauschpegel der Spannungsmessung'
            },
            'current_noise': {
                'type': 'float',
                'default': 0.0001,
                'min': 0.0,
                'max': 0.1,
                'increment': 0.0001,
                'unit': 'A',
                'description': 'Rauschpegel der Strommessung'
            },
            'measurement_delay': {
                'type': 'float',
                'default': 0.08,
                'min': 0.0,
                'max': 1.0,
                'increment': 0.01,
                'unit': 's',
                'description': 'Verzoegerung bei der Messung'
            },
            'enable_power': {
                'type': 'bool',
                'default': True,
                'description': 'Leistungsmessung aktivieren'
            },
            'enable_resistance': {
                'type': 'bool',
                'default': True,
                'description': 'Widerstandsmessung aktivieren'
            },
            'digits': {
                'type': 'int',
                'default': 4,
                'min': 1,
                'max': 8,
                'description': 'Anzahl der Nachkommastellen'
            },
            'measurement_mode': {
                'type': 'choice',
                'default': 'DC',
                'choices': ['DC', 'AC', 'DC+AC'],
                'description': 'Messart (Gleich-/Wechselstrom)'
            }
        }

        # Setze Standardwerte
        for param_name, param_def in self._parameter_definitions.items():
            self.parameters[param_name] = param_def['default']

        self.voltage = 0.0
        self.current = 0.0
        self.resistance = 1000.0
        self.connected = False

    def initialize(self):
        """Initialisiere Messgerät"""
        try:
            logger.info(f"{self.name}: Initialisierung gestartet")
            logger.info(f"{self.name}: Modus: {self.get_parameter_value('measurement_mode')}")

            delay = self.get_parameter_value('measurement_delay', 0.08)
            time.sleep(delay)

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
            logger.info(f"{self.name}: Widerstand gesetzt auf {self.resistance}Ohm")

        # Simuliere Einstellzeit
        time.sleep(0.05)

    def measure(self) -> dict:
        """Führe elektrische Messung durch"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Messgeraet nicht initialisiert")

        # Hole konfigurierte Parameter
        voltage_noise = self.get_parameter_value('voltage_noise', 0.001)
        current_noise = self.get_parameter_value('current_noise', 0.0001)
        enable_power = self.get_parameter_value('enable_power', True)
        enable_resistance = self.get_parameter_value('enable_resistance', True)
        digits = self.get_parameter_value('digits', 4)
        mode = self.get_parameter_value('measurement_mode', 'DC')

        # Simuliere Messung mit Rauschen
        noise_v = random.gauss(0, voltage_noise)
        noise_i = random.gauss(0, current_noise)

        measured_voltage = self.voltage + noise_v
        measured_current = self.current + noise_i

        # AC-Komponente wenn gewählt
        if mode in ['AC', 'DC+AC']:
            ac_freq = 50  # Hz
            ac_amplitude_v = self.voltage * 0.01  # 1% AC
            ac_amplitude_i = self.current * 0.01

            phase = random.random() * 2 * math.pi
            ac_v = ac_amplitude_v * math.sin(phase)
            ac_i = ac_amplitude_i * math.sin(phase)

            if mode == 'AC':
                measured_voltage = ac_v
                measured_current = ac_i
            else:  # DC+AC
                measured_voltage += ac_v
                measured_current += ac_i

        result = {
            'voltage': round(measured_voltage, digits),
            'current': round(measured_current, digits),
            'measurement_mode': mode,
            'unit_info': {
                'voltage': 'V',
                'current': 'A',
                'measurement_mode': ''
            }
        }

        # Leistung wenn aktiviert
        if enable_power:
            power = measured_voltage * measured_current
            result['power'] = round(power, digits)
            result['unit_info']['power'] = 'W'

        # Widerstand wenn aktiviert
        if enable_resistance:
            if abs(measured_current) > 0.001:
                calculated_resistance = measured_voltage / measured_current
            else:
                calculated_resistance = self.resistance + random.gauss(0, 1)

            result['resistance'] = round(calculated_resistance, digits)
            result['unit_info']['resistance'] = 'Ohm'

        # Simuliere Messverzögerung
        delay = self.get_parameter_value('measurement_delay', 0.08)
        time.sleep(delay)

        logger.debug(f"{self.name}: U={measured_voltage:.3f}V, I={measured_current:.4f}A")
        return result

    def get_units(self) -> dict:
        """Gibt Einheiten zurück"""
        units = {
            'voltage': 'V',
            'current': 'A',
            'measurement_mode': ''
        }

        if self.get_parameter_value('enable_power', True):
            units['power'] = 'W'

        if self.get_parameter_value('enable_resistance', True):
            units['resistance'] = 'Ohm'

        return units


class PowerSupply(MeasurementPlugin):
    """Programmierbare Spannungsquelle mit Parametern"""

    def __init__(self):
        super().__init__()
        self.name = "PowerSupply"
        self.version = "2.0"
        self.description = "Programmierbare Spannungsquelle mit Strombegrenzung und Parametern"

        # Parameter-Definitionen
        self._parameter_definitions = {
            'max_voltage': {
                'type': 'float',
                'default': 30.0,
                'min': 1.0,
                'max': 100.0,
                'increment': 1.0,
                'unit': 'V',
                'description': 'Maximale Ausgangsspannung'
            },
            'max_current': {
                'type': 'float',
                'default': 3.0,
                'min': 0.1,
                'max': 10.0,
                'increment': 0.1,
                'unit': 'A',
                'description': 'Maximaler Ausgangsstrom'
            },
            'voltage_stability': {
                'type': 'float',
                'default': 0.01,
                'min': 0.001,
                'max': 1.0,
                'increment': 0.001,
                'unit': '%',
                'description': 'Spannungsstabilitaet (Genauigkeit)'
            },
            'ramp_time': {
                'type': 'float',
                'default': 0.1,
                'min': 0.0,
                'max': 5.0,
                'increment': 0.1,
                'unit': 's',
                'description': 'Rampenzeit beim Spannungswechsel'
            },
            'enable_ovp': {
                'type': 'bool',
                'default': True,
                'description': 'Ueberspannungsschutz aktivieren'
            },
            'enable_ocp': {
                'type': 'bool',
                'default': True,
                'description': 'Ueberstromschutz aktivieren'
            },
            'output_resistance': {
                'type': 'float',
                'default': 10.0,
                'min': 0.1,
                'max': 1000.0,
                'increment': 0.1,
                'unit': 'Ohm',
                'description': 'Simulierte Last am Ausgang'
            }
        }

        # Setze Standardwerte
        for param_name, param_def in self._parameter_definitions.items():
            self.parameters[param_name] = param_def['default']

        self.set_voltage = 0.0
        self.set_current_limit = 1.0
        self.output_enabled = False

        self.actual_voltage = 0.0
        self.actual_current = 0.0
        self.connected = False

    def initialize(self):
        """Initialisiere Spannungsquelle"""
        logger.info(f"{self.name}: Initialisierung")
        logger.info(f"{self.name}: Max Voltage: {self.get_parameter_value('max_voltage')}V")
        logger.info(f"{self.name}: Max Current: {self.get_parameter_value('max_current')}A")

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
        max_voltage = self.get_parameter_value('max_voltage', 30.0)
        max_current = self.get_parameter_value('max_current', 3.0)

        if 'voltage' in parameters:
            self.set_voltage = max(0, min(max_voltage, parameters['voltage']))
            logger.info(f"{self.name}: Ausgangsspannung gesetzt auf {self.set_voltage}V")

        if 'current_limit' in parameters:
            self.set_current_limit = max(0, min(max_current, parameters['current_limit']))
            logger.info(f"{self.name}: Strombegrenzung gesetzt auf {self.set_current_limit}A")

        if 'output_enable' in parameters:
            self.output_enabled = bool(parameters['output_enable'])
            logger.info(f"{self.name}: Ausgang {'aktiviert' if self.output_enabled else 'deaktiviert'}")

        # Simuliere Rampenzeit
        ramp_time = self.get_parameter_value('ramp_time', 0.1)
        time.sleep(ramp_time)

        # Simuliere Spannungsrampe
        if self.output_enabled:
            stability = self.get_parameter_value('voltage_stability', 0.01)
            noise = random.gauss(0, self.set_voltage * stability / 100)

            self.actual_voltage = self.set_voltage * 0.9 + noise

            # Simuliere Last
            output_resistance = self.get_parameter_value('output_resistance', 10.0)
            self.actual_current = self.actual_voltage / output_resistance

            # Strombegrenzung
            self.actual_current = min(self.actual_current, self.set_current_limit)

            # Bei Strombegrenzung fällt Spannung
            if self.actual_current >= self.set_current_limit * 0.99:
                self.actual_voltage = self.actual_current * output_resistance
        else:
            self.actual_voltage = 0.0
            self.actual_current = 0.0

    def measure(self) -> dict:
        """Messe Ausgangswerte"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Spannungsquelle nicht initialisiert")

        # Simuliere kleine Schwankungen
        stability = self.get_parameter_value('voltage_stability', 0.01)
        voltage_noise = random.gauss(0, self.actual_voltage * stability / 100)
        current_noise = random.gauss(0, self.actual_current * stability / 100)

        voltage = self.actual_voltage + voltage_noise
        current = self.actual_current + current_noise

        # Berechne Leistung
        power = voltage * current

        # Status-Flags
        cv_mode = abs(voltage - self.set_voltage) < self.set_voltage * 0.1  # Constant Voltage
        cc_mode = abs(current - self.set_current_limit) < self.set_current_limit * 0.05  # Constant Current

        # Überspannungs-/Überstromschutz
        enable_ovp = self.get_parameter_value('enable_ovp', True)
        enable_ocp = self.get_parameter_value('enable_ocp', True)
        max_voltage = self.get_parameter_value('max_voltage', 30.0)
        max_current = self.get_parameter_value('max_current', 3.0)

        ovp_triggered = enable_ovp and voltage > max_voltage
        ocp_triggered = enable_ocp and current > max_current

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
            'ovp_triggered': 1 if ovp_triggered else 0,
            'ocp_triggered': 1 if ocp_triggered else 0,
            'unit_info': {
                'output_voltage': 'V',
                'output_current': 'A',
                'output_power': 'W',
                'set_voltage': 'V',
                'current_limit': 'A',
                'cv_mode': '',
                'cc_mode': '',
                'output_enabled': '',
                'ovp_triggered': '',
                'ocp_triggered': ''
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
