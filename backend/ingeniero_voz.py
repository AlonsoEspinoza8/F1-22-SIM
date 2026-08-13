"""
Ingeniero de pista con IA: genera los mensajes de radio (avisos automáticos y
respuestas a preguntas) a partir del estado actual de la carrera.

Estilo inspirado en la radio de boxes profesional: frases cortas, tono
calmado y directo, sin relleno. Es un personaje genérico (no simula a
ninguna persona real) — puedes personalizar su nombre y el apodo con el
que se dirige al piloto más abajo.

Usa la API de Anthropic (Claude) como "cerebro". Requiere la librería
`anthropic` y la variable de entorno ANTHROPIC_API_KEY.
"""
import os
from collections import deque

try:
    import anthropic
    _ANTHROPIC_DISPONIBLE = True
except ImportError:
    _ANTHROPIC_DISPONIBLE = False


# --- Personalización ---
APODO_PILOTO = "Piloto"          # Cómo te llama el ingeniero. Cámbialo por tu nombre/apodo si quieres.
MODELO = "claude-haiku-4-5-20251001"  # Rápido y económico; suficiente para frases cortas de radio

PROMPT_SISTEMA = f"""Eres el ingeniero de pista de un piloto en una simulación de carreras (F1 22).
Hablas por radio durante la carrera: frases cortas (1 a 2 oraciones), tono calmado,
profesional y directo — como la radio de boxes real, sin exclamaciones exageradas
ni relleno innecesario.

Te diriges al piloto como "{APODO_PILOTO}". Vas a recibir un resumen del estado actual
de la carrera (posición, gaps a los rivales, desgaste de neumáticos, últimos tiempos)
y debes responder con UN SOLO mensaje de radio.

No uses emojis. No uses markdown. No repitas números crudos innecesariamente —
redondea y prioriza lo que el piloto necesita saber AHORA. Si la información es
positiva, dilo con calma igual; si es una advertencia, sé directo y claro.
"""


class IngenieroDeVoz:
    def __init__(self):
        self.disponible = _ANTHROPIC_DISPONIBLE and bool(os.environ.get("ANTHROPIC_API_KEY"))
        self.cliente = None

        if not _ANTHROPIC_DISPONIBLE:
            print("⚠️ Ingeniero de voz deshabilitado: falta instalar el paquete 'anthropic'.")
        elif not os.environ.get("ANTHROPIC_API_KEY"):
            print("⚠️ Ingeniero de voz deshabilitado: falta la variable de entorno ANTHROPIC_API_KEY.")
        else:
            self.cliente = anthropic.Anthropic()

        # Contexto reciente de la conversación (para que las respuestas tengan continuidad)
        self.historial_mensajes = deque(maxlen=8)

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
            mensajes = list(self.historial_mensajes) + [
                {"role": "user", "content": f"Estado actual de la carrera: {contexto}\n\n{instruccion}"}
            ]

            respuesta = self.cliente.messages.create(
                model=MODELO,
                max_tokens=120,
                system=PROMPT_SISTEMA,
                messages=mensajes,
            )
            texto = "".join(bloque.text for bloque in respuesta.content if bloque.type == "text").strip()

            self.historial_mensajes.append({"role": "user", "content": instruccion})
            self.historial_mensajes.append({"role": "assistant", "content": texto})

            return texto or None
        except Exception as e:
            print(f"⚠️ Error generando mensaje del ingeniero: {e}")
            return None

    def aviso_automatico(self, race, motivo):
        """motivo: p. ej. 'el neumático delantero izquierdo llegó a 80% de desgaste'."""
        return self._generar(race, f"Dale al piloto un aviso breve por radio sobre esto: {motivo}.")

    def responder_pregunta(self, race, pregunta):
        return self._generar(race, f'El piloto pregunta por radio: "{pregunta}". Respóndele directamente.')