"""
Externes Programm-Steuerungs-Plugin - VOLLSTÄNDIG
Mit Fenster-Steuerung, Aufzeichnung und Wiedergabe
"""

import subprocess
import logging
import json
import time
import os
import platform
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.plugin_manager import MeasurementPlugin

logger = logging.getLogger(__name__)

# Plattform-spezifische Imports
AUTOMATION_AVAILABLE = False
WINDOW_CONTROL_AVAILABLE = False

try:
    import pyautogui
    AUTOMATION_AVAILABLE = True
except ImportError:
    logger.warning("pyautogui nicht verfuegbar - Automation eingeschraenkt")

if platform.system() == 'Windows':
    try:
        import win32gui
        import win32con
        import win32process
        WINDOW_CONTROL_AVAILABLE = True
    except ImportError:
        logger.warning("pywin32 nicht verfuegbar - Windows-Fenster-Steuerung nicht moeglich")
elif platform.system() == 'Linux':
    try:
        import subprocess
        WINDOW_CONTROL_AVAILABLE = True
    except:
        pass


class Action:
    """Basis-Klasse für Aktionen"""

    def __init__(self, action_type: str):
        self.action_type = action_type
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            'type': self.action_type,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict):
        """Erstelle Action aus Dictionary"""
        action_type = data.get('type')

        if action_type == 'click':
            return ClickAction.from_dict(data)
        elif action_type == 'type':
            return TypeAction.from_dict(data)
        elif action_type == 'key':
            return KeyAction.from_dict(data)
        elif action_type == 'wait':
            return WaitAction.from_dict(data)
        elif action_type == 'move':
            return MoveAction.from_dict(data)
        elif action_type == 'drag':
            return DragAction.from_dict(data)
        else:
            return None

    def execute(self):
        """Führe Aktion aus"""
        raise NotImplementedError


class ClickAction(Action):
    """Maus-Klick-Aktion"""

    def __init__(self, x: int, y: int, button: str = 'left', clicks: int = 1):
        super().__init__('click')
        self.x = x
        self.y = y
        self.button = button
        self.clicks = clicks

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'x': self.x,
            'y': self.y,
            'button': self.button,
            'clicks': self.clicks
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            data['x'],
            data['y'],
            data.get('button', 'left'),
            data.get('clicks', 1)
        )

    def execute(self):
        """Führe Klick aus"""
        if AUTOMATION_AVAILABLE:
            pyautogui.click(self.x, self.y, clicks=self.clicks, button=self.button)
            logger.debug(f"Klick ausgefuehrt: ({self.x}, {self.y}), {self.button}, {self.clicks}x")
        else:
            logger.warning("Automation nicht verfuegbar - Klick uebersprungen")


class TypeAction(Action):
    """Text-Eingabe-Aktion"""

    def __init__(self, text: str, interval: float = 0.0):
        super().__init__('type')
        self.text = text
        self.interval = interval

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'text': self.text,
            'interval': self.interval
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(data['text'], data.get('interval', 0.0))

    def execute(self):
        """Führe Text-Eingabe aus"""
        if AUTOMATION_AVAILABLE:
            pyautogui.write(self.text, interval=self.interval)
            logger.debug(f"Text eingegeben: {self.text[:20]}...")
        else:
            logger.warning("Automation nicht verfuegbar - Texteingabe uebersprungen")


class KeyAction(Action):
    """Tastendruck-Aktion"""

    def __init__(self, key: str, presses: int = 1):
        super().__init__('key')
        self.key = key
        self.presses = presses

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'key': self.key,
            'presses': self.presses
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(data['key'], data.get('presses', 1))

    def execute(self):
        """Führe Tastendruck aus"""
        if AUTOMATION_AVAILABLE:
            for _ in range(self.presses):
                pyautogui.press(self.key)
            logger.debug(f"Taste gedrueckt: {self.key}, {self.presses}x")
        else:
            logger.warning("Automation nicht verfuegbar - Tastendruck uebersprungen")


class WaitAction(Action):
    """Warte-Aktion"""

    def __init__(self, duration: float):
        super().__init__('wait')
        self.duration = duration

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data['duration'] = self.duration
        return data

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(data['duration'])

    def execute(self):
        """Führe Wartezeit aus"""
        time.sleep(self.duration)
        logger.debug(f"Gewartet: {self.duration}s")


class MoveAction(Action):
    """Maus-Bewegungs-Aktion"""

    def __init__(self, x: int, y: int, duration: float = 0.0):
        super().__init__('move')
        self.x = x
        self.y = y
        self.duration = duration

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'x': self.x,
            'y': self.y,
            'duration': self.duration
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(data['x'], data['y'], data.get('duration', 0.0))

    def execute(self):
        """Führe Mausbewegung aus"""
        if AUTOMATION_AVAILABLE:
            pyautogui.moveTo(self.x, self.y, duration=self.duration)
            logger.debug(f"Maus bewegt: ({self.x}, {self.y})")
        else:
            logger.warning("Automation nicht verfuegbar - Bewegung uebersprungen")


class DragAction(Action):
    """Maus-Drag-Aktion"""

    def __init__(self, x: int, y: int, button: str = 'left', duration: float = 0.0):
        super().__init__('drag')
        self.x = x
        self.y = y
        self.button = button
        self.duration = duration

    def to_dict(self) -> Dict:
        data = super().to_dict()
        data.update({
            'x': self.x,
            'y': self.y,
            'button': self.button,
            'duration': self.duration
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            data['x'],
            data['y'],
            data.get('button', 'left'),
            data.get('duration', 0.0)
        )

    def execute(self):
        """Führe Drag aus"""
        if AUTOMATION_AVAILABLE:
            pyautogui.drag(self.x, self.y, button=self.button, duration=self.duration)
            logger.debug(f"Drag ausgefuehrt: ({self.x}, {self.y})")
        else:
            logger.warning("Automation nicht verfuegbar - Drag uebersprungen")


class ActionSequence:
    """Sequenz von Aktionen"""

    def __init__(self, name: str = "Unbenannt"):
        self.name = name
        self.actions: List[Action] = []
        self.created = datetime.now().isoformat()
        self.modified = self.created

    def add_action(self, action: Action):
        """Füge Aktion hinzu"""
        self.actions.append(action)
        self.modified = datetime.now().isoformat()

    def clear(self):
        """Lösche alle Aktionen"""
        self.actions.clear()
        self.modified = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Exportiere als Dictionary"""
        return {
            'name': self.name,
            'created': self.created,
            'modified': self.modified,
            'actions': [action.to_dict() for action in self.actions]
        }

    def save(self, filepath: str):
        """Speichere in Datei"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Aktionssequenz gespeichert: {filepath}")

    @classmethod
    def from_dict(cls, data: Dict):
        """Lade aus Dictionary"""
        seq = cls(data.get('name', 'Unbenannt'))
        seq.created = data.get('created', datetime.now().isoformat())
        seq.modified = data.get('modified', seq.created)

        for action_data in data.get('actions', []):
            action = Action.from_dict(action_data)
            if action:
                seq.actions.append(action)

        return seq

    @classmethod
    def load(cls, filepath: str):
        """Lade aus Datei"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Aktionssequenz geladen: {filepath}")
        return cls.from_dict(data)

    def execute(self):
        """Führe alle Aktionen aus"""
        logger.info(f"Fuehre Aktionssequenz aus: {self.name} ({len(self.actions)} Aktionen)")

        for i, action in enumerate(self.actions):
            logger.debug(f"Aktion {i+1}/{len(self.actions)}: {action.action_type}")
            action.execute()

        logger.info(f"Aktionssequenz abgeschlossen: {self.name}")


class ExternalProgramController(MeasurementPlugin):
    """Steuert externe Programme mit Aufzeichnung und Wiedergabe"""

    def __init__(self):
        super().__init__()
        self.name = "ExternalProgramController"
        self.version = "3.0"
        self.description = "Steuert externe Programme mit Fenster-Steuerung, Aufzeichnung und Wiedergabe"

        # Parameter-Definitionen
        self._parameter_definitions = {
            'program_path': {
                'type': 'str',
                'default': '',
                'description': 'Pfad zum externen Programm'
            },
            'program_arguments': {
                'type': 'str',
                'default': '',
                'description': 'Kommandozeilen-Argumente fuer das Programm'
            },
            'working_directory': {
                'type': 'str',
                'default': '',
                'description': 'Arbeitsverzeichnis fuer das Programm'
            },
            'window_title': {
                'type': 'str',
                'default': '',
                'description': 'Fenstertitel zum Finden des Programm-Fensters'
            },
            'window_title_partial': {
                'type': 'bool',
                'default': True,
                'description': 'Teilweiser Fenstertitel-Match'
            },
            'start_program': {
                'type': 'bool',
                'default': False,
                'description': 'Programm automatisch starten'
            },
            'wait_after_start': {
                'type': 'float',
                'default': 2.0,
                'min': 0.0,
                'max': 60.0,
                'increment': 0.5,
                'unit': 's',
                'description': 'Wartezeit nach Programmstart'
            },
            'focus_window': {
                'type': 'bool',
                'default': True,
                'description': 'Fenster in den Vordergrund bringen'
            },
            'maximize_window': {
                'type': 'bool',
                'default': False,
                'description': 'Fenster maximieren'
            },
            'action_sequence_file': {
                'type': 'str',
                'default': '',
                'description': 'Pfad zur Aktionssequenz-Datei (.json)'
            },
            'execute_sequence': {
                'type': 'bool',
                'default': False,
                'description': 'Aktionssequenz automatisch ausfuehren'
            },
            'timeout': {
                'type': 'int',
                'default': 30,
                'min': 1,
                'max': 300,
                'description': 'Timeout fuer Programmausfuehrung (Sekunden)'
            },
            'capture_output': {
                'type': 'bool',
                'default': True,
                'description': 'Programmausgabe erfassen'
            }
        }

        # Setze Standardwerte
        for param_name, param_def in self._parameter_definitions.items():
            self.parameters[param_name] = param_def['default']

        self.process = None
        self.window_handle = None
        self.action_sequence = ActionSequence()
        self.recording = False

    def initialize(self):
        """Initialisiere Plugin"""
        logger.info(f"{self.name}: Initialisierung")

        if AUTOMATION_AVAILABLE:
            # Setze Fail-Safe (Maus in Ecke = Abbruch)
            pyautogui.FAILSAFE = True
            logger.info(f"{self.name}: PyAutoGUI verfuegbar (Fail-Safe aktiviert)")
        else:
            logger.warning(f"{self.name}: PyAutoGUI nicht verfuegbar - Automation eingeschraenkt")

        if WINDOW_CONTROL_AVAILABLE:
            logger.info(f"{self.name}: Fenster-Steuerung verfuegbar")
        else:
            logger.warning(f"{self.name}: Fenster-Steuerung nicht verfuegbar")

        self.is_initialized = True
        return True

    def cleanup(self):
        """Cleanup"""
        logger.info(f"{self.name}: Cleanup")

        # Beende Prozess falls noch läuft
        if self.process and self.process.poll() is None:
            logger.info(f"{self.name}: Beende laufenden Prozess")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

        self.is_initialized = False

    def set_parameters(self, parameters: dict):
        """Setze Parameter"""
        # Standard-Parameter-Handling
        for key, value in parameters.items():
            if key in self.parameters:
                self.parameters[key] = value

    def find_window_by_title(self, title: str, partial: bool = True) -> Optional[int]:
        """Finde Fenster anhand des Titels"""
        if not WINDOW_CONTROL_AVAILABLE:
            logger.warning("Fenster-Steuerung nicht verfuegbar")
            return None

        if platform.system() == 'Windows':
            return self._find_window_windows(title, partial)
        elif platform.system() == 'Linux':
            return self._find_window_linux(title, partial)
        else:
            logger.warning(f"Fenstersuche auf {platform.system()} nicht implementiert")
            return None

    def _find_window_windows(self, title: str, partial: bool) -> Optional[int]:
        """Finde Fenster unter Windows"""
        def enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if window_title:
                    if partial:
                        if title.lower() in window_title.lower():
                            results.append((hwnd, window_title))
                    else:
                        if title.lower() == window_title.lower():
                            results.append((hwnd, window_title))

        results = []
        win32gui.EnumWindows(enum_callback, results)

        if results:
            logger.info(f"Fenster gefunden: {results[0][1]}")
            return results[0][0]
        else:
            logger.warning(f"Kein Fenster gefunden mit Titel: {title}")
            return None

    def _find_window_linux(self, title: str, partial: bool) -> Optional[str]:
        """Finde Fenster unter Linux (mit wmctrl)"""
        try:
            result = subprocess.run(
                ['wmctrl', '-l'],
                capture_output=True,
                text=True
            )

            for line in result.stdout.split('\n'):
                if title.lower() in line.lower() if partial else title.lower() == line.lower():
                    # Extrahiere Window-ID (erste Spalte)
                    window_id = line.split()[0]
                    logger.info(f"Fenster gefunden: {line}")
                    return window_id

            logger.warning(f"Kein Fenster gefunden mit Titel: {title}")
            return None
        except Exception as e:
            logger.error(f"Fehler bei Fenstersuche: {e}")
            return None

    def focus_window(self, window_handle) -> bool:
        """Bringe Fenster in den Vordergrund"""
        if not window_handle:
            return False

        try:
            if platform.system() == 'Windows':
                win32gui.SetForegroundWindow(window_handle)
                logger.info("Fenster in den Vordergrund gebracht")
                return True
            elif platform.system() == 'Linux':
                subprocess.run(['wmctrl', '-i', '-a', window_handle])
                logger.info("Fenster in den Vordergrund gebracht")
                return True
        except Exception as e:
            logger.error(f"Fehler beim Fokussieren des Fensters: {e}")
            return False

    def maximize_window(self, window_handle) -> bool:
        """Maximiere Fenster"""
        if not window_handle:
            return False

        try:
            if platform.system() == 'Windows':
                win32gui.ShowWindow(window_handle, win32con.SW_MAXIMIZE)
                logger.info("Fenster maximiert")
                return True
            elif platform.system() == 'Linux':
                subprocess.run(['wmctrl', '-i', '-r', window_handle, '-b', 'add,maximized_vert,maximized_horz'])
                logger.info("Fenster maximiert")
                return True
        except Exception as e:
            logger.error(f"Fehler beim Maximieren des Fensters: {e}")
            return False

    def start_program(self) -> bool:
        """Starte externes Programm"""
        program_path = self.get_parameter_value('program_path', '')

        if not program_path:
            logger.warning("Kein Programmpfad angegeben")
            return False

        if not os.path.exists(program_path):
            logger.error(f"Programm nicht gefunden: {program_path}")
            return False

        try:
            args = self.get_parameter_value('program_arguments', '')
            working_dir = self.get_parameter_value('working_directory', '')

            # Erstelle Kommando
            cmd = [program_path]
            if args:
                cmd.extend(args.split())

            # Starte Prozess
            self.process = subprocess.Popen(
                cmd,
                cwd=working_dir if working_dir else None,
                stdout=subprocess.PIPE if self.get_parameter_value('capture_output', True) else None,
                stderr=subprocess.PIPE if self.get_parameter_value('capture_output', True) else None
            )

            logger.info(f"Programm gestartet: {program_path} (PID: {self.process.pid})")

            # Warte nach Start
            wait_time = self.get_parameter_value('wait_after_start', 2.0)
            time.sleep(wait_time)

            return True

        except Exception as e:
            logger.error(f"Fehler beim Starten des Programms: {e}")
            return False

    def load_action_sequence(self, filepath: str) -> bool:
        """Lade Aktionssequenz aus Datei"""
        try:
            self.action_sequence = ActionSequence.load(filepath)
            logger.info(f"Aktionssequenz geladen: {len(self.action_sequence.actions)} Aktionen")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Laden der Aktionssequenz: {e}")
            return False

    def save_action_sequence(self, filepath: str) -> bool:
        """Speichere Aktionssequenz in Datei"""
        try:
            self.action_sequence.save(filepath)
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Aktionssequenz: {e}")
            return False

    def execute_action_sequence(self) -> bool:
        """Führe Aktionssequenz aus"""
        try:
            self.action_sequence.execute()
            return True
        except Exception as e:
            logger.error(f"Fehler bei Ausfuehrung der Aktionssequenz: {e}")
            return False

    def measure(self) -> dict:
        """Führe Messung durch"""
        if not self.is_initialized:
            raise RuntimeError(f"{self.name}: Plugin nicht initialisiert")

        result = {
            'program_started': 0,
            'window_found': 0,
            'window_focused': 0,
            'sequence_executed': 0,
            'exit_code': -1,
            'output': '',
            'error': '',
            'execution_time': 0.0,
            'unit_info': {
                'program_started': '',
                'window_found': '',
                'window_focused': '',
                'sequence_executed': '',
                'exit_code': '',
                'output': '',
                'error': '',
                'execution_time': 's'
            }
        }

        start_time = time.time()

        try:
            # Starte Programm wenn gewünscht
            if self.get_parameter_value('start_program', False):
                if self.start_program():
                    result['program_started'] = 1

            # Finde Fenster
            window_title = self.get_parameter_value('window_title', '')
            if window_title:
                partial = self.get_parameter_value('window_title_partial', True)
                self.window_handle = self.find_window_by_title(window_title, partial)

                if self.window_handle:
                    result['window_found'] = 1

                    # Fokussiere Fenster
                    if self.get_parameter_value('focus_window', True):
                        if self.focus_window(self.window_handle):
                            result['window_focused'] = 1

                    # Maximiere wenn gewünscht
                    if self.get_parameter_value('maximize_window', False):
                        self.maximize_window(self.window_handle)

            # Lade und führe Aktionssequenz aus
            sequence_file = self.get_parameter_value('action_sequence_file', '')
            if sequence_file and os.path.exists(sequence_file):
                self.load_action_sequence(sequence_file)

            if self.get_parameter_value('execute_sequence', False):
                if self.execute_action_sequence():
                    result['sequence_executed'] = 1

            # Erfasse Programmausgabe wenn Prozess läuft
            if self.process and self.get_parameter_value('capture_output', True):
                try:
                    timeout = self.get_parameter_value('timeout', 30)
                    stdout, stderr = self.process.communicate(timeout=timeout)

                    result['exit_code'] = self.process.returncode
                    result['output'] = stdout.decode('utf-8', errors='ignore') if stdout else ''
                    result['error'] = stderr.decode('utf-8', errors='ignore') if stderr else ''
                except subprocess.TimeoutExpired:
                    logger.warning("Prozess-Timeout erreicht")
                    result['error'] = 'Timeout expired'

        except Exception as e:
            logger.error(f"Fehler in measure(): {e}")
            result['error'] = str(e)

        result['execution_time'] = round(time.time() - start_time, 3)

        return result

    def get_units(self) -> dict:
        return {
            'execution_time': 's'
        }
