import arcade
from frontend.base import PanelUI

class GapsPosicionPanel(PanelUI):
    def __init__(self, backend):
        self.backend = backend

    def draw(self):
        self.dibujar_recuadro_universal(1050, 250, 300, 200, arcade.color.GRAY)
        gaps = self.backend.get_player_gaps() if hasattr(self.backend, 'get_player_gaps') else None
        
        if gaps:
            texto_pos = f"Actual Pos: P{gaps['mi_posicion']}"
            texto_adelante = f"In Front: {gaps['piloto_adelante']} (+{gaps['gap_adelante_m']:.1f}m)"
            texto_atras = f"Behind: {gaps['piloto_atras']} (-{gaps['gap_atras_m']:.1f}m)"
        else:
            texto_pos = "Actual Pos: Calculando..."
            texto_adelante, texto_atras = "-", "-"

        arcade.draw_text(texto_pos, 920, 300, arcade.color.WHITE, 12, bold=True)
        arcade.draw_text(texto_adelante, 920, 270, arcade.color.GREEN, 12)
        arcade.draw_text(texto_atras, 920, 240, arcade.color.RED, 12)