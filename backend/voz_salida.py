"""
Salida de voz (texto -> voz) offline, usando pyttsx3 (motor de voz nativo del
sistema — en macOS, NSSpeechSynthesizer). Corre en un hilo dedicado con una
cola, para no bloquear la ventana de arcade y para que un mensaje no
interrumpa al anterior a medias.

OJO: en macOS, reusar la MISMA instancia del motor entre varios mensajes se
cuelga después del primer runAndWait() — es un bug conocido de pyttsx3. Por
eso acá se crea una instancia NUEVA del motor para cada mensaje.
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
        self.cargando = False          # pyttsx3 no tiene una carga pesada, siempre False
        self.generando_audio = False   # True mientras se está sintetizando/reproduciendo un mensaje
        self._cola = queue.Queue()
        self._velocidad = velocidad

        if not self.disponible:
            print("⚠️ Salida de voz deshabilitada: falta instalar el paquete 'pyttsx3'.")
            return

        hilo = threading.Thread(target=self._worker, daemon=True)
        hilo.start()

    def decir(self, texto):
        if not self.disponible or not texto:
            return
        self._cola.put(texto)

    def _worker(self):
        import subprocess
        while True:
            texto = self._cola.get()
            self.generando_audio = True
            try:
                subprocess.run(["say", texto])
            except Exception as e:
                print(f"⚠️ Error en texto a voz: {e}")
            finally:
                self.generando_audio = False