"""
Test-Skript für Plugin-Parameter
"""

import sys
from pathlib import Path

# Pfad anpassen
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.plugin_manager import PluginManager
import json


def main():
    """Teste Plugin-Parameter"""
    print("=" * 60)
    print("Plugin-Parameter Test")
    print("=" * 60)

    # Plugin-Manager initialisieren
    plugin_manager = PluginManager()
    plugin_manager.load_plugins()

    print(f"\n{len(plugin_manager.plugin_classes)} Plugins geladen\n")

    # Teste jedes Plugin
    for plugin_name in plugin_manager.plugin_classes.keys():
        print(f"\n--- {plugin_name} ---")

        # Erstelle Instanz
        plugin = plugin_manager.get_plugin(plugin_name)

        # Hole Parameter-Definitionen
        param_defs = plugin.get_parameter_definitions()

        if param_defs:
            print(f"  Parameter-Definitionen: {len(param_defs)}")

            for param_name, param_def in param_defs.items():
                print(f"\n  {param_name}:")
                print(f"    Typ: {param_def.get('type')}")
                print(f"    Standard: {param_def.get('default')}")
                if 'min' in param_def:
                    print(f"    Min: {param_def['min']}")
                if 'max' in param_def:
                    print(f"    Max: {param_def['max']}")
                if 'choices' in param_def:
                    print(f"    Auswahl: {param_def['choices']}")
                if 'description' in param_def:
                    print(f"    Beschreibung: {param_def['description']}")

            # Teste Speichern und Laden
            config_file = f"test_{plugin_name}_config.json"

            print(f"\n  Teste Speichern nach {config_file}...")
            plugin.save_parameters(config_file)

            print(f"  Teste Laden aus {config_file}...")
            plugin.load_parameters(config_file)

            print(f"  Aktuelle Parameter:")
            current_params = plugin.get_all_parameters()
            print(f"    {json.dumps(current_params, indent=4)}")
        else:
            print("  Keine Parameter-Definitionen")

    print("\n" + "=" * 60)
    print("Test abgeschlossen")
    print("=" * 60)


if __name__ == "__main__":
    main()
