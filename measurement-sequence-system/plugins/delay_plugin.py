"""
Delay/Wait Plugin - VOLLSTÄNDIG MIT PARAMETERN
"""

import time
import threading
import logging
from core.plugin_manager import MeasurementPlugin

logger = logging.getLogger(__name__)


class DelayPlugin(MeasurementPlugin):
    """Nicht-blockierendes Warte-Plugin mit Parametern"""

    def __init__(self):
        super().__init__()
        self.name = "DelayPlugin"
        self.version = "2.0"
        self.description = "Nicht-blockierendes Warte-Plugin fuer Zeitverzoegerungen mit Parametern"

        # Parameter-Definitionen
        self._parameter_definitions = {
            'default_delay': {
                'type': 'float',
                'default': 1.0,
                'min': 0.0,
                'max': 300.0,
                'increment': 0.1,
                'unit': 's',
                'description': 'Standard-Verzoegerungszeit'
            },
            'use_threading': {
                'type': 'bool',
                'default': True,
                'description': 'Threading fuer lange Delays verwenden'
            },
            'threading_threshold': {
                'type': 'float',
                'default': 2.0,
                'min': 0.5,
                'max': 10.0,
                'increment': 0.5,
                'unit': 's',
                'description': 'Ab dieser Zeit Threading verwenden'
            },
            'step_size': {
                'type': 'float',
                'default': 0.1,
                'min': 0.01,
                'max': 1.0,
                'increment': 0.01,
                'unit': 's',
                'description': 'Schrittgroesse fuer Threading-Delays'
            },
            'verbose_logging': {
                'type': 'bool',
                'default': False,
                'description': 'Ausfuehrliches Logging aktivieren'
            }
        }

        # Setze Standardwerte
        for param_name, param_def in self._parameter_definitions.items():
            self.parameters[param_name] = param_def['default']

        self.delay_seconds = 1.0
        self.delay_complete = False
        self.delay_thread = None

    def initialize(self):
        """Initialisiere Plugin"""
        logger.info(f"{self.name}: Initialisierung")
        logger.info(f"{self.name}: Standard-Delay: {self.get_parameter_value('default_delay')}s")
        self.is_initialized = True
        return True

    def cleanup(self):
        """Cleanup"""
        logger.info(f"{self.name}: Cleanup")
        # Warte auf laufenden Delay
        if self.delay_thread and self.delay_thread.is_alive():
            self.delay_thread.join(timeout=1.0)
        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        """Setze Parameter"""
        if 'delay' in parameters:
            self.delay_seconds = max(0, float(parameters['delay']))

            verbose = self.get_parameter_value('verbose_logging', False)
            if verbose:
                logger.info(f"{self.name}: Verzoegerung gesetzt auf {self.delay_seconds}s")

        if 'wait_time' in parameters:
            self.delay_seconds = max(0, float(parameters['wait_time']))

            verbose = self.get_parameter_value('verbose_logging', False)
            if verbose:
                logger.info(f"{self.name}: Wartezeit gesetzt auf {self.delay_seconds}s")

        # Wenn kein delay Parameter, nutze default
        if 'delay' not in parameters and 'wait_time' not in parameters:
            self.delay_seconds = self.get_parameter_value('default_delay', 1.0)

    def measure(self) -> dict:
        """Führe Wartezeit durch"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Plugin nicht initialisiert")

        verbose = self.get_parameter_value('verbose_logging', False)

        if verbose:
            logger.info(f"{self.name}: Starte Verzoegerung von {self.delay_seconds}s")

        start_time = time.time()

        # Entscheide ob Threading verwendet werden soll
        use_threading = self.get_parameter_value('use_threading', True)
        threshold = self.get_parameter_value('threading_threshold', 2.0)

        if use_threading and self.delay_seconds > threshold:
            self._threaded_delay()
        else:
            self._blocking_delay()

        actual_delay = time.time() - start_time

        result = {
            'delay_requested': self.delay_seconds,
            'delay_actual': round(actual_delay, 3),
            'delay_complete': 1,
            'used_threading': 1 if (use_threading and self.delay_seconds > threshold) else 0,
            'unit_info': {
                'delay_requested': 's',
                'delay_actual': 's',
                'delay_complete': '',
                'used_threading': ''
            }
        }

        if verbose:
            logger.info(f"{self.name}: Verzoegerung abgeschlossen ({actual_delay:.3f}s)")

        return result

    def _blocking_delay(self):
        """Blockierender Delay für kurze Zeiten"""
        time.sleep(self.delay_seconds)

    def _threaded_delay(self):
        """Threading-basierter Delay für längere Zeiten"""
        self.delay_complete = False
        step_size = self.get_parameter_value('step_size', 0.1)
        verbose = self.get_parameter_value('verbose_logging', False)

        def delay_worker():
            """Worker-Funktion für Delay-Thread"""
            steps = int(self.delay_seconds / step_size)
            remainder = self.delay_seconds % step_size

            for i in range(steps):
                if not self.is_initialized:  # Abbruch möglich
                    break

                if verbose and i % 10 == 0:
                    progress = (i * step_size / self.delay_seconds) * 100
                    logger.debug(f"{self.name}: Fortschritt {progress:.0f}%")

                time.sleep(step_size)

            if remainder > 0:
                time.sleep(remainder)

            self.delay_complete = True

        # Starte Thread
        self.delay_thread = threading.Thread(target=delay_worker, daemon=True)
        self.delay_thread.start()

        # Warte auf Completion
        self.delay_thread.join()

    def get_units(self) -> dict:
        """Gibt Einheiten zurück"""
        return {
            'delay_requested': 's',
            'delay_actual': 's',
            'delay_complete': '',
            'used_threading': ''
        }
