import arcade
import fastf1
import threading
import os
from frontend.base import PanelUI

class MinimapaPanel(PanelUI):
    def __init__(self, backend):
        self.backend = backend
        
        self.FASTF1_TRACK_DICT = {
            0: "Australia", 1: "France", 2: "China", 3: "Bahrain",
            4: "Spain", 5: "Monaco", 6: "Canada", 7: "Great Britain", 8: "Germany",
            9: "Hungary", 10: "Belgium", 11: "Italy", 12: "Singapore",
            13: "Japan", 14: "Abu Dhabi", 15: "United States", 16: "Brazil", 17: "Austria",
            18: "Russia", 19: "Mexico", 20: "Azerbaijan", 26: "Netherlands",
            27: "Emilia Romagna", 28: "Portugal", 29: "Saudi Arabia", 30: "Miami"
        }
        
        self.thread_started = False
        self.downloading_data = False
        self.fastf1_ready = False
        self.fastf1_error = ""
        
        self.track_map_points = []
        self.max_fastf1_dist = 0.0 

    def intentar_descargar_mapa(self):
        """Revisa si el backend ya sabe en qué pista estamos para iniciar FastF1."""
        track_id = getattr(self.backend, 'track_id', -1)

        if not self.fastf1_ready and not self.thread_started and track_id != -1:
            track_name = self.FASTF1_TRACK_DICT.get(track_id, getattr(self.backend, 'track_name', "Desconocido"))
            self.thread_started = True
            self.downloading_data = True
            thread = threading.Thread(target=self.download_fastf1_background, args=(track_id, track_name))
            thread.start()

    def download_fastf1_background(self, track_id, track_name):
        """Descarga la telemetría en segundo plano sin congelar la ventana de Arcade."""
        try:
            os.makedirs('cache_dir', exist_ok=True)
            fastf1.Cache.enable_cache('cache_dir') 
            
            fastf1_location = self.FASTF1_TRACK_DICT.get(track_id, track_name)
            
            session = fastf1.get_session(2022, fastf1_location, 'Q')
            session.load(telemetry=True, weather=False, messages=False)
            
            fastest_lap = session.laps.pick_fastest()
            telemetry = fastest_lap.get_telemetry()
            
            x = telemetry['X'].values
            y = telemetry['Y'].values
            dist = telemetry['Distance'].values
            
            self.max_fastf1_dist = dist[-1] 
            
            min_x, max_x = min(x), max(x)
            min_y, max_y = min(y), max(y)
            max_range = max(max_x - min_x, max_y - min_y)
            
            # --- Ajuste de Posición del Minimapa ---
            map_size = 200 
            map_center_x = 1250 - 130 # SCREEN_WIDTH - 130
            map_center_y = 800 - 160  # SCREEN_HEIGHT - 160
            
            self.track_map_points.clear()
            for i in range(len(x)):
                scaled_x = ((x[i] - min_x) / max_range - 0.5) * map_size
                scaled_y = ((y[i] - min_y) / max_range - 0.5) * map_size
                
                self.track_map_points.append({
                    'dist': float(dist[i]),
                    'x': map_center_x + scaled_x,
                    'y': map_center_y + scaled_y
                })
                
            self.fastf1_ready = True
            self.downloading_data = False
            
        except Exception as e:
            self.fastf1_error = f"Error de FastF1: {str(e)}"
            self.downloading_data = False 

    def get_coordenadas_mapa(self, distancia_piloto):
        """Convierte la distancia del juego a una coordenada (X,Y) en el minimapa de FastF1."""
        safe_track_length = max(getattr(self.backend, 'longitud_pista', 5000.0), 1.0)
        progress_pct = distancia_piloto / safe_track_length
        target_fastf1_dist = progress_pct * self.max_fastf1_dist
        
        # Encontramos el punto más cercano en el mapa trazado
        px, py = self.track_map_points[0]['x'], self.track_map_points[0]['y']
        for point in self.track_map_points:
            if point['dist'] >= target_fastf1_dist:
                px, py = point['x'], point['y']
                break
        return px, py

    def draw(self, mi_auto):
        # 1. Intentamos iniciar la descarga si ya tenemos el nombre de la pista
        self.intentar_descargar_mapa()
        
        # Textos de estado superior
        if self.fastf1_error:
            arcade.draw_text(self.fastf1_error, 1000, 750, arcade.color.RED, 10, bold=True)
        elif self.downloading_data:
            arcade.draw_text("Descargando mapa GPS...", 1000, 750, arcade.color.ORANGE, 10)

        # 2. Dibujar circuito y posiciones
        if self.fastf1_ready and len(self.track_map_points) > 0:
            # Línea de la pista
            line_points = [(p['x'], p['y']) for p in self.track_map_points]
            arcade.draw_line_strip(line_points, arcade.color.GRAY, 3)
            
            if not mi_auto:
                return

            mi_posicion = getattr(mi_auto, 'posicion', 0)
            
            # 3. Buscar los perfiles clave iterando por el backend
            pilotos = list(self.backend.drivers.values())
            lider, adelante, atras = None, None, None
            
            for p in pilotos:
                pos = getattr(p, 'posicion', 0)
                if pos == 1:
                    lider = p
                elif pos == mi_posicion - 1:
                    adelante = p
                elif pos == mi_posicion + 1:
                    atras = p

            # Función interna para no repetir código al pintar monoplazas
            def pintar_monoplaza(piloto_obj, color, radio, texto):
                if piloto_obj:
                    # NOTA: Asegúrate de que tu clase Driver actualice 'distancia' con el paquete ID 2
                    dist = getattr(piloto_obj, 'distancia', 0.0) 
                    if dist > 0:
                        px, py = self.get_coordenadas_mapa(dist)
                        arcade.draw_circle_filled(px, py, radio, color)
                        # Mini etiqueta para identificarlos
                        arcade.draw_text(texto, px + 8, py - 4, color, 9, bold=True)

            # 4. Pintamos a los rivales primero (para que tu punto amarillo quede por encima si se cruzan)
            if lider and lider != mi_auto:
                pintar_monoplaza(lider, arcade.color.PURPLE, 5, "P1")
            
            pintar_monoplaza(atras, arcade.color.RED, 5, f"P{mi_posicion + 1}")
            pintar_monoplaza(adelante, arcade.color.GREEN, 5, f"P{mi_posicion - 1}")
            
            # 5. Pintamos tu auto
            pintar_monoplaza(mi_auto, arcade.color.YELLOW, 7, "ME")