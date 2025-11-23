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
