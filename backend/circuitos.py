"""
Mapeo ÚNICO de 'track_id' (el que manda el paquete de sesión del juego) a un
nombre que FastF1 pueda resolver sin ambigüedad.

Importante: usamos nombres de CIRCUITO, no de país. Un nombre de país puede
matchear más de un evento en una temporada dada (ej. "United States" podría
matchear Austin, Miami o Las Vegas; "Italy" podría matchear Monza o Imola),
lo que puede hacer que FastF1 resuelva el circuito equivocado — esto es lo
que causaba que, por ejemplo, Silverstone mostrara el mapa de Austria.

track_id según la especificación oficial de UDP de F1 22 (Track IDs table).
"""

FASTF1_TRACK_DICT = {
    0: "Melbourne",       # Australia
    1: "Paul Ricard",     # France (no corre desde 2022 — puede fallar en años recientes, es esperado)
    2: "Shanghai",        # China
    3: "Bahrain",         # Sakhir
    4: "Barcelona",       # España (evita ambigüedad con Madrid en calendarios nuevos)
    5: "Monaco",
    6: "Montreal",        # Canadá
    7: "Silverstone",     # Great Britain — el caso puntual que se reportó mal
    8: "Hockenheim",      # Alemania (no corre desde 2019/2020 — puede fallar, es esperado)
    9: "Hungaroring",     # Hungría
    10: "Spa",            # Bélgica
    11: "Monza",          # Italia (evita ambigüedad con Imola)
    12: "Singapore",
    13: "Suzuka",         # Japón
    14: "Abu Dhabi",
    15: "Austin",         # Estados Unidos (COTA) — evita ambigüedad con Miami/Las Vegas
    16: "Interlagos",     # Brasil
    17: "Austria",        # Red Bull Ring
    18: "Sochi",          # Rusia (no corre desde 2021 — puede fallar, es esperado)
    19: "Mexico",
    20: "Baku",           # Azerbaiyán
    26: "Zandvoort",      # Países Bajos
    27: "Imola",          # Emilia Romagna
    28: "Portimao",       # Portugal (no corre en calendarios recientes — puede fallar, es esperado)
    29: "Jeddah",         # Arabia Saudita
    30: "Miami",
}