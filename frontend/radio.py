import arcade
from frontend.base import PanelUI


class RadioPanel(PanelUI):
    """Muestra el historial reciente de mensajes de radio (ingeniero <-> piloto) y el estado del micrófono."""

    def draw(self, mensajes, grabando_manual=False, procesando=False, escuchando=False, palabra_activacion="ingeniero"):
        cx, cy = 625, 70
        ancho, alto = 1180, 120
        self.dibujar_recuadro_universal(cx, cy, ancho, alto, arcade.color.GRAY)

        izq = cx - ancho / 2 + 12
        arriba = cy + alto / 2 - 18

        arcade.draw_text("Radio", izq, arriba, arcade.color.WHITE, 12, bold=True)

        # Estado del micrófono, a la derecha del título
        if grabando_manual:
            estado, color = "● GRABANDO (soltá para enviar)", arcade.color.RED
        elif procesando:
            estado, color = "Procesando...", arcade.color.ORANGE
        elif escuchando:
            estado, color = f"🎙️ Escuchando (decí: '{palabra_activacion}, ...')", arcade.color.GREEN
        else:
            estado, color = "Micrófono no disponible", arcade.color.GRAY

        arcade.draw_text(estado, izq + 80, arriba, color, 11, bold=grabando_manual or procesando)

        if not mensajes:
            arcade.draw_text(
                f"Decí '{palabra_activacion}' seguido de tu pregunta para hablar con el ingeniero.",
                izq, arriba - 30, arcade.color.LIGHT_GRAY, 11
            )
            return

        # Mostramos los últimos mensajes, más reciente abajo
        y = arriba - 26
        for hablante, texto in mensajes[-3:]:
            es_ingeniero = (hablante == "Ingeniero")
            color_msg = arcade.color.YELLOW if es_ingeniero else arcade.color.LIGHT_BLUE
            arcade.draw_text(f"{hablante}: {texto}", izq, y, color_msg, 11, width=int(ancho - 24))
            y -= 26