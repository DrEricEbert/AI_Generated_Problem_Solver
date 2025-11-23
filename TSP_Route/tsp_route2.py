

"""
Route Optimizer - TSP Solver mit echter Straßenführung
Erweiterte Version mit OSRM/OpenRouteService Integration
Version: 2.0

pip install tkintermapview geopy requests
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import tkintermapview
import json
import itertools
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Dict
import math
from datetime import datetime
import webbrowser
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import threading
import requests
from functools import lru_cache
import time
import pickle
from pathlib import Path


@dataclass
class Location:
    """Datenklasse für Standorte"""
    name: str
    latitude: float
    longitude: float
    address: str = ""


@dataclass
class RouteSegment:
    """Datenklasse für Routensegmente mit Straßenführung"""
    from_location: Location
    to_location: Location
    distance: float  # in km
    duration: float  # in Minuten
    geometry: List[Tuple[float, float]]  # Wegpunkte für Routenvisualisierung
    instructions: List[str]  # Turn-by-Turn Anweisungen


class RoutingEngine:
    """
    Routing Engine für echte Straßenführung
    Unterstützt: OSRM, OpenRouteService, GraphHopper
    """

    def __init__(self, provider: str = "osrm", api_key: str = None):
        self.provider = provider
        self.api_key = api_key
        self.cache_file = Path.home() / ".route_optimizer_cache.pkl"
        self.cache = self._load_cache()

        # API Endpoints
        self.endpoints = {
            "osrm": "http://router.project-osrm.org/route/v1/driving/",
            "openrouteservice": "https://api.openrouteservice.org/v2/directions/driving-car",
            "graphhopper": "https://graphhopper.com/api/1/route"
        }

    def _load_cache(self) -> Dict:
        """Lädt den Cache vom Dateisystem"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            print(f"Cache-Ladefehler: {e}")
        return {}

    def _save_cache(self):
        """Speichert den Cache"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            print(f"Cache-Speicherfehler: {e}")

    def _get_cache_key(self, loc1: Location, loc2: Location) -> str:
        """Erstellt einen Cache-Schlüssel für zwei Standorte"""
        return f"{self.provider}_{loc1.latitude:.6f}_{loc1.longitude:.6f}_{loc2.latitude:.6f}_{loc2.longitude:.6f}"

    def get_route(self, loc1: Location, loc2: Location) -> Optional[RouteSegment]:
        """
        Berechnet die Route zwischen zwei Standorten mit Straßenführung
        """
        cache_key = self._get_cache_key(loc1, loc2)

        # Cache prüfen
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Route berechnen basierend auf Provider
        try:
            if self.provider == "osrm":
                segment = self._get_route_osrm(loc1, loc2)
            elif self.provider == "openrouteservice":
                segment = self._get_route_ors(loc1, loc2)
            elif self.provider == "graphhopper":
                segment = self._get_route_graphhopper(loc1, loc2)
            else:
                raise ValueError(f"Unbekannter Provider: {self.provider}")

            # Cache speichern
            if segment:
                self.cache[cache_key] = segment
                self._save_cache()

            return segment

        except Exception as e:
            print(f"Routing-Fehler: {e}")
            # Fallback auf Luftlinie
            return self._get_route_fallback(loc1, loc2)

    def _get_route_osrm(self, loc1: Location, loc2: Location) -> RouteSegment:
        """OSRM Routing (kostenlos, keine API-Key erforderlich)"""
        url = f"{self.endpoints['osrm']}{loc1.longitude},{loc1.latitude};{loc2.longitude},{loc2.latitude}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true"
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data["code"] != "Ok":
            raise Exception(f"OSRM Error: {data.get('message', 'Unknown')}")

        route = data["routes"][0]

        # Geometrie extrahieren
        geometry = [
            (coord[1], coord[0])  # OSRM gibt [lon, lat], wir brauchen [lat, lon]
            for coord in route["geometry"]["coordinates"]
        ]

        # Anweisungen extrahieren
        instructions = []
        for leg in route["legs"]:
            for step in leg["steps"]:
                instruction = step.get("maneuver", {}).get("instruction", "")
                distance = step.get("distance", 0)
                if instruction:
                    instructions.append(f"{instruction} ({distance:.0f}m)")

        return RouteSegment(
            from_location=loc1,
            to_location=loc2,
            distance=route["distance"] / 1000,  # Meter zu km
            duration=route["duration"] / 60,  # Sekunden zu Minuten
            geometry=geometry,
            instructions=instructions
        )

    def _get_route_ors(self, loc1: Location, loc2: Location) -> RouteSegment:
        """OpenRouteService Routing (API-Key erforderlich)"""
        if not self.api_key:
            raise ValueError("OpenRouteService benötigt einen API-Key")

        url = self.endpoints['openrouteservice']
        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }

        body = {
            "coordinates": [
                [loc1.longitude, loc1.latitude],
                [loc2.longitude, loc2.latitude]
            ],
            "instructions": True,
            "geometry": True
        }

        response = requests.post(url, json=body, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        route = data["routes"][0]

        # Geometrie dekodieren (Polyline)
        geometry = self._decode_polyline(route["geometry"])

        # Anweisungen
        instructions = [
            f"{step['instruction']} ({step['distance']:.0f}m)"
            for step in route["segments"][0]["steps"]
        ]

        return RouteSegment(
            from_location=loc1,
            to_location=loc2,
            distance=route["summary"]["distance"] / 1000,
            duration=route["summary"]["duration"] / 60,
            geometry=geometry,
            instructions=instructions
        )

    def _get_route_graphhopper(self, loc1: Location, loc2: Location) -> RouteSegment:
        """GraphHopper Routing (API-Key erforderlich)"""
        if not self.api_key:
            raise ValueError("GraphHopper benötigt einen API-Key")

        url = self.endpoints['graphhopper']
        params = {
            'point': [f"{loc1.latitude},{loc1.longitude}", f"{loc2.latitude},{loc2.longitude}"],
            'vehicle': 'car',
            'key': self.api_key,
            'instructions': 'true',
            'points_encoded': 'false'
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        path = data["paths"][0]

        geometry = [
            (coord[1], coord[0])
            for coord in path["points"]["coordinates"]
        ]

        instructions = [
            f"{instr['text']} ({instr['distance']:.0f}m)"
            for instr in path["instructions"]
        ]

        return RouteSegment(
            from_location=loc1,
            to_location=loc2,
            distance=path["distance"] / 1000,
            duration=path["time"] / 60000,
            geometry=geometry,
            instructions=instructions
        )

    def _get_route_fallback(self, loc1: Location, loc2: Location) -> RouteSegment:
        """Fallback: Luftlinie wenn Routing fehlschlägt"""
        distance = geodesic(
            (loc1.latitude, loc1.longitude),
            (loc2.latitude, loc2.longitude)
        ).kilometers

        # Geschätzte Fahrzeit: 50 km/h Durchschnitt
        duration = (distance / 50) * 60

        geometry = [
            (loc1.latitude, loc1.longitude),
            (loc2.latitude, loc2.longitude)
        ]

        return RouteSegment(
            from_location=loc1,
            to_location=loc2,
            distance=distance * 1.3,  # Faktor für Straßenführung
            duration=duration,
            geometry=geometry,
            instructions=[f"Luftlinie: {distance:.2f} km"]
        )

    def _decode_polyline(self, encoded: str) -> List[Tuple[float, float]]:
        """Dekodiert ein Polyline-String"""
        points = []
        index = 0
        lat = 0
        lng = 0

        while index < len(encoded):
            b = 0
            shift = 0
            result = 0

            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break

            dlat = ~(result >> 1) if result & 1 else result >> 1
            lat += dlat

            shift = 0
            result = 0

            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1f) << shift
                shift += 5
                if b < 0x20:
                    break

            dlng = ~(result >> 1) if result & 1 else result >> 1
            lng += dlng

            points.append((lat / 1e5, lng / 1e5))

        return points


class TSPSolverAdvanced:
    """Erweiterter TSP Solver mit Straßenführung"""

    def __init__(self, routing_engine: RoutingEngine):
        self.routing_engine = routing_engine
        self.distance_matrix: Dict[Tuple[int, int], float] = {}
        self.route_segments: Dict[Tuple[int, int], RouteSegment] = {}

    def _calculate_distance_matrix(self, locations: List[Location], progress_callback=None):
        """Berechnet die Distanzmatrix mit Straßenführung"""
        self.distance_matrix.clear()
        self.route_segments.clear()

        total_pairs = len(locations) * (len(locations) - 1) // 2
        current_pair = 0

        for i in range(len(locations)):
            for j in range(i + 1, len(locations)):
                segment = self.routing_engine.get_route(locations[i], locations[j])

                if segment:
                    self.distance_matrix[(i, j)] = segment.distance
                    self.distance_matrix[(j, i)] = segment.distance
                    self.route_segments[(i, j)] = segment

                    # Reverse segment
                    reverse_segment = RouteSegment(
                        from_location=segment.to_location,
                        to_location=segment.from_location,
                        distance=segment.distance,
                        duration=segment.duration,
                        geometry=list(reversed(segment.geometry)),
                        instructions=list(reversed(segment.instructions))
                    )
                    self.route_segments[(j, i)] = reverse_segment

                current_pair += 1
                if progress_callback:
                    progress_callback(current_pair, total_pairs)

                # Rate limiting
                time.sleep(0.1)

    def get_distance(self, idx1: int, idx2: int) -> float:
        """Gibt die Distanz zwischen zwei Standorten zurück"""
        return self.distance_matrix.get((idx1, idx2), float('inf'))

    def solve_tsp_nearest_neighbor(
        self,
        locations: List[Location],
        start_index: int = 0,
        progress_callback=None
    ) -> Tuple[List[Location], float, List[RouteSegment]]:
        """TSP mit Nearest Neighbor und Straßenführung"""

        # Distanzmatrix berechnen
        self._calculate_distance_matrix(locations, progress_callback)

        if len(locations) <= 1:
            return locations, 0, []

        unvisited = set(range(len(locations)))
        route_indices = [start_index]
        unvisited.remove(start_index)

        while unvisited:
            last = route_indices[-1]
            nearest = min(unvisited, key=lambda idx: self.get_distance(last, idx))
            route_indices.append(nearest)
            unvisited.remove(nearest)

        # Erstelle Route
        route = [locations[i] for i in route_indices]

        # Berechne Gesamtdistanz und sammle Segmente
        total_distance = 0
        segments = []

        for i in range(len(route_indices) - 1):
            idx1, idx2 = route_indices[i], route_indices[i + 1]
            segment = self.route_segments.get((idx1, idx2))
            if segment:
                total_distance += segment.distance
                segments.append(segment)

        return route, total_distance, segments

    def solve_tsp_2opt(
        self,
        locations: List[Location],
        max_iterations: int = 1000,
        progress_callback=None
    ) -> Tuple[List[Location], float, List[RouteSegment]]:
        """TSP mit 2-opt und Straßenführung"""

        # Distanzmatrix berechnen
        self._calculate_distance_matrix(locations, progress_callback)

        if len(locations) <= 1:
            return locations, 0, []

        # Start mit Nearest Neighbor
        route_indices = list(range(len(locations)))

        def calculate_route_distance(indices):
            total = 0
            for i in range(len(indices) - 1):
                total += self.get_distance(indices[i], indices[i + 1])
            return total

        improved = True
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            for i in range(1, len(route_indices) - 1):
                for j in range(i + 1, len(route_indices)):
                    new_indices = route_indices[:i] + route_indices[i:j+1][::-1] + route_indices[j+1:]

                    if calculate_route_distance(new_indices) < calculate_route_distance(route_indices):
                        route_indices = new_indices
                        improved = True
                        break

                if improved:
                    break

        # Erstelle finale Route
        route = [locations[i] for i in route_indices]
        total_distance = calculate_route_distance(route_indices)

        segments = []
        for i in range(len(route_indices) - 1):
            segment = self.route_segments.get((route_indices[i], route_indices[i + 1]))
            if segment:
                segments.append(segment)

        return route, total_distance, segments


class RouteOptimizerApp:
    """Hauptanwendung - Erweiterte Version"""

    def __init__(self, root):
        self.root = root
        self.root.title("Route Optimizer Pro - Mit Straßenführung v2.0")
        self.root.geometry("1600x950")

        # Daten
        self.locations: List[Location] = []
        self.optimized_route: List[Location] = []
        self.route_segments: List[RouteSegment] = []
        self.route_distance: float = 0
        self.route_duration: float = 0
        self.markers = []
        self.path = None

        # Routing Engine
        self.routing_provider = tk.StringVar(value="osrm")
        self.api_key = tk.StringVar(value="")
        self.routing_engine = RoutingEngine(provider="osrm")

        # Geocoder
        self.geolocator = Nominatim(user_agent="route_optimizer_pro_v2")

        self._setup_ui()
        self._setup_menu()

    def _setup_menu(self):
        """Erstellt die Menüleiste"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Datei-Menü
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Datei", menu=file_menu)
        file_menu.add_command(label="Öffnen", command=self.load_locations, accelerator="Ctrl+O")
        file_menu.add_command(label="Speichern", command=self.save_locations, accelerator="Ctrl+S")
        file_menu.add_separator()
        file_menu.add_command(label="Route drucken", command=self.print_route, accelerator="Ctrl+P")
        file_menu.add_command(label="Karte exportieren", command=self.export_map)
        file_menu.add_separator()
        file_menu.add_command(label="Cache löschen", command=self.clear_cache)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self.root.quit)

        # Einstellungen-Menü
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Einstellungen", menu=settings_menu)
        settings_menu.add_command(label="Routing-Provider", command=self.show_routing_settings)

        # Bearbeiten-Menü
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bearbeiten", menu=edit_menu)
        edit_menu.add_command(label="Alle löschen", command=self.clear_all)

        # Hilfe-Menü
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Hilfe", menu=help_menu)
        help_menu.add_command(label="Anleitung", command=self.show_help)
        help_menu.add_command(label="Über", command=self.show_about)

        # Tastenkombinationen
        self.root.bind('<Control-o>', lambda e: self.load_locations())
        self.root.bind('<Control-s>', lambda e: self.save_locations())
        self.root.bind('<Control-p>', lambda e: self.print_route())

    def _setup_ui(self):
        """Erstellt das UI-Layout"""

        # Haupt-Container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Linke Seite
        left_frame = ttk.Frame(main_container, width=400)
        main_container.add(left_frame, weight=1)

        # Rechte Seite
        right_frame = ttk.Frame(main_container)
        main_container.add(right_frame, weight=3)

        self._setup_left_panel(left_frame)
        self._setup_right_panel(right_frame)

    def _setup_left_panel(self, parent):
        """Erstellt das linke Steuerungspanel"""

        # Routing Provider Anzeige
        provider_frame = ttk.LabelFrame(parent, text="Routing-Einstellungen", padding=10)
        provider_frame.pack(fill=tk.X, padx=5, pady=5)

        self.provider_label = ttk.Label(
            provider_frame,
            text=f"Provider: {self.routing_provider.get().upper()}",
            font=('Arial', 9, 'bold')
        )
        self.provider_label.pack(anchor=tk.W)

        ttk.Button(
            provider_frame,
            text="⚙ Einstellungen",
            command=self.show_routing_settings,
            width=15
        ).pack(anchor=tk.W, pady=5)

        # Eingabe-Bereich
        input_frame = ttk.LabelFrame(parent, text="Standort hinzufügen", padding=10)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_entry = ttk.Entry(input_frame, width=30)
        self.name_entry.grid(row=0, column=1, pady=2)

        ttk.Label(input_frame, text="Adresse:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.address_entry = ttk.Entry(input_frame, width=30)
        self.address_entry.grid(row=1, column=1, pady=2)

        ttk.Button(input_frame, text="Hinzufügen", command=self.add_location).grid(
            row=2, column=0, columnspan=2, pady=5
        )

        # Standort-Liste
        list_frame = ttk.LabelFrame(parent, text="Standorte", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.location_tree = ttk.Treeview(
            list_frame,
            columns=('Name', 'Adresse'),
            show='tree headings',
            height=8
        )
        self.location_tree.heading('Name', text='Name')
        self.location_tree.heading('Adresse', text='Adresse')
        self.location_tree.column('#0', width=30)
        self.location_tree.column('Name', width=120)
        self.location_tree.column('Adresse', width=200)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.location_tree.yview)
        self.location_tree.configure(yscrollcommand=scrollbar.set)

        self.location_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons für Liste
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="↑", width=3, command=self.move_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="↓", width=3, command=self.move_down).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Löschen", command=self.delete_location).pack(side=tk.LEFT, padx=2)

        # Algorithmus-Auswahl
        algo_frame = ttk.LabelFrame(parent, text="Route optimieren", padding=10)
        algo_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(algo_frame, text="Algorithmus:").pack(anchor=tk.W)
        self.algo_var = tk.StringVar(value="2opt")

        ttk.Radiobutton(
            algo_frame,
            text="2-Opt (empfohlen)",
            variable=self.algo_var,
            value="2opt"
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            algo_frame,
            text="Nearest Neighbor (schneller)",
            variable=self.algo_var,
            value="nearest"
        ).pack(anchor=tk.W)

        self.optimize_button = ttk.Button(
            algo_frame,
            text="🗺 Route mit Straßenführung berechnen",
            command=self.optimize_route,
            style='Accent.TButton'
        )
        self.optimize_button.pack(fill=tk.X, pady=5)

        # Fortschrittsbalken
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            algo_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, pady=5)

        self.progress_label = ttk.Label(algo_frame, text="")
        self.progress_label.pack()

        # Ergebnis-Anzeige
        result_frame = ttk.LabelFrame(parent, text="Ergebnis", padding=10)
        result_frame.pack(fill=tk.X, padx=5, pady=5)

        self.result_label = ttk.Label(
            result_frame,
            text="Noch keine Route berechnet",
            justify=tk.LEFT
        )
        self.result_label.pack(anchor=tk.W)

    def _setup_right_panel(self, parent):
        """Erstellt das rechte Panel mit Karte und Wegbeschreibung"""

        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Karten-Tab
        map_frame = ttk.Frame(notebook)
        notebook.add(map_frame, text="🗺 Karte")

        self.map_widget = tkintermapview.TkinterMapView(map_frame, corner_radius=0)
        self.map_widget.pack(fill=tk.BOTH, expand=True)
        self.map_widget.set_position(51.1657, 10.4515)
        self.map_widget.set_zoom(6)

        # Wegbeschreibungs-Tab
        directions_frame = ttk.Frame(notebook)
        notebook.add(directions_frame, text="📋 Wegbeschreibung")

        self.directions_text = scrolledtext.ScrolledText(
            directions_frame,
            wrap=tk.WORD,
            font=('Arial', 10)
        )
        self.directions_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Turn-by-Turn Tab
        turns_frame = ttk.Frame(notebook)
        notebook.add(turns_frame, text="🧭 Turn-by-Turn")

        self.turns_text = scrolledtext.ScrolledText(
            turns_frame,
            wrap=tk.WORD,
            font=('Arial', 10)
        )
        self.turns_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def show_routing_settings(self):
        """Zeigt Routing-Einstellungen Dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Routing-Einstellungen")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Provider-Auswahl
        provider_frame = ttk.LabelFrame(dialog, text="Routing Provider", padding=15)
        provider_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(
            provider_frame,
            text="Wähle einen Routing-Provider:",
            font=('Arial', 10, 'bold')
        ).pack(anchor=tk.W, pady=5)

        providers = [
            ("OSRM (kostenlos, kein API-Key)", "osrm"),
            ("OpenRouteService (API-Key erforderlich)", "openrouteservice"),
            ("GraphHopper (API-Key erforderlich)", "graphhopper")
        ]

        for text, value in providers:
            ttk.Radiobutton(
                provider_frame,
                text=text,
                variable=self.routing_provider,
                value=value
            ).pack(anchor=tk.W, pady=2)

        # API-Key Eingabe
        key_frame = ttk.LabelFrame(dialog, text="API-Key (falls erforderlich)", padding=15)
        key_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(key_frame, text="API-Key:").pack(anchor=tk.W)
        api_key_entry = ttk.Entry(key_frame, textvariable=self.api_key, width=50)
        api_key_entry.pack(fill=tk.X, pady=5)

        # Info-Text
        info_frame = ttk.LabelFrame(dialog, text="Informationen", padding=15)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        info_text = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, height=8)
        info_text.pack(fill=tk.BOTH, expand=True)
        info_text.insert(1.0, """
OSRM (Open Source Routing Machine):
✓ Kostenlos
✓ Kein API-Key erforderlich
✓ Öffentlicher Server
✗ Geschwindigkeitslimit

OpenRouteService:
✓ Kostenloser API-Key verfügbar
✓ 2000 Anfragen/Tag gratis
→ API-Key unter: openrouteservice.org

GraphHopper:
✓ Kostenloser API-Key verfügbar
✓ 500 Anfragen/Tag gratis
→ API-Key unter: graphhopper.com
        """)
        info_text.config(state=tk.DISABLED)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def apply_settings():
            self.routing_engine = RoutingEngine(
                provider=self.routing_provider.get(),
                api_key=self.api_key.get() if self.api_key.get() else None
            )
            self.provider_label.config(text=f"Provider: {self.routing_provider.get().upper()}")
            messagebox.showinfo("Erfolg", "Routing-Einstellungen gespeichert!")
            dialog.destroy()

        ttk.Button(button_frame, text="Übernehmen", command=apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=dialog.destroy).pack(side=tk.RIGHT)

    def add_location(self):
        """Fügt einen neuen Standort hinzu"""
        name = self.name_entry.get().strip()
        address = self.address_entry.get().strip()

        if not name or not address:
            messagebox.showwarning("Eingabefehler", "Bitte Name und Adresse eingeben!")
            return

        def geocode():
            try:
                location_data = self.geolocator.geocode(address)

                if location_data:
                    loc = Location(
                        name=name,
                        latitude=location_data.latitude,
                        longitude=location_data.longitude,
                        address=address
                    )

                    self.locations.append(loc)
                    self._update_location_list()
                    self._update_map()

                    self.name_entry.delete(0, tk.END)
                    self.address_entry.delete(0, tk.END)
                else:
                    messagebox.showerror("Fehler", f"Adresse '{address}' nicht gefunden!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Geocoding-Fehler: {str(e)}")

        thread = threading.Thread(target=geocode)
        thread.daemon = True
        thread.start()

    def optimize_route(self):
        """Optimiert die Route mit Straßenführung"""
        if len(self.locations) < 2:
            messagebox.showwarning("Warnung", "Mindestens 2 Standorte erforderlich!")
            return

        algorithm = self.algo_var.get()

        # UI sperren
        self.optimize_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_label.config(text="Berechne Routen...")

        def progress_callback(current, total):
            progress = (current / total) * 100
            self.progress_var.set(progress)
            self.progress_label.config(text=f"Route {current}/{total}")
            self.root.update_idletasks()

        def optimize():
            try:
                solver = TSPSolverAdvanced(self.routing_engine)

                if algorithm == "nearest":
                    self.optimized_route, self.route_distance, self.route_segments = \
                        solver.solve_tsp_nearest_neighbor(self.locations, 0, progress_callback)
                elif algorithm == "2opt":
                    self.optimized_route, self.route_distance, self.route_segments = \
                        solver.solve_tsp_2opt(self.locations, progress_callback=progress_callback)

                # Gesamtdauer berechnen
                self.route_duration = sum(seg.duration for seg in self.route_segments)

                # UI aktualisieren
                self.root.after(0, self._update_after_optimization)

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Fehler", f"Optimierung fehlgeschlagen: {str(e)}"))
            finally:
                self.root.after(0, lambda: self.optimize_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.progress_label.config(text=""))

        thread = threading.Thread(target=optimize)
        thread.daemon = True
        thread.start()

    def _update_after_optimization(self):
        """Aktualisiert UI nach erfolgreicher Optimierung"""
        # Ergebnis anzeigen
        hours = int(self.route_duration // 60)
        minutes = int(self.route_duration % 60)

        self.result_label.config(
            text=f"✓ Gesamtdistanz: {self.route_distance:.2f} km\n"
                 f"✓ Fahrzeit: {hours}h {minutes}min\n"
                 f"✓ Stopps: {len(self.optimized_route)}\n"
                 f"✓ Mit Straßenführung"
        )

        self._show_optimized_route()
        self._generate_directions()
        self._generate_turn_by_turn()

        messagebox.showinfo("Erfolg", "Route mit Straßenführung erfolgreich berechnet!")

    def _show_optimized_route(self):
        """Zeigt die optimierte Route auf der Karte mit Straßenführung"""
        # Alte Marker entfernen
        for marker in self.markers:
            marker.delete()
        self.markers.clear()

        if self.path:
            self.path.delete()
            self.path = None

        if not self.optimized_route:
            return

        # Marker setzen
        for i, loc in enumerate(self.optimized_route):
            marker = self.map_widget.set_marker(
                loc.latitude,
                loc.longitude,
                text=f"{i + 1}. {loc.name}"
            )
            self.markers.append(marker)

        # Straßenführung zeichnen
        all_coordinates = []
        for segment in self.route_segments:
            all_coordinates.extend(segment.geometry)

        if all_coordinates:
            self.path = self.map_widget.set_path(all_coordinates, color="blue", width=3)

        self._fit_map_to_markers()

    def _generate_turn_by_turn(self):
        """Generiert detaillierte Turn-by-Turn Anweisungen"""
        self.turns_text.delete(1.0, tk.END)

        if not self.route_segments:
            return

        self.turns_text.insert(tk.END, "=" * 80 + "\n")
        self.turns_text.insert(tk.END, "TURN-BY-TURN NAVIGATION\n")
        self.turns_text.insert(tk.END, f"Generiert: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        self.turns_text.insert(tk.END, "=" * 80 + "\n\n")

        for i, segment in enumerate(self.route_segments):
            self.turns_text.insert(tk.END, f"━━━ ABSCHNITT {i + 1}: {segment.from_location.name} → {segment.to_location.name} ━━━\n")
            self.turns_text.insert(tk.END, f"Distanz: {segment.distance:.2f} km | Dauer: {segment.duration:.0f} min\n\n")

            for j, instruction in enumerate(segment.instructions):
                self.turns_text.insert(tk.END, f"  {j + 1}. {instruction}\n")

            self.turns_text.insert(tk.END, "\n")

    def _generate_directions(self):
        """Generiert die Wegbeschreibung"""
        self.directions_text.delete(1.0, tk.END)

        if not self.optimized_route:
            return

        hours = int(self.route_duration // 60)
        minutes = int(self.route_duration % 60)

        self.directions_text.insert(tk.END, "=" * 80 + "\n")
        self.directions_text.insert(tk.END, "OPTIMIERTE ROUTE - WEGBESCHREIBUNG (STRASSENFÜHRUNG)\n")
        self.directions_text.insert(tk.END, f"Generiert am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        self.directions_text.insert(tk.END, f"Gesamtdistanz: {self.route_distance:.2f} km\n")
        self.directions_text.insert(tk.END, f"Geschätzte Fahrzeit: {hours}h {minutes}min\n")
        self.directions_text.insert(tk.END, f"Anzahl Stopps: {len(self.optimized_route)}\n")
        self.directions_text.insert(tk.END, f"Routing-Provider: {self.routing_provider.get().upper()}\n")
        self.directions_text.insert(tk.END, "=" * 80 + "\n\n")

        for i, loc in enumerate(self.optimized_route):
            self.directions_text.insert(tk.END, f"Stop {i + 1}: {loc.name}\n")
            self.directions_text.insert(tk.END, f"Adresse: {loc.address}\n")
            self.directions_text.insert(tk.END, f"Koordinaten: {loc.latitude:.6f}, {loc.longitude:.6f}\n")

            if i < len(self.route_segments):
                segment = self.route_segments[i]
                self.directions_text.insert(tk.END, f"↓ {segment.distance:.2f} km | {segment.duration:.0f} min Fahrt\n")

            self.directions_text.insert(tk.END, "\n")

        self.directions_text.insert(tk.END, "=" * 80 + "\n")

    def clear_cache(self):
        """Löscht den Routing-Cache"""
        if messagebox.askyesno("Cache löschen", "Möchten Sie den Routing-Cache wirklich löschen?"):
            try:
                if self.routing_engine.cache_file.exists():
                    self.routing_engine.cache_file.unlink()
                self.routing_engine.cache.clear()
                messagebox.showinfo("Erfolg", "Cache gelöscht!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Cache-Fehler: {str(e)}")

    # Übrige Methoden bleiben gleich (move_up, move_down, delete_location, etc.)
    # Hier der Rest des Codes aus der ursprünglichen Version...

    def _update_location_list(self):
        """Aktualisiert die Standort-Liste"""
        self.location_tree.delete(*self.location_tree.get_children())

        for i, loc in enumerate(self.locations):
            self.location_tree.insert(
                '',
                tk.END,
                text=str(i + 1),
                values=(loc.name, loc.address)
            )

    def _update_map(self):
        """Aktualisiert die Karte"""
        for marker in self.markers:
            marker.delete()
        self.markers.clear()

        if self.path:
            self.path.delete()
            self.path = None

        if not self.locations:
            return

        for i, loc in enumerate(self.locations):
            marker = self.map_widget.set_marker(
                loc.latitude,
                loc.longitude,
                text=f"{i + 1}. {loc.name}"
            )
            self.markers.append(marker)

        if len(self.locations) > 1:
            self._fit_map_to_markers()

    def _fit_map_to_markers(self):
        """Passt die Karte an"""
        if not self.locations:
            return

        lats = [loc.latitude for loc in self.locations]
        lons = [loc.longitude for loc in self.locations]

        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        self.map_widget.set_position(center_lat, center_lon)

        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        max_range = max(lat_range, lon_range)

        if max_range < 0.1:
            zoom = 12
        elif max_range < 0.5:
            zoom = 10
        elif max_range < 1:
            zoom = 9
        elif max_range < 5:
            zoom = 7
        else:
            zoom = 6

        self.map_widget.set_zoom(zoom)

    def move_up(self):
        """Verschiebt Standort nach oben"""
        selection = self.location_tree.selection()
        if not selection:
            return

        index = self.location_tree.index(selection[0])
        if index > 0:
            self.locations[index], self.locations[index - 1] = \
                self.locations[index - 1], self.locations[index]
            self._update_location_list()
            self._update_map()

    def move_down(self):
        """Verschiebt Standort nach unten"""
        selection = self.location_tree.selection()
        if not selection:
            return

        index = self.location_tree.index(selection[0])
        if index < len(self.locations) - 1:
            self.locations[index], self.locations[index + 1] = \
                self.locations[index + 1], self.locations[index]
            self._update_location_list()
            self._update_map()

    def delete_location(self):
        """Löscht Standort"""
        selection = self.location_tree.selection()
        if not selection:
            return

        index = self.location_tree.index(selection[0])
        del self.locations[index]
        self._update_location_list()
        self._update_map()

    def clear_all(self):
        """Löscht alle Standorte"""
        if messagebox.askyesno("Bestätigung", "Alle Standorte löschen?"):
            self.locations.clear()
            self.optimized_route.clear()
            self.route_segments.clear()
            self._update_location_list()
            self._update_map()
            self.result_label.config(text="Noch keine Route berechnet")
            self.directions_text.delete(1.0, tk.END)
            self.turns_text.delete(1.0, tk.END)

    def save_locations(self):
        """Speichert Standorte"""
        if not self.locations:
            messagebox.showwarning("Warnung", "Keine Standorte zum Speichern!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )

        if filename:
            try:
                data = {
                    'locations': [asdict(loc) for loc in self.locations],
                    'saved_at': datetime.now().isoformat()
                }

                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                messagebox.showinfo("Erfolg", "Standorte gespeichert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Speicherfehler: {str(e)}")

    def load_locations(self):
        """Lädt Standorte"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON-Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )

        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.locations = [Location(**loc) for loc in data['locations']]
                self._update_location_list()
                self._update_map()

                messagebox.showinfo("Erfolg", f"{len(self.locations)} Standorte geladen!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Ladefehler: {str(e)}")

    def print_route(self):
        """Druckt die Route"""
        if not self.optimized_route:
            messagebox.showwarning("Warnung", "Keine Route zum Drucken!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML-Dateien", "*.html")]
        )

        if filename:
            try:
                html_content = self._generate_print_html()

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                webbrowser.open(filename)
                messagebox.showinfo("Erfolg", "Route exportiert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Export-Fehler: {str(e)}")

    def _generate_print_html(self) -> str:
        """Generiert HTML für Druckausgabe"""
        hours = int(self.route_duration // 60)
        minutes = int(self.route_duration % 60)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Optimierte Route mit Straßenführung</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .info {{ background-color: #e8f4f8; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #2196F3; }}
        .location {{ border-left: 4px solid #4CAF50; padding: 10px; margin: 10px 0; background-color: #f9f9f9; }}
        .segment {{ color: #666; font-style: italic; padding-left: 20px; margin: 5px 0; }}
        .instructions {{ background-color: #fff3cd; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        @media print {{ .no-print {{ display: none; }} }}
    </style>
</head>
<body>
    <h1>🗺 Optimierte Route mit Straßenführung</h1>
    <div class="info">
        <p><strong>📅 Generiert am:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
        <p><strong>📏 Gesamtdistanz:</strong> {self.route_distance:.2f} km (Straßenführung)</p>
        <p><strong>⏱ Geschätzte Fahrzeit:</strong> {hours}h {minutes}min</p>
        <p><strong>📍 Anzahl Stopps:</strong> {len(self.optimized_route)}</p>
        <p><strong>🌐 Routing-Provider:</strong> {self.routing_provider.get().upper()}</p>
    </div>

    <h2>Wegbeschreibung</h2>
"""

        for i, loc in enumerate(self.optimized_route):
            html += f"""
    <div class="location">
        <h3>Stop {i + 1}: {loc.name}</h3>
        <p><strong>Adresse:</strong> {loc.address}</p>
        <p><strong>Koordinaten:</strong> {loc.latitude:.6f}, {loc.longitude:.6f}</p>
    </div>
"""
            if i < len(self.route_segments):
                segment = self.route_segments[i]
                html += f'    <div class="segment">↓ {segment.distance:.2f} km | {segment.duration:.0f} min Fahrt</div>\n'

                if segment.instructions:
                    html += '    <div class="instructions"><strong>Navigation:</strong><ol>\n'
                    for instr in segment.instructions[:5]:  # Max 5 Anweisungen
                        html += f'        <li>{instr}</li>\n'
                    html += '    </ol></div>\n'

        html += """
    <button class="no-print" onclick="window.print()">🖨 Drucken</button>
</body>
</html>
"""
        return html

    def export_map(self):
        """Exportiert Karte als HTML"""
        if not self.optimized_route:
            messagebox.showwarning("Warnung", "Keine Route!")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML-Dateien", "*.html")]
        )

        if filename:
            try:
                html = self._generate_map_html()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html)
                webbrowser.open(filename)
                messagebox.showinfo("Erfolg", "Karte exportiert!")
            except Exception as e:
                messagebox.showerror("Fehler", str(e))

    def _generate_map_html(self) -> str:
        """Generiert interaktive Karte"""
        lats = [loc.latitude for loc in self.optimized_route]
        lons = [loc.longitude for loc in self.optimized_route]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        # Alle Wegpunkte sammeln
        all_coords = []
        for segment in self.route_segments:
            all_coords.extend([f"[{lat}, {lon}]" for lat, lon in segment.geometry])

        coords_js = "[" + ",".join(all_coords) + "]"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Route Map</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
    <style>
        #map {{ height: 600px; width: 100%; }}
        body {{ margin: 0; padding: 0; font-family: Arial; }}
        .info {{ padding: 15px; background: #e8f4f8; }}
    </style>
</head>
<body>
    <div class="info">
        <h2>🗺 Optimierte Route - {self.route_distance:.2f} km | {int(self.route_duration)}min</h2>
        <p>Mit Straßenführung ({self.routing_provider.get().upper()})</p>
    </div>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([{center_lat}, {center_lon}], 10);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap'
        }}).addTo(map);

        // Marker
        var markers = {json.dumps([[loc.latitude, loc.longitude, f"{i+1}. {loc.name}"] for i, loc in enumerate(self.optimized_route)])};
        markers.forEach(function(m) {{
            L.marker([m[0], m[1]]).addTo(map).bindPopup(m[2]);
        }});

        // Route
        var coords = {coords_js};
        L.polyline(coords, {{color: 'blue', weight: 4}}).addTo(map);

        map.fitBounds(L.polyline(coords).getBounds());
    </script>
</body>
</html>
"""
        return html

    def show_help(self):
        """Zeigt Hilfe"""
        help_text = """
ROUTE OPTIMIZER PRO v2.0 - ANLEITUNG

NEU: STRASENFÜHRUNG statt Luftlinie!

1. ROUTING-PROVIDER WÄHLEN:
   Einstellungen → Routing-Provider
   - OSRM: Kostenlos, kein API-Key
   - OpenRouteService: API-Key von openrouteservice.org
   - GraphHopper: API-Key von graphhopper.com

2. STANDORTE HINZUFÜGEN:
   Name + Adresse eingeben → Hinzufügen

3. ROUTE OPTIMIEREN:
   - Algorithmus wählen
   - "Route mit Straßenführung berechnen"
   - Wartezeit: Routing-API wird abgefragt!

4. ERGEBNISSE:
   - Karte: Zeigt echte Straßenführung
   - Wegbeschreibung: Distanzen + Fahrzeiten
   - Turn-by-Turn: Detaillierte Navigation

5. CACHING:
   Routen werden gecacht für schnellere Berechnungen
   Cache löschen: Datei → Cache löschen

TASTENKOMBINATIONEN:
   Ctrl+O: Öffnen
   Ctrl+S: Speichern
   Ctrl+P: Drucken
"""

        help_window = tk.Toplevel(self.root)
        help_window.title("Hilfe")
        help_window.geometry("700x600")

        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=('Courier', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, help_text)
        text.config(state=tk.DISABLED)

    def show_about(self):
        """Zeigt About"""
        messagebox.showinfo(
            "Über Route Optimizer Pro",
            "Route Optimizer Professional v2.0\n\n"
            "NEU: Mit echter Straßenführung!\n\n"
            "✓ TSP-Algorithmen\n"
            "✓ OSRM / OpenRouteService / GraphHopper\n"
            "✓ Turn-by-Turn Navigation\n"
            "✓ Caching für Performance\n\n"
            "© 2024 - Professional Python Developer"
        )


def main():
    """Hauptfunktion"""
    root = tk.Tk()
    app = RouteOptimizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
