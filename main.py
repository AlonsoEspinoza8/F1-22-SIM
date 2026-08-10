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


# import time
# from backend.race import Race

# def main():
#     print("🚀 Iniciando Ingeniero de Pista IA (Modo Consola)...")
    
#     # 1. Instanciamos el cerebro (Backend)
#     motor_datos = Race()
    
#     ultimo_impreso = time.time()
    
#     print("📡 Escuchando telemetría de F1 22 en el puerto 20777...")
#     print("Presiona Ctrl+C para detener el script.\n")
    
#     try:
#         # 2. Arrancamos nuestro propio bucle principal
#         while True:
#             # Actualizamos los datos constantemente (esto es rápido gracias al socket no bloqueante)
#             motor_datos.actualizar_telemetria()
            
#             # 3. Imprimimos el resumen de la carrera cada 2 segundos
#             tiempo_actual = time.time()
#             if tiempo_actual - ultimo_impreso >= 2.0:
#                 motor_datos.imprimir_resumen_carrera()
#                 ultimo_impreso = tiempo_actual
                
#             # Le damos un respiro microscópico a la CPU para no usar el 100% de los recursos
#             time.sleep(0.01)
            
#     except KeyboardInterrupt:
#         # Permite salir del script limpiamente con Ctrl+C
#         print("\n🛑 Sesión de telemetría terminada por el ingeniero. Volviendo a boxes.")

# if __name__ == "__main__":
#     main()