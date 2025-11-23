# Professionelles Messsequenz-System

Ein umfassendes, erweiterbares System zur Verwaltung und Durchführung von Messsequenzen mit Plugin-Architektur.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🌟 Features

- **Sequenz-Generator**: Flexible Definition von Messabläufen mit Parameterbereichen
- **Plugin-System**: Erweiterbar durch Messgeräte- und Verarbeitungs-Plugins
- **Persistente Speicherung**: JSON-basierte Sequenzen, SQLite-Datenbank für Messergebnisse
- **Datenvisualisierung**: Integrierte Grafik-Darstellung mit Matplotlib
- **Statistische Auswertung**: Automatische Berechnung von Kennwerten
- **Bildverarbeitung**: Kamera-Integration und Bildanalyse
- **Zeitstempel & Einheiten**: Vollständige Metadaten für alle Messungen

## 📋 Inhaltsverzeichnis

- [Installation](#installation)
- [Schnellstart](#schnellstart)
- [Architektur](#architektur)
- [Plugin-Entwicklung](#plugin-entwicklung)
- [Verwendung](#verwendung)
- [API-Referenz](#api-referenz)
- [Beispiele](#beispiele)
- [Lizenz](#lizenz)

## 🚀 Installation

### Voraussetzungen

- Python 3.8 oder höher
- Tkinter (meist in Python enthalten)

### Standard-Installation

```bash
# Repository klonen
git clone https://github.com/yourusername/measurement-sequence-system.git
cd measurement-sequence-system

# Virtuelle Umgebung erstellen (empfohlen)
python -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Anwendung starten
python main.py
