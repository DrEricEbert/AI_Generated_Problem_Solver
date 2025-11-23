"""
Vollständiger System-Test
Testet alle Komponenten zusammen
"""

import unittest
import tempfile
import os
import sys
import time
from pathlib import Path

# Pfad anpassen
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.sequence_manager import SequenceManager, MeasurementSequence, ParameterRange
from core.plugin_manager import PluginManager
from core.database_manager import DatabaseManager
from core.config_manager import ConfigManager


class TestCompleteSystem(unittest.TestCase):
    """Vollständiger System-Test"""

    def setUp(self):
        """Setup vor jedem Test"""
        # Temporäre Dateien
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        self.config_path = os.path.join(self.temp_dir, 'config.json')

        # Manager initialisieren
        self.config_manager = ConfigManager(self.config_path)
        self.database_manager = DatabaseManager(self.db_path)
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()

        self.sequence_manager = SequenceManager(
            self.plugin_manager,
            self.database_manager
        )

    def tearDown(self):
        """Cleanup nach jedem Test"""
        self.database_manager.close()

        # Lösche temporäre Dateien
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_run_simple_sequence(self):
        """Test: Erstelle und führe einfache Sequenz aus"""
        # Erstelle Sequenz
        seq = self.sequence_manager.create_sequence("Test Sequence")

        # Füge Parameterbereich hinzu
        pr = ParameterRange("temperature", 20, 40, 3, "°C")
        seq.add_parameter_range(pr)

        # Generiere Messpunkte
        seq.generate_measurement_points()

        self.assertEqual(len(seq.measurement_points), 3)

        # Wähle Plugins (nur wenn verfügbar)
        available_plugins = self.plugin_manager.get_measurement_plugins()
        if 'TemperatureSensor' in available_plugins:
            seq.active_plugins = ['TemperatureSensor']

            # Callbacks für Tracking
            results = {'completed': False, 'points': 0}

            def on_point(point):
                results['points'] += 1

            def on_complete(sequence):
                results['completed'] = True

            self.sequence_manager.register_callback('on_point_complete', on_point)
            self.sequence_manager.register_callback('on_complete', on_complete)

            # Starte Sequenz
            self.sequence_manager.start_sequence()

            # Warte auf Completion (max 30 Sekunden)
            timeout = 30
            start = time.time()
            while self.sequence_manager.is_running() and (time.time() - start) < timeout:
                time.sleep(0.1)

            # Prüfe Ergebnisse
            self.assertTrue(results['completed'], "Sequenz wurde nicht abgeschlossen")
            self.assertEqual(results['points'], 3, "Nicht alle Punkte wurden gemessen")

            # Prüfe Datenbank
            db_data = self.database_manager.get_sequence_data("Test Sequence")
            self.assertEqual(len(db_data), 3, "Daten nicht in Datenbank")

    def test_save_and_load_sequence(self):
        """Test: Speichere und lade Sequenz"""
        # Erstelle Sequenz
        seq = self.sequence_manager.create_sequence("Save Test", "Description")
        pr1 = ParameterRange("temp", 0, 100, 5, "°C")
        pr2 = ParameterRange("voltage", 0, 10, 3, "V")

        seq.add_parameter_range(pr1)
        seq.add_parameter_range(pr2)
        seq.generate_measurement_points()

        seq.active_plugins = ['TemperatureSensor']
        seq.processing_plugins = ['StatisticsProcessor']

        # Speichere
        save_path = os.path.join(self.temp_dir, 'test_seq.json')
        self.sequence_manager.save_sequence(save_path)

        self.assertTrue(os.path.exists(save_path), "Datei wurde nicht erstellt")

        # Lade in neuen Manager
        new_manager = SequenceManager(self.plugin_manager, self.database_manager)
        loaded_seq = new_manager.load_sequence(save_path)

        # Vergleiche
        self.assertEqual(loaded_seq.name, "Save Test")
        self.assertEqual(loaded_seq.description, "Description")
        self.assertEqual(len(loaded_seq.parameter_ranges), 2)
        self.assertEqual(len(loaded_seq.measurement_points), 15)  # 5 * 3
        self.assertEqual(loaded_seq.active_plugins, ['TemperatureSensor'])
        self.assertEqual(loaded_seq.processing_plugins, ['StatisticsProcessor'])

    def test_plugin_loading(self):
        """Test: Plugin-Loading"""
        plugins = self.plugin_manager.get_available_plugins()

        self.assertGreater(len(plugins), 0, "Keine Plugins geladen")

        # Prüfe ob Standard-Plugins vorhanden
        plugin_names = list(plugins.keys())

        # Mindestens einige Plugins sollten verfügbar sein
        expected_plugins = ['TemperatureSensor', 'ElectricalMeter', 'StatisticsProcessor']
        found = [p for p in expected_plugins if p in plugin_names]

        self.assertGreater(len(found), 0, f"Standard-Plugins nicht gefunden. Verfügbar: {plugin_names}")

    def test_database_operations(self):
        """Test: Datenbank-Operationen"""
        # Speichere Testdaten
        self.database_manager.save_measurement(
            sequence_name="DB Test",
            point_name="Point 1",
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

        # Lade Daten
        data = self.database_manager.get_sequence_data("DB Test")

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['point_name'], "Point 1")
        self.assertIn('sensor1', data[0]['values'])

        # Prüfe Sequenz-Liste
        sequences = self.database_manager.get_all_sequences()
        self.assertIn("DB Test", sequences)

        # Lösche Sequenz
        self.database_manager.delete_sequence("DB Test")
        sequences = self.database_manager.get_all_sequences()
        self.assertNotIn("DB Test", sequences)

    def test_config_manager(self):
        """Test: Konfigurations-Manager"""
        # Setze Werte
        self.config_manager.set('test_key', 'test_value')
        self.config_manager.set('test_number', 42)

        # Speichere
        self.config_manager.save()

        # Lade in neue Instanz
        new_config = ConfigManager(self.config_path)
        new_config.load()

        # Prüfe Werte
        self.assertEqual(new_config.get('test_key'), 'test_value')
        self.assertEqual(new_config.get('test_number'), 42)

    def test_delay_plugin(self):
        """Test: Delay-Plugin (nicht-blockierend)"""
        available = self.plugin_manager.get_measurement_plugins()

        if 'DelayPlugin' not in available:
            self.skipTest("DelayPlugin nicht verfügbar")

        # Erstelle Sequenz mit Delay
        seq = self.sequence_manager.create_sequence("Delay Test")
        pr = ParameterRange("delay", 0.1, 0.3, 3, "s")
        seq.add_parameter_range(pr)
        seq.generate_measurement_points()
        seq.active_plugins = ['DelayPlugin']

        # Starte
        start_time = time.time()

        completed = {'flag': False}
        def on_complete(s):
            completed['flag'] = True

        self.sequence_manager.register_callback('on_complete', on_complete)
        self.sequence_manager.start_sequence()

        # Warte
        timeout = 10
        while self.sequence_manager.is_running() and (time.time() - start_time) < timeout:
            time.sleep(0.05)

        elapsed = time.time() - start_time

        # Prüfe
        self.assertTrue(completed['flag'], "Delay-Sequenz nicht abgeschlossen")

        # Gesamtzeit sollte ca. 0.1 + 0.2 + 0.3 = 0.6s sein (plus Overhead)
        self.assertLess(elapsed, 2.0, "Delay zu lang")


class TestPluginSystem(unittest.TestCase):
    """Tests für Plugin-System"""

    def setUp(self):
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()

    def test_plugin_types(self):
        """Test: Plugin-Typen werden korrekt erkannt"""
        meas_plugins = self.plugin_manager.get_measurement_plugins()
        proc_plugins = self.plugin_manager.get_processing_plugins()

        # Listen sollten disjunkt sein
        overlap = set(meas_plugins) & set(proc_plugins)
        self.assertEqual(len(overlap), 0, "Plugins in beiden Kategorien")

    def test_plugin_instantiation(self):
        """Test: Plugins können instanziiert werden"""
        available = self.plugin_manager.get_available_plugins()

        for plugin_name in available.keys():
            try:
                plugin = self.plugin_manager.get_plugin(plugin_name)
                self.assertIsNotNone(plugin, f"Plugin {plugin_name} konnte nicht instanziiert werden")

                # Test initialize/cleanup
                result = plugin.initialize()
                self.assertTrue(result, f"Plugin {plugin_name} Initialisierung fehlgeschlagen")

                plugin.cleanup()

            except Exception as e:
                self.fail(f"Plugin {plugin_name} verursachte Exception: {e}")


def run_tests():
    """Führe alle Tests aus"""
    # Test-Suite erstellen
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Füge Tests hinzu
    suite.addTests(loader.loadTestsFromTestCase(TestCompleteSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestPluginSystem))

    # Führe aus
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
