import os
from collections import deque

try:
    import requests
    _REQUESTS_DISPONIBLE = True
except ImportError:
    _REQUESTS_DISPONIBLE = False


# --- Personalización ---
APODO_PILOTO = "Lonchi"        
MODELO = "llama3.2:3b"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MAX_PALABRAS_RESPUESTA = 40

PROMPT_SISTEMA = f"""Eres el ingeniero de pista de un piloto en una simulación de carreras (F1 22),
con estilo Peter Bonnington con Lewis Hamilton.

Te diriges al piloto como "{APODO_PILOTO}". Vas a recibir un resumen del estado actual
de la carrera y debes responder con UN SOLO mensaje de radio, imitando el patrón de
los ejemplos de abajo (tono, jerga, largo).

REGLA IMPORTANTE: tu respuesta completa debe tener COMO MÁXIMO {MAX_PALABRAS_RESPUESTA}
PALABRAS — un par de frases como mucho, nunca una explicación larga.

MUY IMPORTANTE sobre los datos que recibís:
- La carrera tiene un número de vueltas TOTAL fijo. Nunca digas que la carrera
  terminó, ni felicites al piloto por terminarla, A MENOS que el resumen diga
  EXPLÍCITAMENTE "La carrera acaba de terminar". Si no dice eso, la carrera
  sigue en curso, sin importar en qué vuelta vayan.
- "Rival ADELANTE" es el auto que el piloto tiene que ALCANZAR (va ganando esa
  posición). "Rival ATRÁS" es el que puede ALCANZAR y PASAR al piloto. No los
  confundas ni los intercambies.

No uses emojis. No uses markdown. No repitas números crudos innecesariamente —
redondea y prioriza lo que el piloto necesita saber AHORA.
"""


EJEMPLOS_ESTILO = [
    ("Dale al piloto un aviso breve por radio sobre esto: el neumático delantero izquierdo llegó a 80% de desgaste.",
     "Copiado. Delantero izquierdo al límite."),
    
    ("El piloto pregunta por radio: \"cómo van los tiempos?\". Respóndele directamente.",
     "Ritmo sólido. Sector dos es tu fuerte."),
    
    ("Dale al piloto un aviso breve por radio sobre esto: el rival de atrás está a 1.2 segundos.",
     "Rival a 1.2s. Fuera de zona de DRS."),
    
    ("Indícale al piloto que es el momento de empujar al máximo.",
     "Ok, it's Hammer time. Máximo ritmo."),
    
    ("Pídele al piloto que entre a boxes en esta vuelta para cambiar a neumáticos duros.",
     "Box, box. Confirma box para duros."),
    
    ("Adviértele al piloto que tenga cuidado con los límites de pista en la curva 4, ya tiene dos avisos.",
     "Límites curva 4. Ya van dos avisos."),
    
    ("Informa al piloto que se espera lluvia ligera en unos 5 minutos.",
     "Lluvia ligera en 5 minutos. Clase 1."),
    
    ("Pide al piloto que cambie el mapa del motor para recargar batería.",
     "Estrat 8, por favor. Recarga batería."),
    
    ("Felicita al piloto porque acaba de ganar la carrera y hacer un gran trabajo.",
     "Get in there! Fantástico trabajo hoy."),
    
    ("El piloto se queja por radio de que el auto rebota mucho y los neumáticos no van a aguantar.",
     "Copiado. Aguanta tres vueltas más.")
]

def _armar_mensajes_con_ejemplos(instruccion_actual, contexto_actual, historial):
    mensajes = [{"role": "system", "content": PROMPT_SISTEMA}]
    for pregunta_ejemplo, respuesta_ejemplo in EJEMPLOS_ESTILO:
        mensajes.append({"role": "user", "content": pregunta_ejemplo})
        mensajes.append({"role": "assistant", "content": respuesta_ejemplo})
    mensajes += list(historial)
    mensajes.append({"role": "user", "content": f"Estado actual de la carrera: {contexto_actual}\n\n{instruccion_actual}"})
    return mensajes


def _recortar_respuesta(texto, max_palabras=MAX_PALABRAS_RESPUESTA):
    """
    Red de seguridad, ahora mucho más permisiva que antes: solo corta si el
    modelo se manda un párrafo entero. Preferimos cortar en un límite de
    oración para no dejar la frase (ni el audio) a la mitad.
    """
    palabras = texto.split()
    if len(palabras) <= max_palabras:
        return texto

    recortado = " ".join(palabras[:max_palabras])
    for separador in (". ", "! ", "? "):
        idx = recortado.rfind(separador)  # el ÚLTIMO separador dentro del límite, no el primero
        if idx != -1:
            return recortado[:idx + 1]
    return recortado.rstrip(",;:") + "."


def _formatear_gap(metros, velocidad_kmh):
    """
    Convierte un gap en metros a una aproximación en segundos, usando la
    velocidad actual del piloto (como referencia — no es un gap de F1 oficial
    calculado con transponders, pero da una idea mucho más intuitiva que
    metros crudos para un mensaje de radio hablado).
    """
    velocidad_ms = max(velocidad_kmh, 30) / 3.6  # pisamos un mínimo para evitar división por ~0 al estar parado
    segundos = metros / velocidad_ms
    return f"{segundos:.1f} segundos"


class IngenieroDeVoz:
    def __init__(self):
        self.disponible = False

        if not _REQUESTS_DISPONIBLE:
            print("⚠️ Ingeniero de voz deshabilitado: falta instalar el paquete 'requests'.")
        else:
            self.disponible = self._verificar_ollama()

        # Contexto reciente de la conversación (para que las respuestas tengan continuidad)
        self.historial_mensajes = deque(maxlen=8)

    def _verificar_ollama(self):
        """Chequea que Ollama esté corriendo y que el modelo elegido esté descargado."""
        try:
            resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
            resp.raise_for_status()
            modelos = [m["name"] for m in resp.json().get("models", [])]

            # Ollama a veces guarda el nombre con o sin el sufijo ":latest"/tag exacto
            if not any(MODELO == m or m.startswith(MODELO.split(":")[0] + ":") for m in modelos):
                print(
                    f"⚠️ Ingeniero de voz deshabilitado: el modelo '{MODELO}' no está descargado. "
                    f"Corré: ollama pull {MODELO}"
                )
                return False
            return True
        except requests.exceptions.ConnectionError:
            print(
                "⚠️ Ingeniero de voz deshabilitado: no se pudo conectar a Ollama en "
                f"{OLLAMA_URL}. ¿Está abierta la app de Ollama?"
            )
            return False
        except Exception as e:
            print(f"⚠️ Ingeniero de voz deshabilitado: error consultando Ollama: {e}")
            return False

    def _resumen_carrera(self, race):
        """Arma, en texto plano, el estado actual de la carrera para dárselo a la IA."""
        yo = race.drivers.get(race.player_car_index)
        if not yo:
            return "Sin datos de telemetría todavía."

        gaps = race.get_player_gaps() if hasattr(race, 'get_player_gaps') else None
        gaps = gaps or {}
        desgaste = getattr(yo, 'desgaste_neumaticos', {}) or {}
        vueltas = getattr(yo, 'historial_vueltas', [])
        ultima_vuelta = vueltas[-1] if vueltas else None
        velocidad_actual = getattr(yo, 'velocidad', 0) or 0

        total_vueltas = getattr(race, 'total_vueltas', 0)
        vuelta_actual = getattr(yo, 'vuelta_actual', len(vueltas) + 1)
        info_vueltas = (
            f"Vuelta {vuelta_actual} de {total_vueltas} totales."
            if total_vueltas else f"Vuelta {vuelta_actual}."
        )

        partes = [
            f"Posición actual: P{getattr(yo, 'posicion', '?')}.",
            info_vueltas,
            (
                f"Rival ADELANTE (el que el piloto tiene que alcanzar): {gaps.get('piloto_adelante', '-')}, "
                f"a {_formatear_gap(gaps.get('gap_adelante_m', 0), velocidad_actual)}."
            ),
            (
                f"Rival ATRÁS (el que puede alcanzar y pasar al piloto): {gaps.get('piloto_atras', '-')}, "
                f"a {_formatear_gap(gaps.get('gap_atras_m', 0), velocidad_actual)}."
            ),
            (
                f"Desgaste de neumáticos: delantero izq {desgaste.get('FL', 0):.0f}%, "
                f"delantero der {desgaste.get('FR', 0):.0f}%, "
                f"trasero izq {desgaste.get('RL', 0):.0f}%, "
                f"trasero der {desgaste.get('RR', 0):.0f}%."
            ),
        ]
        if ultima_vuelta:
            partes.append(
                f"Última vuelta: {ultima_vuelta.get('tiempo_total_ms', 0) / 1000:.3f} segundos."
            )

        # Solo mencionamos el fin de carrera si REALMENTE terminó — si no, ni se nombra,
        # para no darle al modelo la oportunidad de alucinar con el tema.
        if getattr(race, 'carrera_terminada', False):
            partes.append("La carrera acaba de terminar.")

        return " ".join(partes)

    def _generar(self, race, instruccion):
        if not self.disponible:
            return None
        try:
            contexto = self._resumen_carrera(race)
            mensajes = _armar_mensajes_con_ejemplos(instruccion, contexto, self.historial_mensajes)

            respuesta = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODELO,
                    "messages": mensajes,
                    "stream": False,
                    "options": {"num_predict": 100, "temperature": 0.2},
                },
                timeout=30,
            )
            respuesta.raise_for_status()
            texto = respuesta.json().get("message", {}).get("content", "").strip()
            texto = _recortar_respuesta(texto)

            self.historial_mensajes.append({"role": "user", "content": instruccion})
            self.historial_mensajes.append({"role": "assistant", "content": texto})

            return texto or None
        except Exception as e:
            print(f"⚠️ Error generando mensaje del ingeniero (Ollama): {e}")
            return None

    def aviso_automatico(self, race, motivo):
        """motivo: p. ej. 'el neumático delantero izquierdo llegó a 80% de desgaste'."""
        return self._generar(race, f"Dale al piloto un aviso breve por radio sobre esto: {motivo}.")

    def responder_pregunta(self, race, pregunta):
        return self._generar(race, f'El piloto pregunta por radio: "{pregunta}". Respóndele directamente.')