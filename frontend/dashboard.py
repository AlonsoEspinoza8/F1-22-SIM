import time
import arcade
import pyglet
from backend.race import Race # Importa tu clase Race real
from backend.ingeniero_voz import IngenieroDeVoz
from backend.monitor_eventos import MonitorEventos
from backend.voz_entrada import EntradaDeVoz
from backend.voz_salida import SalidaDeVoz
from frontend.sectores import TiemposSectoresPanel
from frontend.telemetria import TelemetriaPedalesPanel
from frontend.neumaticos import DesgasteNeumaticosPanel
from frontend.gaps import GapsPosicionPanel
from frontend.leaderboard import LeaderboardPanel
from frontend.minimapa import MinimapaPanel
from frontend.radio import RadioPanel
from backend.voz_salida import SalidaDeVoz  # Importamos tu módulo de voz nativo

SCREEN_WIDTH = 1250
SCREEN_HEIGHT = 800

TECLA_PUSH_TO_TALK = arcade.key.SPACE

# Botón del mando (PS5/Xbox) para push-to-talk. pyglet reconoce los mandos con
# nombres de botón "estándar" (viene de la SDL_GameControllerDB), así que un
# DualSense de PS5 entra en esta misma lista. Equivalencias PS5 más comunes:
#   'a'->Cruz  'b'->Círculo  'x'->Cuadrado  'y'->Triángulo
#   'leftshoulder'->L1  'rightshoulder'->R1  'lefttrigger'->L2  'righttrigger'->R2
#   'leftstick'->L3 (click)  'rightstick'->R3 (click)  'back'->Create  'start'->Options
BOTON_PUSH_TO_TALK_MANDO = "rightshoulder"  # R1, por defecto: fácil de mantener presionado mientras corrés

INTERVALO_REVISION_EVENTOS_S = 3.0  # cada cuánto chequeamos si hay que disparar un aviso automático

class FrontEnd(arcade.Window):
    def __init__(self, backend_race):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, "Ingeniero de Pista - Race Mode")
        arcade.set_background_color(arcade.color.EERIE_BLACK)
        self.backend = backend_race

        # -------- Cargamos un mensaje inicial del asistente de voz -------

        # self.ingeniero_voz = SalidaDeVoz()
        
        # # 2. Mensaje de chequeo de radio en la inicialización
        # mensaje_inicio = (
        #     "Señoras y señores, bienvenidos a una nueva carrera de Fórmula 1."
        # )
        # self.ingeniero_voz.decir(mensaje_inicio)
        
        # Instanciar los paneles importados
        self.panel_sectores = TiemposSectoresPanel(self.backend)
        self.panel_telemetria = TelemetriaPedalesPanel(self.backend)
        self.panel_neumaticos = DesgasteNeumaticosPanel()
        self.panel_gaps = GapsPosicionPanel(self.backend)
        self.panel_leaderboard = LeaderboardPanel(self.backend)
        self.minimapa_panel = MinimapaPanel(self.backend)
        self.panel_radio = RadioPanel()

        # --- Ingeniero de pista con IA ---
        self.ingeniero = IngenieroDeVoz()
        self.monitor_eventos = MonitorEventos()
        self.entrada_voz = EntradaDeVoz()
        self.salida_voz = SalidaDeVoz()

        self.mensajes_radio = []       # [(hablante, texto), ...] para mostrar en pantalla
        self.procesando_pregunta = False
        self._ultima_revision_eventos = 0.0

        # --- Mando (PS5/Xbox) para push-to-talk, en paralelo a la tecla SPACE (respaldo manual) ---
        self.mando = None
        self._conectar_mando()

        # --- Escucha continua con palabra de activación (modo principal, tipo "oye Siri") ---
        self.entrada_voz.iniciar_escucha_continua(self._on_comando_de_voz)

    def _conectar_mando(self):
        """
        Se conecta al primer mando detectado. A diferencia del teclado, pyglet lee
        el mando directo del sistema operativo — no hace falta que esta ventana
        tenga el foco, así podés tener el juego en primer plano y usar el mando igual.
        """
        try:
            mandos = pyglet.input.get_controllers()
            if not mandos:
                print("ℹ️ No se detectó ningún mando. Push-to-talk disponible con la tecla SPACE.")
                return

            self.mando = mandos[0]
            self.mando.open()
            self.mando.push_handlers(
                on_button_press=self._on_boton_mando_press,
                on_button_release=self._on_boton_mando_release,
            )
            print(f"🎮 Mando conectado: '{self.mando.name}'. Push-to-talk: botón '{BOTON_PUSH_TO_TALK_MANDO}'.")
        except Exception as e:
            print(f"⚠️ No se pudo conectar el mando (podés seguir usando la tecla SPACE): {e}")

    def _on_boton_mando_press(self, controller, boton):
        if boton == BOTON_PUSH_TO_TALK_MANDO and not self.entrada_voz.grabando:
            self.entrada_voz.iniciar_grabacion()

    def _on_boton_mando_release(self, controller, boton):
        if boton == BOTON_PUSH_TO_TALK_MANDO:
            self.entrada_voz.detener_grabacion_y_reconocer(self._on_pregunta_reconocida)

    def on_update(self, delta_time):
        try:
            self.backend.actualizar_telemetria()
        except Exception:
            import traceback
            print("⚠️ Error en actualizar_telemetria():")
            traceback.print_exc()

        try:
            self._revisar_avisos_automaticos()
        except Exception:
            import traceback
            print("⚠️ Error en _revisar_avisos_automaticos():")
            traceback.print_exc()

    def _revisar_avisos_automaticos(self):
        ahora = time.time()
        if ahora - self._ultima_revision_eventos < INTERVALO_REVISION_EVENTOS_S:
            return
        self._ultima_revision_eventos = ahora

        if not self.ingeniero.disponible:
            return

        motivo = self.monitor_eventos.revisar(self.backend)
        if motivo:
            self._generar_en_hilo(lambda: self.ingeniero.aviso_automatico(self.backend, motivo))

    def _generar_en_hilo(self, funcion_generadora):
        """Llama a la IA (y después al TTS) en un hilo aparte, para no congelar la ventana."""
        import threading

        def _tarea():
            texto = funcion_generadora()
            if texto:
                self.mensajes_radio.append(("Ingeniero", texto))
                self.salida_voz.decir(texto)
            self.procesando_pregunta = False

        threading.Thread(target=_tarea, daemon=True).start()

    # --- Push-to-talk ---
    def on_key_press(self, symbol, modifiers):
        if symbol == TECLA_PUSH_TO_TALK and not self.entrada_voz.grabando:
            self.entrada_voz.iniciar_grabacion()

    def on_key_release(self, symbol, modifiers):
        if symbol == TECLA_PUSH_TO_TALK:
            self.entrada_voz.detener_grabacion_y_reconocer(self._on_pregunta_reconocida)

    def _on_pregunta_reconocida(self, texto_pregunta):
        """Callback del push-to-talk manual (tecla SPACE o mando)."""
        self.mensajes_radio.append(("Piloto", texto_pregunta))
        self.procesando_pregunta = True
        self._generar_en_hilo(lambda: self.ingeniero.responder_pregunta(self.backend, texto_pregunta))

    def _on_comando_de_voz(self, comando, frase_completa):
        """Callback de la escucha continua: se dispara cuando se detectó la palabra de activación."""
        self.mensajes_radio.append(("Piloto", frase_completa))
        self.procesando_pregunta = True
        self._generar_en_hilo(lambda: self.ingeniero.responder_pregunta(self.backend, comando))

    def on_draw(self):
        self.clear()
        
        mi_auto = None
        # Validación de seguridad por si el backend aún no inicializa los diccionarios
        if hasattr(self.backend, 'player_car_index') and hasattr(self.backend, 'drivers') and self.backend.player_car_index in self.backend.drivers:
            mi_auto = self.backend.drivers[self.backend.player_car_index]

        # Cada panel se dibuja en su propio try/except: si uno falla (p. ej. por un
        # estado inesperado justo al terminar la carrera), no debe tumbar el resto
        # del frame ni impedir que se muestre el aviso de fin de carrera más abajo.
        self._draw_seguro(self.panel_sectores.draw, mi_auto)
        self._draw_seguro(self.panel_leaderboard.draw)
        self._draw_seguro(self.panel_telemetria.draw, mi_auto)
        self._draw_seguro(self.panel_neumaticos.draw, mi_auto)
        self._draw_seguro(self.panel_gaps.draw)
        self._draw_seguro(self.minimapa_panel.draw, mi_auto)
        self._draw_seguro(
            self.panel_radio.draw,
            self.mensajes_radio,
            self.entrada_voz.grabando,                                  # push-to-talk manual activo
            self.procesando_pregunta or self.entrada_voz.procesando_frase,
            self.entrada_voz.escuchando,
            self.entrada_voz.palabra_activacion,
        )

        # Aviso de carrera finalizada (overlay), para no quedar "pegado" sin feedback
        if getattr(self.backend, 'carrera_terminada', False):
            self._draw_seguro(self._dibujar_mensaje_fin_carrera)

    def _draw_seguro(self, func, *args):
        """Ejecuta el draw() de un panel; si falla, lo registra en consola pero no rompe el frame."""
        try:
            func(*args)
        except Exception:
            import traceback
            print(f"⚠️ Error dibujando '{func.__qualname__}':")
            traceback.print_exc()

    def _dibujar_mensaje_fin_carrera(self):
        centro_x, centro_y = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        arcade.draw_lrbt_rectangle_filled(
            centro_x - 240, centro_x + 240, centro_y - 60, centro_y + 60,
            (0, 0, 0, 190)
        )
        arcade.draw_lrbt_rectangle_outline(
            centro_x - 240, centro_x + 240, centro_y - 60, centro_y + 60,
            arcade.color.YELLOW, 3
        )
        arcade.draw_text(
            "CARRERA FINALIZADA", centro_x, centro_y + 12,
            arcade.color.WHITE, 22, bold=True, anchor_x="center", anchor_y="center"
        )
        arcade.draw_text(
            "Esperando la siguiente sesión...", centro_x, centro_y - 18,
            arcade.color.LIGHT_GRAY, 13, anchor_x="center", anchor_y="center"
        )