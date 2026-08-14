"""
Ingeniero de pista con IA: genera los mensajes de radio (avisos automáticos y
respuestas a preguntas) a partir del estado actual de la carrera.

Estilo inspirado en la radio de boxes profesional: frases cortas, tono
calmado y directo, sin relleno. Es un personaje genérico (no simula a
ninguna persona real) — puedes personalizar su nombre y el apodo con el
que se dirige al piloto más abajo.

Usa Ollama (https://ollama.com) como "cerebro", corriendo 100% local — sin
costo, sin API key, sin internet. Necesitás:
  1) Tener la app de Ollama abierta (o el servicio corriendo en background).
  2) Haber descargado el modelo una vez: ollama pull llama3.2:3b
"""


import os
from collections import deque

try:
    import requests
    _REQUESTS_DISPONIBLE = True
except ImportError:
    _REQUESTS_DISPONIBLE = False


# --- Personalización ---
APODO_PILOTO = "Lonchi"           # Cómo te llama el ingeniero. Cámbialo por tu nombre/apodo si quieres.
MODELO = "llama3.2:3b"             # Liviano (~1.3GB); clave en Macs de 8GB si además corre XTTS-v2 a la vez.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")

# Límite duro de longitud: cada palabra de más son varios segundos extra de
# síntesis de voz en XTTS-v2 corriendo en CPU (44s+ para un mensaje largo).
MAX_PALABRAS_RESPUESTA = 15

PROMPT_SISTEMA = f"""Eres el ingeniero de pista de un piloto en una simulación de carreras (F1 22),
como Peter Bonnington con Lewis Hamilton, pero sin imitar a nadie en particular. Tu trabajo es
dar avisos breves y claros por radio, y responder preguntas del piloto de manera directa.
Te diriges al piloto como "{APODO_PILOTO}". Cuando haga un adelantamiento, felicítalo."""

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

        partes = [
            f"Posición actual: P{getattr(yo, 'posicion', '?')}.",
            f"Rival adelante: {gaps.get('piloto_adelante', '-')}, a {gaps.get('gap_adelante_m', 0):.0f} metros.",
            f"Rival atrás: {gaps.get('piloto_atras', '-')}, a {gaps.get('gap_atras_m', 0):.0f} metros.",
            (
                f"Desgaste de neumáticos: delantero izq {desgaste.get('FL', 0):.0f}%, "
                f"delantero der {desgaste.get('FR', 0):.0f}%, "
                f"trasero izq {desgaste.get('RL', 0):.0f}%, "
                f"trasero der {desgaste.get('RR', 0):.0f}%."
            ),
            f"Vueltas completadas: {len(vueltas)}.",
        ]
        if ultima_vuelta:
            partes.append(
                f"Última vuelta: {ultima_vuelta.get('tiempo_total_ms', 0) / 1000:.3f} segundos."
            )
        if getattr(race, 'carrera_terminada', False):
            partes.append("La carrera acaba de terminar.")

        return " ".join(partes)

    def _generar(self, race, instruccion):
        if not self.disponible:
            return None
        try:
            contexto = self._resumen_carrera(race)
            mensaje_usuario = f"Estado actual de la carrera: {contexto}\n\n{instruccion}"

            mensajes = (
                [{"role": "system", "content": PROMPT_SISTEMA}]
                + list(self.historial_mensajes)
                + [{"role": "user", "content": mensaje_usuario}]
            )

            respuesta = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": MODELO,
                    "messages": mensajes,
                    "stream": False,
                    "options": {"num_predict": 40, "temperature": 0.1},
                },
                timeout=30,
            )
            respuesta.raise_for_status()
            texto = respuesta.json().get("message", {}).get("content", "").strip()

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