# PyMathPad Ultimate

PyMathPad ist ein modulares Computer-Algebra-System (CAS), geschrieben in Python. Es kombiniert symbolische Mathematik (SymPy) mit numerischer Berechnung (NumPy/SciPy) und einer dynamischen Dokumenten-Oberfläche.

## Features

*   **Dokument-basiert:** Berechnungen finden in Zellen statt, die untereinander angeordnet sind.
*   **Symbolik & Numerik:** Löst Integrale symbolisch oder berechnet FFTs numerisch.
*   **Live-Updates:** Ändern Sie eine Variable am Anfang, und das gesamte Dokument wird neu berechnet.
*   **Erweiterbar:** Plugin-System (Toolboxes) für Physik, Signalverarbeitung, Bildverarbeitung etc.
*   **Plotting:** Integrierte Matplotlib-Graphen mit Zoom- und Pan-Werkzeugen.
*   **Export:** Speichern und Laden von Arbeitsblättern als JSON.

## Installation

Benötigte Bibliotheken installieren:

```bash
pip install sympy numpy matplotlib scipy scikit-image
