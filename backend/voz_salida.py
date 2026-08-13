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
        try:
            motor = pyttsx3.init()
            motor.setProperty('rate', self._velocidad)
        except Exception as e:
            print(f"⚠️ No se pudo inicializar el motor de voz (pyttsx3): {e}")
            self.disponible = False
            return

        while True:
            texto = self._cola.get()
            try:
                motor.say(texto)
                motor.runAndWait()
            except Exception as e:
                print(f"⚠️ Error en texto a voz: {e}")