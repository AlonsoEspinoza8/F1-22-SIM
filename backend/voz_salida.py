"""
Salida de voz (texto -> voz) offline, usando pyttsx3. Corre en un hilo
dedicado con una cola, para no bloquear la ventana de arcade y para que un
mensaje no interrumpa al anterior a medias.
"""
import threading
import queue

try:
    import pyttsx3
    _PYTTSX3_DISPONIBLE = True
except ImportError:
    _PYTTSX3_DISPONIBLE = False


class SalidaDeVoz:
    def __init__(self, velocidad=175):
        self.disponible = _PYTTSX3_DISPONIBLE
        self._cola = queue.Queue()

        if not self.disponible:
            print("⚠️ Salida de voz deshabilitada: falta instalar el paquete 'pyttsx3'.")
            return

        self._velocidad = velocidad
        hilo = threading.Thread(target=self._worker, daemon=True)
        hilo.start()

    def decir(self, texto):
        if not self.disponible or not texto:
            return
        self._cola.put(texto)

    def _worker(self):
        # OJO: en macOS (driver 'nsss' de pyttsx3), reusar la MISMA instancia del
        # motor entre varios mensajes se cuelga después del primer runAndWait() —
        # es un bug conocido de pyttsx3. La solución es crear una instancia NUEVA
        # del motor para cada mensaje en vez de reutilizar una persistente.
        while True:
            texto = self._cola.get()
            try:
                motor = pyttsx3.init()
                motor.setProperty('rate', self._velocidad)
                motor.say(texto)
                motor.runAndWait()
                motor.stop()
                del motor
            except Exception as e:
                print(f"⚠️ Error en texto a voz: {e}")