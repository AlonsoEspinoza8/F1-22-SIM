import arcade
from frontend.base import PanelUI

class LeaderboardPanel(PanelUI):
    def __init__(self, backend):
        self.backend = backend

    def draw(self):
        self.dibujar_recuadro_universal(950, 650, 400, 200, arcade.color.GRAY)
        arcade.draw_text("Leaderboard", 770, 735, arcade.color.WHITE, 12, bold=True)
        
        if hasattr(self.backend, 'get_leaderboard'):
            leaderboard = self.backend.get_leaderboard()
            y_offset = 700
            for i, piloto in enumerate(leaderboard[:8]): 
                texto = f"P{piloto.posicion} | {piloto.nombre}"
                # Validamos para evitar errores de atributos inexistentes
                color = arcade.color.YELLOW if getattr(piloto, 'car_index', -1) == getattr(self.backend, 'player_car_index', -1) else arcade.color.WHITE
                arcade.draw_text(texto, 770, y_offset, color, 11)
                y_offset -= 16