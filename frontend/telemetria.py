import arcade
from frontend.base import PanelUI

class TelemetriaPedalesPanel(PanelUI):
    def __init__(self, backend):
        self.backend = backend

    def draw(self, mi_auto):
        # 1. Dibujamos el contenedor base
        self.dibujar_recuadro_universal(200, 425, 350, 190, arcade.color.GRAY)
        arcade.draw_text("Live Telemetry & Engine", 10, 505, arcade.color.WHITE, 12, bold=True)
        
        # Validamos que tengamos datos
        if not mi_auto:
            arcade.draw_text("Esperando telemetría del auto...", 80, 415, arcade.color.ORANGE, 12)
            return

        # 2. Extraemos los datos de manera segura 
        # ¡CORRECCIÓN!: Usamos los atributos exactos en ESPAÑOL de tu clase Driver
        speed = getattr(mi_auto, 'velocidad', 0)
        gear = getattr(mi_auto, 'marcha', 0)
        throttle = getattr(mi_auto, 'acelerador', 0.0)
        brake = getattr(mi_auto, 'freno', 0.0)

        # 3. Dibujar Textos (Lado Izquierdo del recuadro)
        marcha_str = "R" if gear == -1 else ("N" if gear == 0 else str(gear))
        arcade.draw_text(f"Velocidad: {speed} km/h", 20, 455, arcade.color.WHITE, 14, bold=True)
        arcade.draw_text(f"Marcha: {marcha_str}", 20, 425, arcade.color.WHITE, 14)

        # 4. Dibujar Barras de Pedales (Lado Derecho del recuadro)
        max_height = 120
        bar_width = 40
        bottom_y = 355
        
        # --- Barra del Acelerador ---
        cx_accel = 230
        arcade.draw_polygon_outline((
            (cx_accel - bar_width/2, bottom_y), 
            (cx_accel + bar_width/2, bottom_y), 
            (cx_accel + bar_width/2, bottom_y + max_height), 
            (cx_accel - bar_width/2, bottom_y + max_height)
        ), arcade.color.WHITE, 2)
        
        throttle_h = throttle * max_height
        if throttle_h > 0:
            arcade.draw_polygon_filled((
                (cx_accel - bar_width/2 + 2, bottom_y + 2), 
                (cx_accel + bar_width/2 - 2, bottom_y + 2), 
                (cx_accel + bar_width/2 - 2, bottom_y + throttle_h), 
                (cx_accel - bar_width/2 + 2, bottom_y + throttle_h)
            ), arcade.color.GREEN)
        arcade.draw_text("ACEL", cx_accel - 18, bottom_y - 20, arcade.color.WHITE, 10, bold=True)

        # --- Barra del Freno ---
        cx_brake = 310
        arcade.draw_polygon_outline((
            (cx_brake - bar_width/2, bottom_y), 
            (cx_brake + bar_width/2, bottom_y), 
            (cx_brake + bar_width/2, bottom_y + max_height), 
            (cx_brake - bar_width/2, bottom_y + max_height)
        ), arcade.color.WHITE, 2)
        
        brake_h = brake * max_height
        if brake_h > 0:
            arcade.draw_polygon_filled((
                (cx_brake - bar_width/2 + 2, bottom_y + 2), 
                (cx_brake + bar_width/2 - 2, bottom_y + 2), 
                (cx_brake + bar_width/2 - 2, bottom_y + brake_h), 
                (cx_brake - bar_width/2 + 2, bottom_y + brake_h)
            ), arcade.color.RED)
        arcade.draw_text("FRENO", cx_brake - 22, bottom_y - 20, arcade.color.WHITE, 10, bold=True)