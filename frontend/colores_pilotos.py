"""
Color estable por piloto, para que el mismo color identifique al mismo piloto
tanto en el minimapa como en el leaderboard (igual que 'driver_colors' en los
replays de FastF1: un solo color por piloto, reutilizado en toda la UI).

No tenemos los colores reales de equipo de F1 en la telemetría del juego, así
que generamos uno determinístico a partir del nombre/id del piloto: mismo
piloto -> siempre el mismo color, dentro y entre sesiones.
"""
import arcade

# Paleta con buen contraste sobre fondo oscuro (evita colores muy oscuros/grises
# que se pierden contra el fondo del panel)
_PALETA = [
    (0, 210, 255),    # celeste
    (255, 90, 90),    # rojo coral
    (120, 230, 120),  # verde
    (255, 200, 40),   # amarillo/dorado
    (200, 120, 255),  # violeta
    (255, 140, 60),   # naranja
    (90, 200, 255),   # azul claro
    (255, 110, 180),  # rosa
    (170, 220, 60),   # lima
    (140, 160, 255),  # lavanda
]


def color_para_piloto(identificador):
    """
    Devuelve una tupla RGB estable para el piloto dado (nombre, driverId, lo
    que sea, siempre que sea el mismo valor para el mismo piloto en toda la
    sesión). No es aleatorio: mismo identificador -> siempre el mismo color.
    """
    indice = hash(str(identificador)) % len(_PALETA)
    return _PALETA[indice]


COLOR_JUGADOR = arcade.color.GOLD  # el propio auto siempre se destaca igual, sin importar el hash