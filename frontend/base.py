import arcade

class PanelUI:
    def dibujar_recuadro_universal(self, centro_x, centro_y, ancho, alto, color):
        izq, der = centro_x - (ancho / 2), centro_x + (ancho / 2)
        abj, arr = centro_y - (alto / 2), centro_y + (alto / 2)
        puntos = [(izq, abj), (der, abj), (der, arr), (izq, arr), (izq, abj)]
        arcade.draw_line_strip(puntos, color, 1)