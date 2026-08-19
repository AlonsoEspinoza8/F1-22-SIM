import arcade
from frontend.base import PanelUI

class GapsPosicionPanel(PanelUI):
    def __init__(self, backend):
        self.backend = backend

    def draw(self):
        cx, cy = 1080, 155
        self.dibujar_recuadro_universal(cx, cy, 280, 125, arcade.color.GRAY)
        arcade.draw_text("Race Info", cx - 130, cy + 45, arcade.color.WHITE, 12, bold=True)

        gaps = self.backend.get_player_gaps() if hasattr(self.backend, 'get_player_gaps') else None
        
        if gaps:
            texto_pos = f"Actual Pos: P{gaps['mi_posicion']}"
            texto_adelante = f"In Front: {gaps['piloto_adelante']} (+{gaps['gap_adelante_m']:.1f}m)"
            texto_atras = f"Behind: {gaps['piloto_atras']} (-{gaps['gap_atras_m']:.1f}m)"
        else:
            texto_pos = "Actual Pos: Calculando..."
            texto_adelante, texto_atras = "-", "-"

        arcade.draw_text(texto_pos, cx - 130, cy + 15, arcade.color.WHITE, 11, bold=True)
        arcade.draw_text(texto_adelante, cx - 130, cy - 15, arcade.color.GREEN, 10)
        arcade.draw_text(texto_atras, cx - 130, cy - 45, arcade.color.RED, 10)