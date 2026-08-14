"""
Caché local (JSON) de los datos de circuito que antes se descargaban de FastF1
en cada sesión: el trazado (X, Y, distancia) de la vuelta más rápida y la
posición/ángulo de cada curva.

Se genera UNA sola vez con precargar_circuitos.py y de ahí en adelante se lee
directo del JSON — sin fastf1, sin pandas, sin red — lo cual ahorra bastante
RAM y tiempo en máquinas justas de memoria (el objetivo original de esto).

Si el JSON de un circuito no existe todavía, se cae a descargarlo de FastF1
en el momento (como antes) y de paso lo guarda en caché para la próxima vez.
"""
import os
import json

_DIR_BACKEND = os.path.dirname(os.path.abspath(__file__))
_DIR_PROYECTO = os.path.dirname(_DIR_BACKEND)
_DIR_CACHE_CIRCUITOS = os.path.join(_DIR_PROYECTO, "circuitos_cache")
_DIR_CACHE_FASTF1 = os.path.join(_DIR_PROYECTO, "cache_dir")


def _ruta_json(track_id):
    return os.path.join(_DIR_CACHE_CIRCUITOS, f"{track_id}.json")


def cargar_desde_cache(track_id):
    """Devuelve los datos del circuito si ya existe el JSON en caché, o None."""
    ruta = _ruta_json(track_id)
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ No se pudo leer el caché de circuito '{ruta}': {e}")
        return None


def guardar_en_cache(track_id, datos):
    os.makedirs(_DIR_CACHE_CIRCUITOS, exist_ok=True)
    ruta = _ruta_json(track_id)
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f)
        print(f"💾 Circuito guardado en caché: {ruta}")
    except Exception as e:
        print(f"⚠️ No se pudo guardar el caché de circuito '{ruta}': {e}")


def _descargar_de_fastf1(track_id, track_dict, anios=(2024, 2023, 2025, 2022)):
    """
    Descarga de FastF1 (requiere internet). Import perezoso a propósito: si el
    circuito ya está en caché, este módulo (y sus consumidores, minimapa.py y
    analisis_curvas.py) nunca necesitan cargar fastf1/pandas en memoria.

    Probamos varios años en orden: solo necesitamos el TRAZADO del circuito
    (no resultados de pilotos de una temporada puntual), y el trazado es el
    mismo año a año para el mismo circuito. Esto esquiva un bug conocido y
    documentado de FastF1 (KeyError: 'DriverNumber') que afecta puntualmente
    a los datos de las temporadas 2021 y 2022 — es un problema de la fuente
    de datos de F1, no de FastF1 ni de nuestro código (ver issues #606/#607
    en el repo de FastF1 en GitHub).
    """
    import fastf1

    os.makedirs(_DIR_CACHE_FASTF1, exist_ok=True)
    fastf1.Cache.enable_cache(_DIR_CACHE_FASTF1)

    ubicacion = track_dict.get(track_id)
    if not ubicacion:
        raise ValueError(f"track_id={track_id} no está en el diccionario de circuitos")

    ultimo_error = None
    for anio in anios:
        try:
            session = fastf1.get_session(anio, ubicacion, 'Q')
            session.load(telemetry=True, weather=False, messages=False)

            vuelta = session.laps.pick_fastest()
            telemetria_df = vuelta.get_telemetry()
            if 'Distance' not in telemetria_df.columns:
                telemetria_df = telemetria_df.add_distance()

            circuit_info = session.get_circuit_info()

            return {
                "track_id": track_id,
                "nombre": ubicacion,
                "anio_usado": anio,
                "angulo_rotacion_grados": float(circuit_info.rotation),
                "telemetria": [
                    {"x": float(x), "y": float(y), "distancia": float(d)}
                    for x, y, d in zip(telemetria_df["X"], telemetria_df["Y"], telemetria_df["Distance"])
                ],
                "curvas": sorted(
                    [{
                        "numero": int(fila.Number),
                        "distancia": float(fila.Distance),
                        "x": float(fila.X),
                        "y": float(fila.Y),
                        "angulo": float(fila.Angle),
                    } for _, fila in circuit_info.corners.iterrows()],
                    key=lambda c: c["distancia"]
                ),
            }
        except Exception as e:
            print(f"   ⚠️ Falló con temporada {anio} ({e}), probando con otra temporada...")
            ultimo_error = e
            continue

    raise ultimo_error


def obtener_datos_circuito(track_id, track_dict):
    """
    Punto de entrada único para todo el proyecto: intenta caché local primero
    (rápido, sin fastf1/pandas en memoria); si no existe, descarga de FastF1
    (requiere internet) y de paso lo cachea para la próxima vez.
    """
    datos = cargar_desde_cache(track_id)
    if datos is not None:
        return datos

    try:
        print(f"⬇️ Circuito track_id={track_id} no está en caché, descargando de FastF1 (una sola vez)...")
        datos = _descargar_de_fastf1(track_id, track_dict)
        guardar_en_cache(track_id, datos)
        return datos
    except Exception as e:
        print(f"⚠️ No se pudieron obtener los datos del circuito (ni caché ni FastF1): {e}")
        return None