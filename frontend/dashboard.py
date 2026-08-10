import arcade
from backend.race import Race # Importa tu clase Race real
from frontend.sectores import TiemposSectoresPanel
from frontend.telemetria import TelemetriaPedalesPanel
from frontend.neumaticos import DesgasteNeumaticosPanel
from frontend.gaps import GapsPosicionPanel
from frontend.leaderboard import LeaderboardPanel
from frontend.minimapa import MinimapaPanel

SCREEN_WIDTH = 1250
SCREEN_HEIGHT = 800

class FrontEnd(arcade.Window):
    def __init__(self, backend_race):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "Ingeniero de Pista - Race Mode")
        arcade.set_background_color(arcade.color.EERIE_BLACK)
        self.backend = backend_race
        
        # Instanciar los paneles importados
        self.panel_sectores = TiemposSectoresPanel()
        self.panel_telemetria = TelemetriaPedalesPanel(self.backend)
        self.panel_neumaticos = DesgasteNeumaticosPanel()
        self.panel_gaps = GapsPosicionPanel(self.backend)
        self.panel_leaderboard = LeaderboardPanel(self.backend)
        self.minimapa_panel = MinimapaPanel(self.backend) 

    def on_update(self, delta_time):
        try:
            self.backend.actualizar_telemetria()
        except Exception as e:
            pass

    def on_draw(self):
        self.clear()
        
        mi_auto = None
        # Validación de seguridad por si el backend aún no inicializa los diccionarios
        if hasattr(self.backend, 'player_car_index') and hasattr(self.backend, 'drivers') and self.backend.player_car_index in self.backend.drivers:
            mi_auto = self.backend.drivers[self.backend.player_car_index]

        # Delegar el dibujado a cada panel individual
        self.panel_sectores.draw(mi_auto)
        self.panel_leaderboard.draw()
        self.panel_telemetria.draw(mi_auto)
        self.panel_neumaticos.draw(mi_auto)
        self.panel_gaps.draw()
        # self.minimapa_panel.draw(mi_auto)