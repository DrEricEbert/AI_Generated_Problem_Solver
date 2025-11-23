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
