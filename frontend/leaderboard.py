import arcade
from frontend.base import PanelUI
from frontend.colores_escuderia import color_por_team_id, nombre_compuesto, color_compuesto


class LeaderboardPanel(PanelUI):
    def __init__(self, backend):
        self.backend = backend

    def draw(self):
        # Panel alto y angosto (columna derecha), para que entren los 20 pilotos.
        cx, cy = 1082, 480
        ancho, alto = 275, 515
        self.dibujar_recuadro_universal(cx, cy, ancho, alto, arcade.color.GRAY)
        izq = cx - ancho / 2 + 10
        arcade.draw_text("Leaderboard", izq, cy + alto / 2 - 20, arcade.color.WHITE, 12, bold=True)

        if not hasattr(self.backend, 'get_leaderboard'):
            return

        leaderboard = self.backend.get_leaderboard()  # los 20 pilotos, sin recortar
        alto_fila = 17
        y = cy + alto / 2 - 45

        mi_car_index = getattr(self.backend, 'player_car_index', -1)

        for i, piloto in enumerate(leaderboard):
            es_jugador = getattr(piloto, 'car_index', -2) == mi_car_index
            color_equipo = color_por_team_id(getattr(piloto, 'teamId', -1))

            # Fondo de fila: alternado sutil, y resaltado si es el jugador
            if es_jugador:
                arcade.draw_lrbt_rectangle_filled(izq - 4, cx + ancho / 2 - 6, y - 4, y + 12, (80, 65, 0))
            elif i % 2 == 1:
                arcade.draw_lrbt_rectangle_filled(izq - 4, cx + ancho / 2 - 6, y - 4, y + 12, (40, 40, 40))

            # Chip del color real de la escudería
            arcade.draw_circle_filled(izq + 6, y + 3, 4.5, color_equipo)

            texto = f"P{piloto.posicion}  {piloto.nombre}"
            color_texto = arcade.color.WHITE if not es_jugador else arcade.color.GOLD
            arcade.draw_text(texto, izq + 16, y - 2, color_texto, 9, bold=es_jugador)

            # Compuesto de neumático actual, alineado a la derecha de la fila
            compuesto = getattr(piloto, 'compuesto_neumatico', 0)
            if compuesto:
                letra = nombre_compuesto(compuesto)[0]  # B/M/D/I/L
                color_llanta = color_compuesto(compuesto)
                cx_llanta = cx + ancho / 2 - 20
                arcade.draw_circle_filled(cx_llanta, y + 3, 7, color_llanta)
                arcade.draw_circle_outline(cx_llanta, y + 3, 7, arcade.color.BLACK, 1)
                arcade.draw_text(letra, cx_llanta, y - 2, arcade.color.BLACK, 8, bold=True,
                                  anchor_x="center", anchor_y="baseline")

            y -= alto_fila