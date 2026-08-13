import arcade
from frontend.base import PanelUI


def color_por_desgaste(pct):
    """Interpola de verde (0% desgaste) a amarillo (50%) a rojo (100%)."""
    pct = max(0.0, min(100.0, pct))
    if pct <= 50:
        t = pct / 50.0
        r = int(0 + t * 255)
        g = 255
    else:
        t = (pct - 50) / 50.0
        r = 255
        g = int(255 - t * 255)
    return (r, g, 0)


class DesgasteNeumaticosPanel(PanelUI):
    def draw(self, mi_auto):
        cx, cy = 700, 250
        self.dibujar_recuadro_universal(cx, cy, 300, 200, arcade.color.GRAY)
        arcade.draw_text("Tyre Degradation", 560, 335, arcade.color.WHITE, 12, bold=True)

        if not mi_auto:
            arcade.draw_text("Esperando telemetría...", 610, 245, arcade.color.ORANGE, 11)
            return

        desgaste = getattr(mi_auto, 'desgaste_neumaticos', {"FL": 0.0, "FR": 0.0, "RL": 0.0, "RR": 0.0})

        rueda_w, rueda_h = 55, 90
        # Posiciones relativas al centro del panel, en vista superior del auto:
        # delanteras arriba, traseras abajo
        posiciones = {
            "FL": (cx - 60, cy + 45),
            "FR": (cx + 60, cy + 45),
            "RL": (cx - 60, cy - 55),
            "RR": (cx + 60, cy - 55),
        }

        for etiqueta, (px, py) in posiciones.items():
            pct = desgaste.get(etiqueta, 0.0)
            color = color_por_desgaste(pct)

            izq, der = px - rueda_w / 2, px + rueda_w / 2
            abj, arr = py - rueda_h / 2, py + rueda_h / 2

            # Rueda: relleno de color según desgaste + contorno
            arcade.draw_lrbt_rectangle_filled(izq, der, abj, arr, color)
            arcade.draw_lrbt_rectangle_outline(izq, der, abj, arr, arcade.color.WHITE, 2)

            # Etiqueta (FL/FR/RL/RR) y porcentaje de desgaste
            arcade.draw_text(etiqueta, px, py + 10, arcade.color.BLACK, 11, bold=True, anchor_x="center")
            arcade.draw_text(f"{pct:.0f}%", px, py - 12, arcade.color.BLACK, 11, bold=True, anchor_x="center")

        # Silueta simple del chasis conectando las 4 ruedas, para ubicar visualmente el auto
        arcade.draw_line(cx - 30, cy + 45, cx - 30, cy - 55, arcade.color.LIGHT_GRAY, 2)
        arcade.draw_line(cx + 30, cy + 45, cx + 30, cy - 55, arcade.color.LIGHT_GRAY, 2)