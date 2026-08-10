import arcade
from frontend.base import PanelUI

class DesgasteNeumaticosPanel(PanelUI):
    def draw(self, mi_auto):
        self.dibujar_recuadro_universal(700, 250, 300, 200, arcade.color.GRAY)
        arcade.draw_text("Tyre Degradation", 560, 335, arcade.color.WHITE, 12, bold=True)