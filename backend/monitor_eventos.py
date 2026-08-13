"""
Detecta eventos de carrera dignos de un aviso de radio automático: desgaste
de neumáticos cruzando umbrales, cambios de posición, un rival encima, o una
vuelta recién completada. Tiene un cooldown para no saturar al piloto de
avisos.
"""
import time

UMBRALES_DESGASTE = (50, 80)      # % de desgaste que dispara un aviso (una vez cada uno, por rueda)
UMBRAL_GAP_CRITICO_M = 15.0       # metros: rival encima, posible ataque
COOLDOWN_ENTRE_AVISOS_S = 25      # no más de un aviso automático cada tantos segundos


class MonitorEventos:
    def __init__(self):
        self._ultimo_aviso = 0.0
        self._umbrales_desgaste_avisados = set()   # (rueda, umbral) ya avisados esta carrera
        self._ultima_posicion = None
        self._vueltas_ya_avisadas = 0

    def revisar(self, race):
        """Devuelve un motivo (str) para generar un aviso, o None si no corresponde todavía."""
        ahora = time.time()
        if ahora - self._ultimo_aviso < COOLDOWN_ENTRE_AVISOS_S:
            return None

        yo = race.drivers.get(race.player_car_index)
        if not yo:
            return None

        # 1) Desgaste de neumáticos cruzando umbrales
        for rueda, valor in getattr(yo, 'desgaste_neumaticos', {}).items():
            for umbral in UMBRALES_DESGASTE:
                clave = (rueda, umbral)
                if valor >= umbral and clave not in self._umbrales_desgaste_avisados:
                    self._umbrales_desgaste_avisados.add(clave)
                    self._ultimo_aviso = ahora
                    return f"el neumático {rueda} llegó a {umbral}% de desgaste"

        # 2) Cambio de posición
        posicion_actual = getattr(yo, 'posicion', None)
        if posicion_actual:
            if self._ultima_posicion and posicion_actual != self._ultima_posicion:
                anterior = self._ultima_posicion
                self._ultima_posicion = posicion_actual
                self._ultimo_aviso = ahora
                verbo = "subió a" if posicion_actual < anterior else "bajó a"
                return f"el piloto {verbo} la posición {posicion_actual}"
            self._ultima_posicion = posicion_actual

        # 3) Rival justo detrás, en rango de ataque
        gaps = race.get_player_gaps() if hasattr(race, 'get_player_gaps') else None
        if gaps:
            gap_atras = gaps.get('gap_atras_m')
            if isinstance(gap_atras, (int, float)) and 0 < gap_atras < UMBRAL_GAP_CRITICO_M:
                self._ultimo_aviso = ahora
                return f"el rival de atrás ({gaps.get('piloto_atras', '-')}) está a {gap_atras:.0f} metros"

        # 4) Vuelta recién completada
        vueltas = getattr(yo, 'historial_vueltas', [])
        if len(vueltas) > self._vueltas_ya_avisadas:
            self._vueltas_ya_avisadas = len(vueltas)
            ultima = vueltas[-1]
            self._ultimo_aviso = ahora
            return (
                f"acaba de completar la vuelta {ultima.get('vuelta')} "
                f"en {ultima.get('tiempo_total_ms', 0) / 1000:.3f} segundos"
            )

        return None