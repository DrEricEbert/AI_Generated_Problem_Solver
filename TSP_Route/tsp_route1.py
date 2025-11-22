# -*- coding: utf-8 -*-


"""
Route Optimizer - Traveling Salesman Problem Solver mit Google Maps Integration
Autor: Professional Python Developer
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import tkintermapview
import json
import itertools
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
import math
from datetime import datetime
import webbrowser
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import threading


@dataclass
class Location:
    """Datenklasse für Standorte"""
    name: str
    latitude: float
    longitude: float
    address: str = ""


class TSPSolver:
    """Traveling Salesman Problem Solver"""
    
    @staticmethod
    def calculate_distance(loc1: Location, loc2: Location) -> float:
        """Berechnet die Distanz zwischen zwei Standorten in km"""
        return geodesic(
            (loc1.latitude, loc1.longitude),
            (loc2.latitude, loc2.longitude)
        ).kilometers
    
    @staticmethod
    def calculate_route_distance(route: List[Location]) -> float:
        """Berechnet die Gesamtdistanz einer Route"""
        total_distance = 0
        for i in range(len(route) - 1):
            total_distance += TSPSolver.calculate_distance(route[i], route[i + 1])
        return total_distance
    
    @staticmethod
    def solve_tsp_nearest_neighbor(locations: List[Location], start_index: int = 0) -> Tuple[List[Location], float]:
        """
        Löst TSP mit Nearest Neighbor Algorithmus
        Schnell, aber nicht optimal
        """
        if len(locations) <= 1:
            return locations, 0
        
        unvisited = locations.copy()
        route = [unvisited.pop(start_index)]
        
        while unvisited:
            last = route[-1]
            nearest = min(unvisited, key=lambda loc: TSPSolver.calculate_distance(last, loc))
            route.append(nearest)
            unvisited.remove(nearest)
        
        distance = TSPSolver.calculate_route_distance(route)
        return route, distance
    
    @staticmethod
    def solve_tsp_brute_force(locations: List[Location]) -> Tuple[List[Location], float]:
        """
        Löst TSP mit Brute Force (nur für wenige Standorte geeignet)
        Optimal, aber langsam
        """
        if len(locations) <= 1:
            return locations, 0
        
        if len(locations) > 10:
            raise ValueError("Brute Force nur für max. 10 Standorte geeignet")
        
        start = locations[0]
        others = locations[1:]
        
        best_route = None
        best_distance = float('inf')
        
        for perm in itertools.permutations(others):
            route = [start] + list(perm)
            distance = TSPSolver.calculate_route_distance(route)
            
            if distance < best_distance:
                best_distance = distance
                best_route = route
        
        return best_route, best_distance
    
    @staticmethod
    def solve_tsp_2opt(locations: List[Location], max_iterations: int = 1000) -> Tuple[List[Location], float]:
        """
        Löst TSP mit 2-opt Algorithmus
        Guter Kompromiss zwischen Geschwindigkeit und Qualität
        """
        if len(locations) <= 1:
            return locations, 0
        
        # Start mit Nearest Neighbor
        route, _ = TSPSolver.solve_tsp_nearest_neighbor(locations)
        improved = True
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            for i in range(1, len(route) - 1):
                for j in range(i + 1, len(route)):
                    # Erstelle neue Route durch Umkehrung des Segments
                    new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]
                    
                    new_distance = TSPSolver.calculate_route_distance(new_route)
                    old_distance = TSPSolver.calculate_route_distance(route)
                    
                    if new_distance < old_distance:
                        route = new_route
                        improved = True
                        break
                
                if improved:
                    break
        
        distance = TSPSolver.calculate_route_distance(route)
        return route, distance


class RouteOptimizerApp:
    """Hauptanwendung für Route Optimization"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Route Optimizer - TSP Solver Professional")
        self.root.geometry("1400x900")
        
        # Daten
        self.locations: List[Location] = []
        self.optimized_route: List[Location] = []
        self.route_distance: float = 0
        self.markers = []
        self.path = None
        
        # Geocoder
        self.geolocator = Nominatim(user_agent="route_optimizer_pro")
        
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
        file_menu.add_command(label="Beenden", command=self.root.quit)
        
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
        
        # Linke Seite - Steuerung
        left_frame = ttk.Frame(main_container, width=400)
        main_container.add(left_frame, weight=1)
        
        # Rechte Seite - Karte
        right_frame = ttk.Frame(main_container)
        main_container.add(right_frame, weight=3)
        
        self._setup_left_panel(left_frame)
        self._setup_right_panel(right_frame)
        
    def _setup_left_panel(self, parent):
        """Erstellt das linke Steuerungspanel"""
        
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
        
        # Treeview für Standorte
        self.location_tree = ttk.Treeview(
            list_frame,
            columns=('Name', 'Adresse'),
            show='tree headings',
            height=10
        )
        self.location_tree.heading('Name', text='Name')
        self.location_tree.heading('Adresse', text='Adresse')
        self.location_tree.column('#0', width=30)
        self.location_tree.column('Name', width=120)
        self.location_tree.column('Adresse', width=200)
        
        # Scrollbar
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
            text="Nearest Neighbor (schnell)",
            variable=self.algo_var,
            value="nearest"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            algo_frame,
            text="Brute Force (nur ≤10 Orte)",
            variable=self.algo_var,
            value="brute"
        ).pack(anchor=tk.W)
        
        ttk.Button(
            algo_frame,
            text="Route berechnen",
            command=self.optimize_route,
            style='Accent.TButton'
        ).pack(fill=tk.X, pady=5)
        
        # Ergebnis-Anzeige
        result_frame = ttk.LabelFrame(parent, text="Ergebnis", padding=10)
        result_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.result_label = ttk.Label(result_frame, text="Noch keine Route berechnet")
        self.result_label.pack()
        
    def _setup_right_panel(self, parent):
        """Erstellt das rechte Panel mit Karte und Wegbeschreibung"""
        
        # Notebook für Tabs
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Karten-Tab
        map_frame = ttk.Frame(notebook)
        notebook.add(map_frame, text="Karte")
        
        # Karte
        self.map_widget = tkintermapview.TkinterMapView(map_frame, corner_radius=0)
        self.map_widget.pack(fill=tk.BOTH, expand=True)
        self.map_widget.set_position(51.1657, 10.4515)  # Deutschland Zentrum
        self.map_widget.set_zoom(6)
        
        # Wegbeschreibungs-Tab
        directions_frame = ttk.Frame(notebook)
        notebook.add(directions_frame, text="Wegbeschreibung")
        
        self.directions_text = scrolledtext.ScrolledText(
            directions_frame,
            wrap=tk.WORD,
            font=('Arial', 10)
        )
        self.directions_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def add_location(self):
        """Fügt einen neuen Standort hinzu"""
        name = self.name_entry.get().strip()
        address = self.address_entry.get().strip()
        
        if not name or not address:
            messagebox.showwarning("Eingabefehler", "Bitte Name und Adresse eingeben!")
            return
        
        # Geocoding in separatem Thread
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
                    messagebox.showerror("Fehler", f"Adresse '{address}' konnte nicht gefunden werden!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Geocoding-Fehler: {str(e)}")
        
        thread = threading.Thread(target=geocode)
        thread.daemon = True
        thread.start()
        
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
        """Aktualisiert die Karte mit allen Standorten"""
        # Alte Marker entfernen
        for marker in self.markers:
            marker.delete()
        self.markers.clear()
        
        if self.path:
            self.path.delete()
            self.path = None
        
        if not self.locations:
            return
        
        # Neue Marker hinzufügen
        for i, loc in enumerate(self.locations):
            marker = self.map_widget.set_marker(
                loc.latitude,
                loc.longitude,
                text=f"{i + 1}. {loc.name}"
            )
            self.markers.append(marker)
        
        # Karte auf alle Marker zentrieren
        if len(self.locations) == 1:
            self.map_widget.set_position(
                self.locations[0].latitude,
                self.locations[0].longitude
            )
            self.map_widget.set_zoom(12)
        else:
            self._fit_map_to_markers()
    
    def _fit_map_to_markers(self):
        """Passt die Karte an alle Marker an"""
        if not self.locations:
            return
        
        lats = [loc.latitude for loc in self.locations]
        lons = [loc.longitude for loc in self.locations]
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        self.map_widget.set_position(center_lat, center_lon)
        
        # Zoom basierend auf Ausdehnung
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
    
    def optimize_route(self):
        """Optimiert die Route mit dem gewählten Algorithmus"""
        if len(self.locations) < 2:
            messagebox.showwarning("Warnung", "Mindestens 2 Standorte erforderlich!")
            return
        
        algorithm = self.algo_var.get()
        
        try:
            if algorithm == "nearest":
                self.optimized_route, self.route_distance = TSPSolver.solve_tsp_nearest_neighbor(
                    self.locations
                )
            elif algorithm == "2opt":
                self.optimized_route, self.route_distance = TSPSolver.solve_tsp_2opt(
                    self.locations
                )
            elif algorithm == "brute":
                if len(self.locations) > 10:
                    messagebox.showerror("Fehler", "Brute Force nur für max. 10 Standorte!")
                    return
                self.optimized_route, self.route_distance = TSPSolver.solve_tsp_brute_force(
                    self.locations
                )
            
            # Ergebnis anzeigen
            self.result_label.config(
                text=f"Gesamtdistanz: {self.route_distance:.2f} km\n"
                     f"Standorte: {len(self.optimized_route)}"
            )
            
            self._show_optimized_route()
            self._generate_directions()
            
            messagebox.showinfo("Erfolg", "Route erfolgreich optimiert!")
            
        except Exception as e:
            messagebox.showerror("Fehler", f"Optimierungsfehler: {str(e)}")
    
    def _show_optimized_route(self):
        """Zeigt die optimierte Route auf der Karte"""
        # Alte Marker entfernen
        for marker in self.markers:
            marker.delete()
        self.markers.clear()
        
        if self.path:
            self.path.delete()
            self.path = None
        
        if not self.optimized_route:
            return
        
        # Neue Marker mit Reihenfolge
        for i, loc in enumerate(self.optimized_route):
            marker = self.map_widget.set_marker(
                loc.latitude,
                loc.longitude,
                text=f"{i + 1}. {loc.name}"
            )
            self.markers.append(marker)
        
        # Pfad zeichnen
        coordinates = [
            (loc.latitude, loc.longitude)
            for loc in self.optimized_route
        ]
        
        self.path = self.map_widget.set_path(coordinates)
        self._fit_map_to_markers()
    
    def _generate_directions(self):
        """Generiert die Wegbeschreibung"""
        self.directions_text.delete(1.0, tk.END)
        
        if not self.optimized_route:
            return
        
        # Header
        self.directions_text.insert(tk.END, "=" * 80 + "\n")
        self.directions_text.insert(tk.END, "OPTIMIERTE ROUTE - WEGBESCHREIBUNG\n")
        self.directions_text.insert(tk.END, f"Generiert am: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        self.directions_text.insert(tk.END, f"Gesamtdistanz: {self.route_distance:.2f} km\n")
        self.directions_text.insert(tk.END, f"Anzahl Stopps: {len(self.optimized_route)}\n")
        self.directions_text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Detaillierte Wegbeschreibung
        for i, loc in enumerate(self.optimized_route):
            self.directions_text.insert(tk.END, f"Stop {i + 1}: {loc.name}\n")
            self.directions_text.insert(tk.END, f"Adresse: {loc.address}\n")
            self.directions_text.insert(tk.END, f"Koordinaten: {loc.latitude:.6f}, {loc.longitude:.6f}\n")
            
            if i < len(self.optimized_route) - 1:
                next_loc = self.optimized_route[i + 1]
                distance = TSPSolver.calculate_distance(loc, next_loc)
                self.directions_text.insert(tk.END, f"↓ {distance:.2f} km bis zum nächsten Stopp\n")
            
            self.directions_text.insert(tk.END, "\n")
        
        self.directions_text.insert(tk.END, "=" * 80 + "\n")
        self.directions_text.insert(tk.END, "ENDE DER ROUTE\n")
    
    def move_up(self):
        """Verschiebt den ausgewählten Standort nach oben"""
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
        """Verschiebt den ausgewählten Standort nach unten"""
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
        """Löscht den ausgewählten Standort"""
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
            self._update_location_list()
            self._update_map()
            self.result_label.config(text="Noch keine Route berechnet")
            self.directions_text.delete(1.0, tk.END)
    
    def save_locations(self):
        """Speichert die Standorte in einer JSON-Datei"""
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
                
                messagebox.showinfo("Erfolg", "Standorte erfolgreich gespeichert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Speicherfehler: {str(e)}")
    
    def load_locations(self):
        """Lädt Standorte aus einer JSON-Datei"""
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
            messagebox.showwarning("Warnung", "Keine Route zum Drucken verfügbar!")
            return
        
        # Erstelle HTML-Druckversion
        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML-Dateien", "*.html"), ("Alle Dateien", "*.*")]
        )
        
        if filename:
            try:
                html_content = self._generate_print_html()
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                # Öffne im Browser
                webbrowser.open(filename)
                messagebox.showinfo("Erfolg", "Route exportiert und im Browser geöffnet!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Druckfehler: {str(e)}")
    
    def _generate_print_html(self) -> str:
        """Generiert HTML für Druckausgabe"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Optimierte Route</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
        }}
        h1 {{
            color: #333;
        }}
        .info {{
            background-color: #f0f0f0;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        .location {{
            border-left: 4px solid #4CAF50;
            padding: 10px;
            margin: 10px 0;
            background-color: #f9f9f9;
        }}
        .distance {{
            color: #666;
            font-style: italic;
            padding-left: 20px;
        }}
        @media print {{
            .no-print {{
                display: none;
            }}
        }}
    </style>
</head>
<body>
    <h1>Optimierte Route</h1>
    <div class="info">
        <p><strong>Generiert am:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
        <p><strong>Gesamtdistanz:</strong> {self.route_distance:.2f} km</p>
        <p><strong>Anzahl Stopps:</strong> {len(self.optimized_route)}</p>
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
            if i < len(self.optimized_route) - 1:
                next_loc = self.optimized_route[i + 1]
                distance = TSPSolver.calculate_distance(loc, next_loc)
                html += f'    <div class="distance">↓ {distance:.2f} km bis zum nächsten Stopp</div>\n'
        
        html += """
    <button class="no-print" onclick="window.print()">Drucken</button>
</body>
</html>
"""
        return html
    
    def export_map(self):
        """Exportiert die Karte als HTML"""
        if not self.optimized_route:
            messagebox.showwarning("Warnung", "Keine Route zum Exportieren!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("HTML-Dateien", "*.html"), ("Alle Dateien", "*.*")]
        )
        
        if filename:
            try:
                html_content = self._generate_map_html()
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                webbrowser.open(filename)
                messagebox.showinfo("Erfolg", "Karte exportiert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Export-Fehler: {str(e)}")
    
    def _generate_map_html(self) -> str:
        """Generiert HTML mit interaktiver Karte"""
        # Berechne Zentrum
        lats = [loc.latitude for loc in self.optimized_route]
        lons = [loc.longitude for loc in self.optimized_route]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        # Erstelle Marker-Liste
        markers_js = "[\n"
        for i, loc in enumerate(self.optimized_route):
            markers_js += f"    [{loc.latitude}, {loc.longitude}, '{i + 1}. {loc.name}'],\n"
        markers_js += "]"
        
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
        .info {{ padding: 10px; background: white; }}
    </style>
</head>
<body>
    <div class="info">
        <h2>Optimierte Route - {self.route_distance:.2f} km</h2>
    </div>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([{center_lat}, {center_lon}], 10);
        
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);
        
        var markers = {markers_js};
        var latLngs = [];
        
        markers.forEach(function(marker) {{
            L.marker([marker[0], marker[1]]).addTo(map)
                .bindPopup(marker[2]);
            latLngs.push([marker[0], marker[1]]);
        }});
        
        L.polyline(latLngs, {{color: 'blue'}}).addTo(map);
        
        var bounds = L.latLngBounds(latLngs);
        map.fitBounds(bounds);
    </script>
</body>
</html>
"""
        return html
    
    def show_help(self):
        """Zeigt die Hilfe an"""
        help_text = """
ROUTE OPTIMIZER - ANLEITUNG

1. STANDORTE HINZUFÜGEN:
   - Name und Adresse eingeben
   - "Hinzufügen" klicken
   - Standort wird geokodiert und auf Karte angezeigt

2. LISTE VERWALTEN:
   - ↑/↓ Buttons: Reihenfolge ändern
   - "Löschen": Ausgewählten Standort entfernen
   
3. ROUTE OPTIMIEREN:
   - Algorithmus wählen:
     * 2-Opt: Beste Balance (empfohlen)
     * Nearest Neighbor: Schnellste Berechnung
     * Brute Force: Optimales Ergebnis (nur ≤10 Orte)
   - "Route berechnen" klicken

4. ERGEBNISSE:
   - Karte zeigt optimierte Route
   - Wegbeschreibung zeigt Details
   
5. SPEICHERN/LADEN:
   - Datei → Speichern: Standorte in JSON speichern
   - Datei → Öffnen: Standorte aus JSON laden

6. DRUCKEN/EXPORTIEREN:
   - Datei → Route drucken: HTML-Wegbeschreibung
   - Datei → Karte exportieren: Interaktive Karte

TASTENKOMBINATIONEN:
   Ctrl+O: Öffnen
   Ctrl+S: Speichern
   Ctrl+P: Drucken
"""
        
        help_window = tk.Toplevel(self.root)
        help_window.title("Hilfe")
        help_window.geometry("600x500")
        
        text = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=('Courier', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(1.0, help_text)
        text.config(state=tk.DISABLED)
    
    def show_about(self):
        """Zeigt Info über die Anwendung"""
        messagebox.showinfo(
            "Über Route Optimizer",
            "Route Optimizer Professional v1.0\n\n"
            "Traveling Salesman Problem Solver\n"
            "mit Google Maps Integration\n\n"
            "Entwickelt mit Python & Tkinter\n\n"
            "© 2024 - Professional Python Developer"
        )


def main():
    """Hauptfunktion"""
    root = tk.Tk()
    app = RouteOptimizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()