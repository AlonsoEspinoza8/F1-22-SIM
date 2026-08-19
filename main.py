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