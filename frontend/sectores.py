import arcade
from frontend.base import PanelUI

# Helper para convertir milisegundos a formato F1 (Minutos:Segundos.Milisegundos)
def formato_f1(ms):
    if ms <= 0 or ms is None:
        return "--.---"
    minutos = int(ms // 60000)
    segundos = int((ms % 60000) // 1000)
    milis = int(ms % 1000)
    
    if minutos > 0:
        return f"{minutos}:{segundos:02d}.{milis:03d}"
    else:
        return f"{segundos}.{milis:03d}"

class TiemposSectoresPanel(PanelUI):
    def __init__(self, backend=None):
        self.backend = backend

    def draw(self, mi_auto):
        self.dibujar_recuadro_universal(205, 650, 390, 165, arcade.color.GRAY)
        arcade.draw_text("Sector | Last Lap | My Best | Race Best", 25, 720, arcade.color.WHITE, 12, bold=True)
        
        if not mi_auto:
            arcade.draw_text("Esperando telemetría...", 25, 690, arcade.color.ORANGE, 11)
            return

        historial = getattr(mi_auto, 'historial_vueltas', [])
        
        s1_last, s2_last, s3_last, total_last = 0, 0, 0, 0
        mejor_s1, mejor_s2, mejor_s3, mejor_vuelta = 0, 0, 0, 0

        if len(historial) > 0:
            ultima_vuelta = historial[-1]
            s1_last = ultima_vuelta["sector_1_ms"]
            s2_last = ultima_vuelta["sector_2_ms"]
            s3_last = ultima_vuelta["sector_3_ms"]
            total_last = ultima_vuelta["tiempo_total_ms"]
            
            mejor_s1 = min([v["sector_1_ms"] for v in historial if v["sector_1_ms"] > 0], default=0)
            mejor_s2 = min([v["sector_2_ms"] for v in historial if v["sector_2_ms"] > 0], default=0)
            mejor_s3 = min([v["sector_3_ms"] for v in historial if v["sector_3_ms"] > 0], default=0)
            mejor_vuelta = min([v["tiempo_total_ms"] for v in historial if v["tiempo_total_ms"] > 0], default=0)

        # Extraemos los Tiempos en Vivo
        s1_vivo = getattr(mi_auto, 'tiempo_s1_ms', 0)
        s2_vivo = getattr(mi_auto, 'tiempo_s2_ms', 0)
        
        # --- LA MAGIA EN TIEMPO REAL ---
        # Si ya cruzamos el checkpoint del sector en la vuelta actual (s1_vivo > 0), 
        # comprobamos instantáneamente si es un nuevo récord y lo sobreescribimos visualmente.
        if s1_vivo > 0:
            mejor_s1 = min(mejor_s1, s1_vivo) if mejor_s1 > 0 else s1_vivo
        if s2_vivo > 0:
            mejor_s2 = min(mejor_s2, s2_vivo) if mejor_s2 > 0 else s2_vivo
        # -------------------------------

        # Lógica visual para la columna "Last Lap" / "Live"
        s1_mostrar = formato_f1(s1_vivo) if s1_vivo > 0 else formato_f1(s1_last)
        s2_mostrar = formato_f1(s2_vivo) if s2_vivo > 0 else formato_f1(s2_last)
        
        s3_mostrar = formato_f1(s3_last)
        total_mostrar = formato_f1(total_last)

        # Mejores tiempos de LA CARRERA (todos los pilotos), calculados en el backend
        race_best = self.backend.get_race_best_sectors() if self.backend else {}
        race_s1 = formato_f1(race_best.get("sector_1_ms", 0))
        race_s2 = formato_f1(race_best.get("sector_2_ms", 0))
        race_s3 = formato_f1(race_best.get("sector_3_ms", 0))
        race_vuelta = formato_f1(race_best.get("vuelta_ms", 0))

        # Imprimimos los datos en pantalla
        arcade.draw_text(f"Sector 1 | {s1_mostrar} | {formato_f1(mejor_s1)} | {race_s1}", 25, 690, arcade.color.WHITE, 11)
        arcade.draw_text(f"Sector 2 | {s2_mostrar} | {formato_f1(mejor_s2)} | {race_s2}", 25, 660, arcade.color.WHITE, 11)
        arcade.draw_text(f"Sector 3 | {s3_mostrar} | {formato_f1(mejor_s3)} | {race_s3}", 25, 630, arcade.color.WHITE, 11)
        
        arcade.draw_text(f"Total | {total_mostrar} | {formato_f1(mejor_vuelta)} | {race_vuelta}", 25, 600, arcade.color.YELLOW, 11, bold=True)