import arcade
from frontend.base import PanelUI


class RadioPanel(PanelUI):
    """Muestra el historial reciente de mensajes de radio (ingeniero <-> piloto) y el estado del micrófono."""

    def draw(self, mensajes, grabando_manual=False, procesando=False, escuchando=False, palabra_activacion="ingeniero"):
        cx, cy = 670, 160
        ancho, alto = 455, 135
        self.dibujar_recuadro_universal(cx, cy, ancho, alto, arcade.color.GRAY)

        izq = cx - ancho / 2 + 12
        arriba = cy + alto / 2 - 16

        arcade.draw_text("Chat With Engineer", izq, arriba, arcade.color.WHITE, 12, bold=True)

        # Estado del micrófono, en su propia línea (el panel es angosto)
        if grabando_manual:
            estado, color = "● GRABANDO (soltá para enviar)", arcade.color.RED
        elif procesando:
            estado, color = "Procesando...", arcade.color.ORANGE
        elif escuchando:
            estado, color = f"🎙️ Escuchando (decí: '{palabra_activacion}, ...')", arcade.color.GREEN
        else:
            estado, color = "Micrófono no disponible", arcade.color.GRAY

        arcade.draw_text(estado, izq, arriba - 20, color, 10, bold=grabando_manual or procesando)

        if not mensajes:
            arcade.draw_text(
                f"Decí '{palabra_activacion}' seguido de tu pregunta.",
                izq, arriba - 42, arcade.color.LIGHT_GRAY, 10
            )
            return

        # Mostramos los últimos 2 mensajes (panel más bajo que antes), más reciente abajo
        y = arriba - 44
        for hablante, texto in mensajes[-2:]:
            es_ingeniero = (hablante == "Ingeniero")
            color_msg = arcade.color.YELLOW if es_ingeniero else arcade.color.LIGHT_BLUE
            arcade.draw_text(f"{hablante}: {texto}", izq, y, color_msg, 10, width=int(ancho - 24))
            y -= 20