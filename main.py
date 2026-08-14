import arcade
from backend.race import Race
from frontend.dashboard import FrontEnd

def main():
    print("🚀 Iniciando Ingeniero de Pista IA...")
    
    # 1. Instanciamos el cerebro (Backend)
    motor_datos = Race()
    
    # 2. Instanciamos la vista (Frontend) y le inyectamos el cerebro
    interfaz = FrontEnd(backend_race=motor_datos)
    
    # 3. Arrancamos el bucle principal de la aplicación
    arcade.run()

if __name__ == "__main__":
    main()

# import os
# import sys
# import time
# import threading
# import traceback

# from backend.race import Race

# INTERVALO_REVISION_EVENTOS_S = 3.0


# def main_con_gui():
#     """Modo normal: arranca la ventana completa de arcade con todos los paneles."""
#     import arcade
#     from frontend.dashboard import FrontEnd

#     print("🚀 Iniciando Ingeniero de Pista IA...")
#     motor_datos = Race()
#     interfaz = FrontEnd(backend_race=motor_datos)
#     arcade.run()


# def main_sin_gui():
#     """
#     Modo de prueba SIN ventana: solo telemetría + voz por consola. Sirve para
#     probar el ingeniero (Ollama + XTTS-v2 + escucha continua) en tiempo real,
#     con datos reales del juego, sin la sobrecarga de abrir la ventana de arcade.

#     No hay push-to-talk (tecla/mando) porque eso depende de la ventana — acá
#     solo funciona la escucha continua con palabra de activación ("ingeniero, ...").
#     """
#     from backend.ingeniero_voz import IngenieroDeVoz
#     from backend.voz_entrada import EntradaDeVoz
#     from backend.voz_salida import SalidaDeVoz
#     from backend.monitor_eventos import MonitorEventos

#     print("🚀 Iniciando Ingeniero de Pista IA (SIN interfaz gráfica — solo voz por consola)...")

#     race = Race()
#     ingeniero = IngenieroDeVoz()
#     entrada_voz = EntradaDeVoz()
#     salida_voz = SalidaDeVoz()
#     monitor_eventos = MonitorEventos()

#     def generar_y_decir(funcion_generadora):
#         def _tarea():
#             texto = funcion_generadora()
#             if texto:
#                 print(f"🎙️ Ingeniero: {texto}")
#                 salida_voz.decir(texto)
#             else:
#                 print("⚠️ El ingeniero no generó respuesta (revisá que Ollama esté corriendo).")
#         threading.Thread(target=_tarea, daemon=True).start()

#     def on_comando_de_voz(comando, frase_completa):
#         print(f"🗣️ Piloto: {frase_completa}")
#         generar_y_decir(lambda: ingeniero.responder_pregunta(race, comando))

#     entrada_voz.iniciar_escucha_continua(on_comando_de_voz)

#     print("✅ Listo. Decí 'ingeniero, <tu pregunta>' cerca del micrófono para probar la voz en tiempo real.")
#     print("   (Ctrl+C para salir)\n")

#     ultima_revision_eventos = 0.0

#     try:
#         while True:
#             try:
#                 race.actualizar_telemetria()
#             except Exception:
#                 print("⚠️ Error en actualizar_telemetria():")
#                 traceback.print_exc()

#             ahora = time.time()
#             if ahora - ultima_revision_eventos >= INTERVALO_REVISION_EVENTOS_S:
#                 ultima_revision_eventos = ahora
#                 if ingeniero.disponible:
#                     try:
#                         motivo = monitor_eventos.revisar(race)
#                         if motivo:
#                             print(f"📡 Evento detectado: {motivo}")
#                             generar_y_decir(lambda: ingeniero.aviso_automatico(race, motivo))
#                     except Exception:
#                         print("⚠️ Error en monitor_eventos.revisar():")
#                         traceback.print_exc()

#             time.sleep(1 / 60)  # similar al framerate del juego, para no consumir 100% de un core en el loop
#     except KeyboardInterrupt:
#         print("\n👋 Cerrando...")


# if __name__ == "__main__":
#     # Corré así para probar SOLO la voz, sin ventana:
#     #   python main.py --sin-gui
#     # Corré así (o sin flags) para el juego normal, con toda la interfaz:
#     #   python main.py
#     sin_gui = "--sin-gui" in sys.argv or os.environ.get("SIN_GUI") == "1"

#     if sin_gui:
#         main_sin_gui()
#     else:
#         main_con_gui()