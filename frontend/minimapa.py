import arcade
import threading
import math
from frontend.base import PanelUI
from backend.circuito_cache import obtener_datos_circuito
from backend.circuitos import FASTF1_TRACK_DICT
from frontend.colores_escuderia import color_por_team_id
from frontend.colores_pilotos import COLOR_JUGADOR

ANCHO_CINTA_PISTA = 5.0  # separación entre el borde interior/exterior del minimapa, en px de pantalla

# Geometría del panel "Circuit" (centro grande del dashboard)
CX_MAPA, CY_MAPA = 675, 490
ANCHO_MAPA, ALTO_MAPA = 460, 495
TAMANO_TRAZADO = 400  # tamaño del trazado dentro del panel, dejando margen para el título


class MinimapaPanel(PanelUI):
    def __init__(self, backend):
        self.backend = backend
        
        self.FASTF1_TRACK_DICT = FASTF1_TRACK_DICT
        
        self.thread_started = False
        self.downloading_data = False
        self.fastf1_ready = False
        self.fastf1_error = ""
        
        self.track_map_points = []
        self.track_inner_points = []   # borde interior de la "cinta" de pista
        self.track_outer_points = []   # borde exterior
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
        """
        Trae el trazado del circuito en un hilo aparte (sin congelar la ventana).
        Usa el caché local si ya existe (rápido, sin fastf1/pandas en memoria);
        si no, cae a descargarlo de FastF1.
        """
        try:
            datos = obtener_datos_circuito(track_id, self.FASTF1_TRACK_DICT)
            if not datos:
                self.fastf1_error = "No se pudo obtener el circuito (ni caché ni FastF1)"
                self.downloading_data = False
                return

            x = [p["x"] for p in datos["telemetria"]]
            y = [p["y"] for p in datos["telemetria"]]
            dist = [p["distancia"] for p in datos["telemetria"]]

            self.max_fastf1_dist = dist[-1]

            min_x, max_x = min(x), max(x)
            min_y, max_y = min(y), max(y)
            max_range = max(max_x - min_x, max_y - min_y) or 1.0
            
            # --- Ajuste de posición del trazado dentro del panel "Circuit" ---
            map_size = TAMANO_TRAZADO
            map_center_x = CX_MAPA
            map_center_y = CY_MAPA - 15  # un poco hacia abajo para dejar aire al título
            
            puntos = []
            for i in range(len(x)):
                scaled_x = ((x[i] - min_x) / max_range - 0.5) * map_size
                scaled_y = ((y[i] - min_y) / max_range - 0.5) * map_size
                puntos.append({
                    'dist': float(dist[i]),
                    'x': map_center_x + scaled_x,
                    'y': map_center_y + scaled_y
                })

            self.track_map_points = puntos
            self.track_inner_points, self.track_outer_points = self._calcular_cinta(puntos)

            self.fastf1_ready = True
            self.downloading_data = False
            
        except Exception as e:
            self.fastf1_error = f"Error obteniendo el circuito: {str(e)}"
            self.downloading_data = False

    @staticmethod
    def _calcular_cinta(puntos, ancho=ANCHO_CINTA_PISTA):
        """
        A partir de la línea central, calcula dos líneas paralelas (borde
        interior/exterior) desplazadas por la normal en cada punto — el mismo
        truco que usan los replays de FastF1 para dibujar la pista como una
        cinta con ancho en vez de una línea fina.
        """
        n = len(puntos)
        interior, exterior = [], []
        for i in range(n):
            anterior = puntos[i - 1]
            siguiente = puntos[(i + 1) % n]
            dx = siguiente['x'] - anterior['x']
            dy = siguiente['y'] - anterior['y']
            largo = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / largo, dx / largo  # vector normal unitario

            p = puntos[i]
            interior.append((p['x'] - nx * ancho, p['y'] - ny * ancho))
            exterior.append((p['x'] + nx * ancho, p['y'] + ny * ancho))
        return interior, exterior

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
        # 0. Recuadro + título del panel (antes el mapa flotaba sin caja propia)
        self.dibujar_recuadro_universal(CX_MAPA, CY_MAPA, ANCHO_MAPA, ALTO_MAPA, arcade.color.GRAY)
        arcade.draw_text("Circuit", CX_MAPA - ANCHO_MAPA / 2 + 12, CY_MAPA + ALTO_MAPA / 2 - 20,
                          arcade.color.WHITE, 13, bold=True)

        # 1. Intentamos iniciar la descarga si ya tenemos el nombre de la pista
        self.intentar_descargar_mapa()
        
        # Textos de estado, debajo del título
        estado_y = CY_MAPA + ALTO_MAPA / 2 - 40
        if self.fastf1_error:
            arcade.draw_text(self.fastf1_error, CX_MAPA - ANCHO_MAPA / 2 + 12, estado_y, arcade.color.RED, 10, bold=True)
        elif self.downloading_data:
            arcade.draw_text("Descargando mapa GPS...", CX_MAPA - ANCHO_MAPA / 2 + 12, estado_y, arcade.color.ORANGE, 10)

        # 2. Dibujar circuito como una "cinta" (borde interior + exterior), no una línea fina
        if self.fastf1_ready and len(self.track_map_points) > 0:
            if len(self.track_inner_points) > 1:
                arcade.draw_line_strip(self.track_inner_points, (110, 110, 110), 3)
            if len(self.track_outer_points) > 1:
                arcade.draw_line_strip(self.track_outer_points, (110, 110, 110), 3)

            if not mi_auto:
                return

            mi_posicion = getattr(mi_auto, 'posicion', 0)
            mi_car_index = getattr(self.backend, 'player_car_index', -1)

            # 3. Pintamos TODOS los autos en pista, cada uno con su color estable
            for piloto in self.backend.drivers.values():
                dist = getattr(piloto, 'distancia', 0.0)
                if dist <= 0:
                    continue

                px, py = self.get_coordenadas_mapa(dist)
                es_jugador = getattr(piloto, 'car_index', -2) == mi_car_index

                if es_jugador:
                    color = COLOR_JUGADOR
                    radio = 11
                    etiqueta = "ME"
                else:
                    color = color_por_team_id(getattr(piloto, 'teamId', -1))
                    radio = 7
                    pos = getattr(piloto, 'posicion', 0)
                    etiqueta = f"P{pos}" if pos else ""

                arcade.draw_circle_filled(px, py, radio, color)
                if es_jugador:
                    arcade.draw_circle_outline(px, py, radio + 3, arcade.color.WHITE, 2)
                if etiqueta:
                    arcade.draw_text(etiqueta, px + radio + 3, py - 5, color, 11, bold=True)