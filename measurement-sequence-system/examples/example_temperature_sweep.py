"""
Beispiel: Temperatur-Sweep mit elektrischen Messungen
"""

import sys
import os

# Pfad anpassen um Module zu importieren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.sequence_manager import SequenceManager, ParameterRange
from core.plugin_manager import PluginManager
from core.database_manager import DatabaseManager
import time


def main():
    """Beispiel für automatische Messsequenz"""

    print("=" * 60)
    print("Temperatur-Sweep Beispiel")
    print("=" * 60)

    # Manager initialisieren
    plugin_manager = PluginManager()
    database_manager = DatabaseManager('example_measurements.db')
    sequence_manager = SequenceManager(plugin_manager, database_manager)

    # Plugins laden
    plugin_manager.load_plugins()
    print(f"\nGeladene Plugins: {len(plugin_manager.plugin_classes)}")
    for name in plugin_manager.plugin_classes.keys():
        print(f"  - {name}")

    # Sequenz erstellen
    print("\n1. Erstelle Sequenz...")
    sequence = sequence_manager.create_sequence(
        "Temperatur-Sweep Beispiel",
        "Messung von Spannung und Strom bei verschiedenen Temperaturen"
    )

    # Parameterbereiche definieren
    print("2. Definiere Parameterbereiche...")

    # Temperatur: 25°C bis 75°C in 6 Schritten
    temp_range = ParameterRange(
        parameter_name="temperature",
        start=25.0,
        end=75.0,
        steps=6,
        unit="°C"
    )
    sequence.add_parameter_range(temp_range)

    # Spannung: 0V bis 5V in 3 Schritten
    voltage_range = ParameterRange(
        parameter_name="voltage",
        start=0.0,
        end=5.0,
        steps=3,
        unit="V"
    )
    sequence.add_parameter_range(voltage_range)

    # Messpunkte generieren
    print("3. Generiere Messpunkte...")
    sequence.generate_measurement_points()
    print(f"   -> {len(sequence.measurement_points)} Messpunkte generiert")

    # Plugins auswählen
    print("4. Wähle Plugins...")
    sequence.active_plugins = ['TemperatureSensor', 'ElectricalMeter']
    sequence.processing_plugins = ['StatisticsProcessor']

    # Sequenz speichern
    print("5. Speichere Sequenz...")
    sequence.save_to_file('temperature_sweep.json')
    print("   -> Gespeichert als 'temperature_sweep.json'")

    # Callbacks registrieren
    def on_start(seq):
        print(f"\n{'='*60}")
        print(f"Messung gestartet: {seq.name}")
        print(f"{'='*60}")

    def on_point_complete(point):
        print(f"\n✓ Messpunkt abgeschlossen: {point.name}")
        print(f"  Parameter: {point.parameters}")
        print(f"  Ergebnisse:")
        for plugin_name, results in point.results.items():
            if isinstance(results, dict):
                for key, value in results.items():
                    if key != 'unit_info':
                        print(f"    {plugin_name}.{key} = {value}")

    def on_progress(current, total, percentage):
        print(f"  Fortschritt: {current}/{total} ({percentage:.1f}%)")

    def on_complete(seq):
        print(f"\n{'='*60}")
        print(f"Messung abgeschlossen: {seq.name}")
        print(f"{'='*60}")

    def on_error(error):
        print(f"\n✗ FEHLER: {error}")

    sequence_manager.register_callback('on_start', on_start)
    sequence_manager.register_callback('on_point_complete', on_point_complete)
    sequence_manager.register_callback('on_progress', on_progress)
    sequence_manager.register_callback('on_complete', on_complete)
    sequence_manager.register_callback('on_error', on_error)

    # Sequenz ausführen
    print("\n6. Starte Messung...\n")
    sequence_manager.start_sequence()

    # Warte auf Abschluss
    while sequence_manager.is_running():
        time.sleep(0.5)

    # Ergebnisse anzeigen
    print("\n7. Lade Ergebnisse aus Datenbank...")
    data = database_manager.get_sequence_data(sequence.name)

    print(f"\n{len(data)} Messpunkte in Datenbank:")
    for i, point in enumerate(data[:3]):  # Zeige erste 3
        print(f"\n  Punkt {i+1}: {point['point_name']}")
        print(f"  Zeitstempel: {point['timestamp']}")
        print(f"  Parameter: {point['parameters']}")

    if len(data) > 3:
        print(f"\n  ... und {len(data) - 3} weitere Punkte")

    # Cleanup
    database_manager.close()

    print("\n" + "="*60)
    print("Beispiel abgeschlossen!")
    print("="*60)
    print(f"\nDateien erstellt:")
    print(f"  - temperature_sweep.json (Sequenz-Definition)")
    print(f"  - example_measurements.db (SQLite-Datenbank)")
    print("\nStarten Sie die GUI um Ergebnisse zu visualisieren:")
    print("  python main.py")


if __name__ == "__main__":
    main()
