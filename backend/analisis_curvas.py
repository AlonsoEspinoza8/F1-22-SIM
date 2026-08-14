"""
Análisis post-carrera: genera gráficos comparativos de velocidad, acelerador
y freno en función de la distancia recorrida, agrupados por curva (o por
zonas de curvas cercanas entre sí), comparando la mejor vuelta propia contra
la mejor vuelta de los 5 pilotos mejor clasificados.

Junto a cada gráfico se dibuja el trazado del circuito con las curvas
numeradas, resaltando la curva (o zona de curvas) que se está analizando.

Se apoya en FastF1 para conocer la posición (X, Y y distancia de vuelta) de
cada curva del circuito real, y en la telemetría por distancia que Driver ya
guarda en `mejor_vuelta_telemetria`.
"""
import os
import threading
import traceback
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Backend sin ventana: solo genera archivos PNG, no compite con la ventana de arcade
import matplotlib.pyplot as plt

from backend.circuito_cache import obtener_datos_circuito as _obtener_datos_circuito_cache


UMBRAL_AGRUPACION_M = 200   # Si dos curvas quedan a menos de esto, se grafican juntas
MARGEN_ZONA_M = 60          # Contexto extra antes/después de la(s) curva(s): frenada y salida

# Todo se ancla a la carpeta del proyecto (donde vive este archivo), NO al directorio
# desde el que se ejecuta el script — así el resultado siempre queda en el mismo lugar
# sin importar cómo se haya lanzado el juego/script.
_DIR_BACKEND = os.path.dirname(os.path.abspath(__file__))
_DIR_PROYECTO = os.path.dirname(_DIR_BACKEND)
_DIR_GRAFICOS_BASE = os.path.join(_DIR_PROYECTO, "graficos_curvas")
_ARCHIVO_LOG_ERRORES = os.path.join(_DIR_PROYECTO, "graficos_curvas", "errores.log")


def _registrar_error(mensaje):
    """Imprime el error en consola Y lo deja escrito en un .log, para poder verlo aunque no haya consola visible."""
    print(mensaje)
    try:
        os.makedirs(_DIR_GRAFICOS_BASE, exist_ok=True)
        with open(_ARCHIVO_LOG_ERRORES, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}\n")
    except Exception:
        pass  # si ni siquiera se puede escribir el log, no hay mucho más que hacer


def _rotar(xy, angulo):
    """Rota un punto o un array de puntos [n, 2] el ángulo dado (en radianes)."""
    matriz_rotacion = np.array([
        [np.cos(angulo), np.sin(angulo)],
        [-np.sin(angulo), np.cos(angulo)]
    ])
    return np.matmul(xy, matriz_rotacion)


def obtener_datos_circuito(track_id, track_dict):
    """
    Trae los datos del circuito (telemetría X/Y/distancia + curvas + rotación).
    Usa el caché local (backend/circuito_cache.py) si ya existe — así ni fastf1
    ni pandas se cargan en memoria — y si no, cae a descargarlo de FastF1.
    """
    datos = _obtener_datos_circuito_cache(track_id, track_dict)
    if not datos:
        return None

    # El caché guarda listas planas (JSON-friendly) y el ángulo en grados;
    # acá los convertimos a lo que ya usa el resto de este archivo: arrays de
    # NumPy y el ángulo en radianes.
    telemetria = datos["telemetria"]
    return {
        "curvas": datos["curvas"],
        "angulo_rotacion": datos["angulo_rotacion_grados"] / 180 * np.pi,
        "_xs": np.array([p["x"] for p in telemetria]),
        "_ys": np.array([p["y"] for p in telemetria]),
        "_dists": np.array([p["distancia"] for p in telemetria]),
    }


def agrupar_curvas(curvas, longitud_pista, umbral=UMBRAL_AGRUPACION_M, margen=MARGEN_ZONA_M):
    """
    Agrupa curvas consecutivas separadas por menos de 'umbral' metros en una
    misma zona, para que terminen en un solo gráfico en vez de uno por curva.
    """
    if not curvas:
        return []

    zonas = []
    zona_actual = [curvas[0]]

    for curva in curvas[1:]:
        distancia_anterior = zona_actual[-1]["distancia"]
        if curva["distancia"] - distancia_anterior < umbral:
            zona_actual.append(curva)
        else:
            zonas.append(zona_actual)
            zona_actual = [curva]
    zonas.append(zona_actual)

    zonas_finales = []
    for zona in zonas:
        inicio = max(0.0, zona[0]["distancia"] - margen)
        fin = min(longitud_pista, zona[-1]["distancia"] + margen)
        zonas_finales.append({"curvas": zona, "inicio": inicio, "fin": fin})

    return zonas_finales


def _filtrar_por_zona(telemetria, inicio, fin):
    """Devuelve (distancias, velocidad, acelerador, freno) dentro del rango [inicio, fin]."""
    dist, vel, acel, freno = [], [], [], []
    for muestra in telemetria:
        d = muestra["distancia"]
        if inicio <= d <= fin:
            dist.append(d)
            vel.append(muestra["velocidad"])
            acel.append(muestra["acelerador"])
            freno.append(muestra["freno"])
    return dist, vel, acel, freno


def _dibujar_mapa_circuito(ax, datos_circuito, zona):
    """
    Dibuja el trazado completo del circuito con todas las curvas numeradas,
    resaltando en rojo el tramo y las curvas correspondientes a 'zona'.
    """
    xs, ys, dists = datos_circuito["_xs"], datos_circuito["_ys"], datos_circuito["_dists"]
    angulo = datos_circuito["angulo_rotacion"]
    numeros_zona = {c["numero"] for c in zona["curvas"]}

    # Trazado completo, en gris
    pista = np.column_stack([xs, ys])
    pista_rotada = _rotar(pista, angulo)
    ax.plot(pista_rotada[:, 0], pista_rotada[:, 1], color="dimgray", linewidth=1.5, zorder=1)

    # Tramo de pista de la zona analizada, resaltado
    mascara = (dists >= zona["inicio"]) & (dists <= zona["fin"])
    if mascara.any():
        segmento_xy = _rotar(np.column_stack([xs[mascara], ys[mascara]]), angulo)
        ax.plot(segmento_xy[:, 0], segmento_xy[:, 1], color="red", linewidth=4,
                solid_capstyle="round", zorder=2)

    # Marcadores de curva: cada uno con su propio ángulo de "salida" respecto a la pista
    offset_vector = np.array([500.0, 0.0])
    for curva in datos_circuito["curvas"]:
        es_zona = curva["numero"] in numeros_zona
        color = "red" if es_zona else "gray"

        offset_angulo = curva["angulo"] / 180 * np.pi
        offset_x, offset_y = _rotar(offset_vector, offset_angulo)

        texto_x, texto_y = _rotar(np.array([curva["x"] + offset_x, curva["y"] + offset_y]), angulo)
        pista_x, pista_y = _rotar(np.array([curva["x"], curva["y"]]), angulo)

        ax.plot([pista_x, texto_x], [pista_y, texto_y], color=color, linewidth=1, zorder=2)
        ax.scatter([texto_x], [texto_y], color=color, s=160 if es_zona else 110, zorder=3)
        ax.text(texto_x, texto_y, str(curva["numero"]), color="white", va="center_baseline",
                ha="center", size="small", weight="bold", zorder=4)

    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Trazado del circuito", fontsize=10)


def _carpeta_para_esta_sesion(race, carpeta_base=None):
    """
    Arma automáticamente: graficos_curvas/<Circuito>/<fecha_hora>/
    Un subdirectorio por circuito, y dentro de cada uno, uno por sesión (fecha y hora).
    """
    if carpeta_base is None:
        carpeta_base = _DIR_GRAFICOS_BASE

    nombre_circuito = getattr(race, 'track_name', None) or race.FASTF1_TRACK_DICT.get(race.track_id, f"Track_{race.track_id}")
    nombre_circuito = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in nombre_circuito).strip().replace(" ", "_")

    marca_tiempo = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    return os.path.join(carpeta_base, nombre_circuito, marca_tiempo)


def generar_graficos(race, carpeta_salida=None):
    """
    Genera un PNG por cada zona de curvas: a la izquierda, velocidad/acelerador/freno
    comparando la mejor vuelta del jugador contra la mejor vuelta de los 5 pilotos
    mejor clasificados; a la derecha, el trazado del circuito con la zona resaltada.

    Los archivos se guardan en graficos_curvas/<Circuito>/<fecha_hora>/, generado
    automáticamente, salvo que se indique explícitamente 'carpeta_salida'.
    """
    print("🔍 Carrera finalizada: iniciando análisis de curvas en segundo plano...")
    try:
        _generar_graficos_interno(race, carpeta_salida)
    except Exception:
        _registrar_error(f"❌ El análisis de curvas falló inesperadamente:\n{traceback.format_exc()}")


def _generar_graficos_interno(race, carpeta_salida):
    if carpeta_salida is None:
        carpeta_salida = _carpeta_para_esta_sesion(race)

    os.makedirs(carpeta_salida, exist_ok=True)

    yo = race.drivers.get(race.player_car_index)
    if not yo or not getattr(yo, 'mejor_vuelta_telemetria', None):
        _registrar_error("⚠️ Todavía no hay una vuelta propia registrada, no se generan gráficos.")
        return

    top5 = [p for p in race.get_top_pilotos(5) if p.car_index != race.player_car_index]

    datos_circuito = obtener_datos_circuito(race.track_id, race.FASTF1_TRACK_DICT)
    if not datos_circuito:
        _registrar_error("⚠️ No se pudo descargar el circuito, no se generan gráficos.")
        return

    zonas = agrupar_curvas(datos_circuito["curvas"], race.longitud_pista)
    if not zonas:
        _registrar_error("⚠️ No se pudo determinar la ubicación de las curvas del circuito.")
        return

    colores_rivales = ["red", "cyan", "magenta", "lime", "orange"]
    pilotos_a_comparar = [("Yo", yo, "gold")]
    for i, piloto in enumerate(top5):
        if getattr(piloto, 'mejor_vuelta_telemetria', None):
            pilotos_a_comparar.append((piloto.nombre, piloto, colores_rivales[i % len(colores_rivales)]))

    for idx, zona in enumerate(zonas, start=1):
        numeros_curvas = "-".join(str(c["numero"]) for c in zona["curvas"])

        fig = plt.figure(figsize=(14, 8))
        gs = fig.add_gridspec(3, 2, width_ratios=[2, 1])
        ax_vel = fig.add_subplot(gs[0, 0])
        ax_acel = fig.add_subplot(gs[1, 0], sharex=ax_vel)
        ax_freno = fig.add_subplot(gs[2, 0], sharex=ax_vel)
        ax_mapa = fig.add_subplot(gs[:, 1])
        ejes_telemetria = [ax_vel, ax_acel, ax_freno]

        fig.suptitle(f"Curva(s) {numeros_curvas}  |  {zona['inicio']:.0f}m - {zona['fin']:.0f}m")

        hubo_datos = False
        for nombre, piloto, color in pilotos_a_comparar:
            dist, vel, acel, freno = _filtrar_por_zona(piloto.mejor_vuelta_telemetria, zona["inicio"], zona["fin"])
            if not dist:
                continue
            hubo_datos = True
            ax_vel.plot(dist, vel, label=nombre, color=color)
            ax_acel.plot(dist, acel, label=nombre, color=color)
            ax_freno.plot(dist, freno, label=nombre, color=color)

        if not hubo_datos:
            plt.close(fig)
            continue

        for curva in zona["curvas"]:
            for eje in ejes_telemetria:
                eje.axvline(curva["distancia"], color="gray", linestyle="--", linewidth=0.8)

        for eje in ejes_telemetria:
            eje.set_xlim(zona["inicio"], zona["fin"])

        ax_vel.set_ylabel("Velocidad (km/h)")
        ax_acel.set_ylabel("Acelerador")
        ax_freno.set_ylabel("Freno")
        ax_freno.set_xlabel("Distancia de vuelta (m)")
        ax_vel.legend(loc="lower right", fontsize=8)

        _dibujar_mapa_circuito(ax_mapa, datos_circuito, zona)

        plt.tight_layout()
        nombre_archivo = os.path.join(carpeta_salida, f"curva_{idx}_{numeros_curvas}.png")
        plt.savefig(nombre_archivo, dpi=120)
        plt.close(fig)

    print(f"✅ Gráficos de curvas guardados en '{os.path.abspath(carpeta_salida)}'")


def generar_graficos_async(race, carpeta_salida=None):
    """Lanza la generación de gráficos en un hilo aparte para no congelar la ventana de arcade."""
    hilo = threading.Thread(target=generar_graficos, args=(race, carpeta_salida))
    hilo.start()