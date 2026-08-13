"""
Salida de voz (texto -> voz) offline, usando XTTS-v2 local. 
Clona una voz a partir de un archivo .wav de muestra.
Corre en un hilo dedicado con una cola para no bloquear la telemetría.
"""
import threading
import queue
import os
import subprocess

try:
    from TTS.api import TTS
    import torch
    # --- AJUSTE DE SEGURIDAD PARA PYTORCH 2.6+ ---
    from TTS.tts.configs.xtts_config import XttsConfig
    torch.serialization.add_safe_globals([XttsConfig])
    # ---------------------------------------------
    _TTS_DISPONIBLE = True
except ImportError as e:
    print(f"⚠️ Alerta de telemetría: Error real al importar TTS: {e}")
    _TTS_DISPONIBLE = False

class SalidaDeVoz:
    def __init__(self, archivo_muestra="closs_sample.wav"):
        self.disponible = _TTS_DISPONIBLE
        self._cola = queue.Queue()
        self.archivo_muestra = archivo_muestra
        self.archivo_salida = "respuesta_ingeniero.wav"

        if not self.disponible:
            print("⚠️ Salida de voz deshabilitada: falta instalar 'TTS'. Ejecuta: pip install TTS")
            return
            
        if not os.path.exists(self.archivo_muestra):
            print(f"⚠️ Error: No se encontró el audio de muestra '{self.archivo_muestra}' para clonar la voz.")
            self.disponible = False
            return

        print("🔧 Calentando neumáticos... Cargando modelo XTTS-v2 (esto puede tardar unos segundos)...")
        
        # Desactivamos el dispositivo MPS de Apple por incompatibilidad de tensores 
        # y forzamos el uso de la CPU.
        device = "cpu"
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        
        print("✅ Motor de voz cargado y listo.")

        hilo = threading.Thread(target=self._worker, daemon=True)
        hilo.start()

    def decir(self, texto):
        if not self.disponible or not texto:
            return
        self._cola.put(texto)

    def _worker(self):
        while True:
            texto = self._cola.get()
            try:
                # 1. Genera el audio clonado y lo guarda temporalmente
                self.tts.tts_to_file(
                    text=texto,
                    speaker_wav=self.archivo_muestra,
                    language="es", # Español
                    file_path=self.archivo_salida
                )
                
                # 2. Reproduce el audio generado usando el comando nativo de Mac (afplay)
                subprocess.run(["afplay", self.archivo_salida])
                
            except Exception as e:
                print(f"⚠️ Error generando la voz clonada: {e}")
            finally:
                self._cola.task_done()