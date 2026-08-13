"""
Entrada de voz. Dos modos, que conviven:

1) ESCUCHA CONTINUA CON PALABRA DE ACTIVACIÓN (modo principal, tipo "oye Siri"):
   el micrófono queda escuchando solo; cuando detecta que empezaste a hablar,
   graba automáticamente hasta que te quedas en silencio (usa la detección de
   voz de SpeechRecognition, no hace falta mantener nada presionado). Si la
   frase reconocida empieza con la palabra de activación (por defecto
   "ingeniero"), se dispara el comando.

2) PUSH-TO-TALK manual (respaldo): mantener presionada una tecla/botón y
   soltarla para enviar. Útil si el ambiente es muy ruidoso y la palabra de
   activación no se reconoce bien.

Todo el reconocimiento corre en hilos aparte, para no bloquear la ventana de
arcade. Requiere los paquetes 'SpeechRecognition' y 'PyAudio'.
"""
import threading

try:
    import speech_recognition as sr
    _SR_DISPONIBLE = True
except ImportError:
    _SR_DISPONIBLE = False


class EntradaDeVoz:
    def __init__(self, idioma="es-CL", palabra_activacion="ingeniero"):
        self.disponible = _SR_DISPONIBLE
        self.idioma = idioma
        self.palabra_activacion = palabra_activacion.lower().strip()

        self.grabando = False          # estado del push-to-talk manual
        self.escuchando = False        # True mientras el modo continuo está activo
        self.procesando_frase = False  # True mientras se reconoce/despacha una frase detectada

        self._reconocedor = None
        self._microfono = None
        self._frames = []
        self._hilo_grabacion = None
        self._detener_escucha_continua = None

        if not self.disponible:
            print("⚠️ Entrada de voz deshabilitada: falta instalar 'SpeechRecognition' (y 'PyAudio').")
            return

        self._reconocedor = sr.Recognizer()
        try:
            self._microfono = sr.Microphone()
        except Exception as e:
            print(f"⚠️ No se pudo inicializar el micrófono: {e}")
            self.disponible = False

    # ------------------------------------------------------------------
    # MODO 1: escucha continua con palabra de activación
    # ------------------------------------------------------------------
    def iniciar_escucha_continua(self, on_comando_reconocido):
        """
        Empieza a escuchar en segundo plano de forma indefinida.
        on_comando_reconocido(comando, frase_completa) se llama cuando se detecta
        una frase que empieza con la palabra de activación. 'comando' viene SIN
        la palabra de activación; 'frase_completa' es la transcripción tal cual.
        """
        if not self.disponible or self._detener_escucha_continua is not None:
            return
        try:
            with self._microfono as fuente:
                self._reconocedor.adjust_for_ambient_noise(fuente, duration=1)

            self.escuchando = True
            self._detener_escucha_continua = self._reconocedor.listen_in_background(
                self._microfono,
                lambda reconocedor, audio: self._on_frase_detectada(reconocedor, audio, on_comando_reconocido),
                phrase_time_limit=8,
            )
            print(f"🎙️ Escucha continua activa. Decí: '{self.palabra_activacion}, <tu pregunta>'.")
        except Exception as e:
            print(f"⚠️ No se pudo iniciar la escucha continua: {e}")
            self.escuchando = False

    def detener_escucha_continua(self):
        if self._detener_escucha_continua:
            self._detener_escucha_continua(wait_for_stop=False)
            self._detener_escucha_continua = None
        self.escuchando = False

    def _on_frase_detectada(self, reconocedor, audio, on_comando_reconocido):
        # Se ejecuta en el hilo propio de listen_in_background: despachamos a OTRO
        # hilo enseguida para no bloquear la detección de la siguiente frase mientras
        # esta se reconoce (llamada de red) y se procesa.
        threading.Thread(
            target=self._reconocer_y_despachar,
            args=(reconocedor, audio, on_comando_reconocido),
            daemon=True,
        ).start()

    def _reconocer_y_despachar(self, reconocedor, audio, on_comando_reconocido):
        self.procesando_frase = True
        try:
            texto = reconocedor.recognize_google(audio, language=self.idioma).strip()
        except sr.UnknownValueError:
            texto = ""
        except Exception as e:
            print(f"⚠️ Error de reconocimiento de voz: {e}")
            texto = ""
        finally:
            self.procesando_frase = False

        if not texto:
            return

        texto_normalizado = texto.lower()
        if self.palabra_activacion not in texto_normalizado:
            return  # no era para el ingeniero, ignoramos (ruido, radio del juego, conversación, etc.)

        idx = texto_normalizado.index(self.palabra_activacion) + len(self.palabra_activacion)
        comando = texto[idx:].strip(" ,.:;¿?¡!")
        on_comando_reconocido(comando or texto, texto)

    # ------------------------------------------------------------------
    # MODO 2: push-to-talk manual (respaldo)
    # ------------------------------------------------------------------
    def iniciar_grabacion(self):
        """Llamar al PRESIONAR la tecla/botón de push-to-talk."""
        if not self.disponible or self.grabando:
            return
        self.grabando = True
        self._frames = []
        self._hilo_grabacion = threading.Thread(target=self._loop_grabacion, daemon=True)
        self._hilo_grabacion.start()

    def _loop_grabacion(self):
        try:
            with self._microfono as fuente:
                stream = fuente.stream
                while self.grabando:
                    self._frames.append(stream.read(fuente.CHUNK, exception_on_overflow=False))
        except Exception as e:
            print(f"⚠️ Error grabando audio: {e}")

    def detener_grabacion_y_reconocer(self, on_texto_reconocido):
        """
        Llamar al SOLTAR la tecla/botón de push-to-talk. Corta la grabación y hace
        el reconocimiento en un hilo aparte; 'on_texto_reconocido(texto)' se llama
        cuando (si) hay resultado.
        """
        if not self.disponible:
            return
        self.grabando = False

        def _cerrar_y_reconocer():
            if self._hilo_grabacion:
                self._hilo_grabacion.join(timeout=2)
            self._reconocer_push_to_talk(on_texto_reconocido)

        threading.Thread(target=_cerrar_y_reconocer, daemon=True).start()

    def _reconocer_push_to_talk(self, on_texto_reconocido):
        if not self._frames:
            return
        audio_data = sr.AudioData(
            b"".join(self._frames),
            self._microfono.SAMPLE_RATE,
            self._microfono.SAMPLE_WIDTH,
        )
        try:
            texto = self._reconocedor.recognize_google(audio_data, language=self.idioma)
            if texto:
                on_texto_reconocido(texto)
        except sr.UnknownValueError:
            pass
        except Exception as e:
            print(f"⚠️ Error de reconocimiento de voz: {e}")