
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
