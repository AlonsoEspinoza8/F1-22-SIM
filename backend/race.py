import socket
import struct
import time
from tabulate import tabulate
import traceback
from backend.circuitos import FASTF1_TRACK_DICT

class Race:
    def __init__(self):
        self.udp_ip = "0.0.0.0"
        self.udp_port = 20777
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.udp_ip, self.udp_port))
        self.sock.setblocking(False) 
        
        self.header_format = "<H4BQfIBB"
        self.header_size = 24
        
        self.drivers = {} 
        self.player_car_index = 0
        self.track_name = "Esperando..."
        self.track_id = -1
        self.longitud_pista = 5000.0
        self.total_vueltas = 0

        # --- ESTADO DE LA SESIÓN / FIN DE CARRERA ---
        self.session_uid = None
        self.carrera_terminada = False
        self.momento_fin_carrera = None

        # Último gap válido conocido (para no mostrar un número disparatado ante un
        # glitch transitorio de un frame, típicamente justo al cruzar la meta)
        self._ultimo_gap_adelante_valido = None
        self._ultimo_gap_atras_valido = None

        # Para el log de diagnóstico de _verificar_fin_de_carrera_por_resultado
        self._ultimo_result_status_visto = None

        # --- DIAGNÓSTICO: contador de paquetes recibidos, para saber si la
        # recepción UDP se corta justo al terminar la carrera (problema de red)
        # o si sigue llegando normalmente (en cuyo caso el problema es otro).
        self._contador_paquetes = 0
        self._ultimo_reporte_paquetes = time.time()

        # Mapeo de trackId (paquete de sesión) a nombre de circuito — fuente única en backend/circuitos.py
        self.FASTF1_TRACK_DICT = FASTF1_TRACK_DICT

    def actualizar_telemetria(self):
        try:
            while True:
                packet_data, addr = self.sock.recvfrom(2048)
                self._contador_paquetes += 1
                header_data = packet_data[0:self.header_size]
                unpacked_header = struct.unpack(self.header_format, header_data)
                
                packet_id = unpacked_header[4]
                self.player_car_index = unpacked_header[8]

                # --- DETECCIÓN DE SESIÓN NUEVA (sessionUID cambia entre practica/quali/carrera) ---
                # OJO: ya NO reseteamos acá el aviso de fin de carrera por un simple cambio de
                # session_uid — eso pasa apenas volvés al garage/menú (aunque no hayas arrancado
                # a manejar de nuevo), y con un tiempo de gracia corto el aviso podía apagarse
                # antes de que llegaras a mirar la pantalla (por ejemplo, si jugás en la PS5/TV y
                # recién después mirás el Mac). El reseteo real ahora pasa en
                # _verificar_fin_de_carrera_por_resultado(), cuando volvés a estar ACTIVO en pista.
                nuevo_session_uid = unpacked_header[5]
                self.session_uid = nuevo_session_uid

                # # --- NUEVO RADAR ---
                # if packet_id == 6:
                #     print(f"📡 Recibiendo Paquete ID 6. Bytes totales: {len(packet_data)}")
                # -------------------
                
                if packet_id == 1:
                    session_format = "<BbbBHBb"
                    session_size = struct.calcsize(session_format)
                    if len(packet_data) >= self.header_size + session_size:
                        session_data = packet_data[self.header_size : self.header_size + session_size]
                        unpacked = struct.unpack(session_format, session_data)
                        self.longitud_pista = unpacked[4]
                        self.total_vueltas = unpacked[3]

                        nuevo_track_id = unpacked[6]
                        if nuevo_track_id != self.track_id:
                            self.track_id = nuevo_track_id
                            self.track_name = self.FASTF1_TRACK_DICT.get(nuevo_track_id, f"Track {nuevo_track_id}")

                elif packet_id == 4:
                    self.get_race_participants(packet_data)

                elif packet_id == 8:
                    # Final Classification: el juego lo envía una sola vez, justo al terminar la carrera.
                    print("ℹ️ [diagnóstico] Llegó paquete Final Classification (packet_id 8).")
                    if not self.carrera_terminada:
                        self.carrera_terminada = True
                        self.momento_fin_carrera = time.time()
                        self._lanzar_analisis_curvas()

                elif packet_id in [0, 2, 6, 7, 10] and self.drivers:
                    sizes = {0: 60, 2: 43, 6: 60, 7: 47, 10: 42}
                    size_car = sizes[packet_id]
                    
                    for i in range(22):
                        if i in self.drivers:
                            offset = self.header_size + (i * size_car)
                            if offset + size_car <= len(packet_data):
                                car_block = packet_data[offset : offset + size_car]
                                
                                if packet_id == 0: self.drivers[i].get_driver_motion(car_block)
                                elif packet_id == 2: self.drivers[i].get_driver_lap_data(car_block)
                                elif packet_id == 6: 
                                    self.drivers[i].get_driver_car_telemetry(car_block, self.player_car_index)
                                elif packet_id == 7:
                                    self.drivers[i].get_driver_car_status(car_block)
                                elif packet_id == 10:
                                    self.drivers[i].get_driver_car_damage(car_block)

                    if packet_id == 2:
                        self._verificar_fin_de_carrera_por_resultado()
                

        except BlockingIOError:
            pass  # Esto es completamente normal en sockets no bloqueantes
        except Exception as e:
            print("\n💥 ¡CHOQUE DE DATOS EN EL MOTOR UDP!")
            import traceback
            traceback.print_exc()  # Esto revelará la línea exacta que falla

        # --- DIAGNÓSTICO: reporte de paquetes/segundo cada 5s. Si esto cae a 0
        # justo al cruzar la meta, confirma que es un corte de red (WiFi consola
        # <-> Mac), no un problema del parseo/lógica de nuestro código.
        ahora = time.time()
        if ahora - self._ultimo_reporte_paquetes >= 5.0:
            print(f"ℹ️ [diagnóstico] Paquetes UDP recibidos en los últimos 5s: {self._contador_paquetes}")
            self._contador_paquetes = 0
            self._ultimo_reporte_paquetes = ahora

    def get_race_participants(self, packet_data):
        if len(packet_data) < self.header_size + 1: return
        
        num_active_cars = struct.unpack("<B", packet_data[self.header_size : self.header_size + 1])[0]
        offset_base = self.header_size + 1
        
        size_participant = 56 
        
        for i in range(num_active_cars):
            offset = offset_base + (i * size_participant)
            if offset + size_participant > len(packet_data): break
            
            participant_data = packet_data[offset : offset + size_participant]
            
            driver_id = struct.unpack("<B", participant_data[1:2])[0]
            team_id = struct.unpack("<B", participant_data[3:4])[0]
            
            raw_name = participant_data[7:55]
            nombre_real = raw_name.split(b'\x00')[0].decode('utf-8', errors='ignore')
            
            if i not in self.drivers:
                from backend.driver import Driver
                self.drivers[i] = Driver(driverId=driver_id, teamId=team_id, car_index=i)
            
            if nombre_real:
                self.drivers[i].nombre = nombre_real

    def get_leaderboard(self):
        pilotos_activos = [d for d in self.drivers.values() if getattr(d, 'posicion', 0) > 0]
        return sorted(pilotos_activos, key=lambda x: x.posicion)

    def get_top_pilotos(self, n=5):
        """Devuelve los N pilotos mejor clasificados según la posición actual de carrera."""
        return self.get_leaderboard()[:n]

    def _lanzar_analisis_curvas(self):
        """Al terminar la carrera, genera en segundo plano los gráficos comparativos por curva."""
        try:
            from backend.analisis_curvas import generar_graficos_async
            generar_graficos_async(self)
        except Exception as e:
            print(f"⚠️ No se pudo iniciar el análisis de curvas: {e}")

    def _verificar_fin_de_carrera_por_resultado(self):
        """
        Detecta el fin de carrera vía m_resultStatus del propio piloto (respaldo a
        Final Classification, packet_id 8, que el juego manda UNA sola vez y por lo
        tanto puede perderse por red). m_resultStatus viene en CADA paquete de Lap
        Data, así que es mucho más difícil que se pierda.

        También es la responsable de APAGAR el aviso: no lo hacemos por un simple
        cambio de session_uid ni por un timer corto, porque si jugás mirando otra
        pantalla (p. ej. la PS5/TV) y recién después mirás este dashboard, un aviso
        que se auto-oculta a los pocos segundos puede desaparecer antes de que
        llegues a verlo. En cambio, se apaga recién cuando volvés a estar
        ACTIVO en pista (result_status == 2) de verdad.
        """
        yo = self.drivers.get(self.player_car_index)
        if not yo:
            if self._ultimo_result_status_visto != "sin_auto":
                print(f"ℹ️ [diagnóstico] player_car_index={self.player_car_index} no está (todavía) en self.drivers.")
                self._ultimo_result_status_visto = "sin_auto"
            return

        status = getattr(yo, 'result_status', 0)

        # Log de diagnóstico: solo cuando CAMBIA, para ver la secuencia real sin saturar la consola
        if status != self._ultimo_result_status_visto:
            print(f"ℹ️ [diagnóstico] result_status del piloto cambió: {self._ultimo_result_status_visto} -> {status}")
            self._ultimo_result_status_visto = status

        if not self.carrera_terminada:
            # 3=terminó 4=DNF 5=descalificado 6=no clasificado 7=retirado -> tu carrera ya acabó
            if status >= 3:
                print("🏁 Fin de carrera detectado por resultado del piloto (respaldo a Final Classification).")
                self.carrera_terminada = True
                self.momento_fin_carrera = time.time()
                self._lanzar_analisis_curvas()
        else:
            # Volviste a estar activo en pista de verdad -> recién ahí apagamos el aviso
            if status == 2:
                self.carrera_terminada = False
                self.momento_fin_carrera = None

    def get_race_best_sectors(self):
        """
        Recorre el historial de vueltas de TODOS los pilotos (no solo el jugador)
        y devuelve el mejor tiempo registrado en la carrera para cada sector y vuelta completa.
        """
        mejor_s1, mejor_s2, mejor_s3, mejor_vuelta = 0, 0, 0, 0

        for piloto in self.drivers.values():
            for vuelta in getattr(piloto, 'historial_vueltas', []):
                s1 = vuelta.get("sector_1_ms", 0)
                s2 = vuelta.get("sector_2_ms", 0)
                s3 = vuelta.get("sector_3_ms", 0)
                total = vuelta.get("tiempo_total_ms", 0)

                if s1 > 0 and (mejor_s1 == 0 or s1 < mejor_s1):
                    mejor_s1 = s1
                if s2 > 0 and (mejor_s2 == 0 or s2 < mejor_s2):
                    mejor_s2 = s2
                if s3 > 0 and (mejor_s3 == 0 or s3 < mejor_s3):
                    mejor_s3 = s3
                if total > 0 and (mejor_vuelta == 0 or total < mejor_vuelta):
                    mejor_vuelta = total

        return {
            "sector_1_ms": mejor_s1,
            "sector_2_ms": mejor_s2,
            "sector_3_ms": mejor_s3,
            "vuelta_ms": mejor_vuelta
        }

    def get_player_gaps(self):
        if self.player_car_index not in self.drivers: return None
        yo = self.drivers[self.player_car_index]
        if getattr(yo, 'posicion', 0) == 0: return None

        pilotos = self.get_leaderboard()
        gaps = {
            "mi_posicion": yo.posicion,
            "piloto_adelante": "-", "gap_adelante_m": 0.0,
            "piloto_atras": "-", "gap_atras_m": 0.0
        }

        # Distancia ACUMULADA en toda la carrera (no solo dentro de la vuelta actual):
        # la distancia de vuelta ('distancia') se reinicia a ~0 cada vez que cruzás la
        # meta, así que restarla directamente entre dos autos provoca un salto brusco
        # justo en ese instante. Sumándole las vueltas ya completadas se vuelve
        # monótona a lo largo de toda la carrera y el gap queda estable.
        def distancia_acumulada(piloto):
            vuelta = max(getattr(piloto, 'vuelta_actual', 1), 1)
            return (vuelta - 1) * self.longitud_pista + getattr(piloto, 'distancia', 0.0)

        # Salvaguarda extra: por más que la fórmula de arriba sea correcta, un paquete
        # UDP perdido justo en el instante del cruce puede dejar a un auto "atrasado"
        # un frame (su vuelta_actual todavía no incrementó). Un gap real entre autos
        # consecutivos en la clasificación nunca debería superar ~medio circuito; si
        # da eso, es ese glitch transitorio, no un gap real: lo ignoramos ese frame y
        # mantenemos el último valor válido en vez de mostrar un número disparatado.
        limite_gap_valido_m = self.longitud_pista * 0.5

        mi_distancia = distancia_acumulada(yo)

        if yo.posicion > 1 and (yo.posicion - 2) < len(pilotos):
            p_adelante = pilotos[yo.posicion - 2]
            gap = abs(distancia_acumulada(p_adelante) - mi_distancia)
            if gap <= limite_gap_valido_m:
                gaps["piloto_adelante"] = p_adelante.nombre
                gaps["gap_adelante_m"] = gap
            elif self._ultimo_gap_adelante_valido is not None:
                gaps["piloto_adelante"], gaps["gap_adelante_m"] = self._ultimo_gap_adelante_valido
            if gap <= limite_gap_valido_m:
                self._ultimo_gap_adelante_valido = (p_adelante.nombre, gap)

        if yo.posicion < len(pilotos):
            p_atras = pilotos[yo.posicion]
            gap = abs(mi_distancia - distancia_acumulada(p_atras))
            if gap <= limite_gap_valido_m:
                gaps["piloto_atras"] = p_atras.nombre
                gaps["gap_atras_m"] = gap
                self._ultimo_gap_atras_valido = (p_atras.nombre, gap)
            elif self._ultimo_gap_atras_valido is not None:
                gaps["piloto_atras"], gaps["gap_atras_m"] = self._ultimo_gap_atras_valido

        return gaps