"""
Colores oficiales de cada escudería, indexados por 'teamId' — el mismo id que
manda el paquete de Participants del juego (ver Team IDs en la especificación
UDP oficial de F1 22). A diferencia de FastF1 (que requiere una sesión real
cargada para mapear colores), esto funciona directo con la telemetría en vivo
del juego sin depender de internet ni de ninguna sesión externa.
"""

COLOR_POR_TEAM_ID = {
    0: (39, 244, 210),    # Mercedes
    1: (218, 41, 28),     # Ferrari
    2: (30, 65, 255),     # Red Bull Racing
    3: (55, 190, 221),    # Williams
    4: (34, 153, 113),    # Aston Martin
    5: (255, 135, 188),   # Alpine
    6: (60, 130, 200),    # AlphaTauri
    7: (182, 186, 189),   # Haas
    8: (255, 135, 0),     # McLaren
    9: (172, 32, 57),     # Alfa Romeo
    # Equipos "clásicos"/edición especial: se les da un color genérico distinto
    # entre sí para que al menos se puedan diferenciar, aunque no sean oficiales
    85: (39, 244, 210), 86: (218, 41, 28), 87: (30, 65, 255), 88: (55, 190, 221),
    89: (245, 150, 200), 90: (255, 210, 0), 91: (60, 130, 200), 92: (182, 186, 189),
    93: (255, 135, 0), 94: (172, 32, 57),
}

COLOR_POR_DEFECTO = (160, 160, 160)  # equipo desconocido / F2 / clásicos sin mapear


def color_por_team_id(team_id):
    return COLOR_POR_TEAM_ID.get(team_id, COLOR_POR_DEFECTO)


# Compuesto VISUAL de neumático (m_visualTyreCompound del paquete CarStatusData).
# Nota: es distinto del compuesto "actual" (C1-C5) — el visual solo distingue
# blando/medio/duro/intermedio/lluvia, que es lo que se muestra en pantalla en el juego.
NOMBRE_COMPUESTO = {
    16: "Blando",
    17: "Medio",
    18: "Duro",
    7: "Intermedio",
    8: "Lluvia",
}

COLOR_COMPUESTO = {
    16: (255, 60, 60),     # blando -> rojo
    17: (255, 210, 0),     # medio -> amarillo
    18: (240, 240, 240),   # duro -> blanco
    7: (60, 200, 90),      # intermedio -> verde
    8: (60, 120, 255),     # lluvia -> azul
}


def nombre_compuesto(codigo):
    return NOMBRE_COMPUESTO.get(codigo, "?")


def color_compuesto(codigo):
    return COLOR_COMPUESTO.get(codigo, (120, 120, 120))