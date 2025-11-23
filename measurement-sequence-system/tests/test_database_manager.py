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
