import socket
import struct
import time
from tabulate import tabulate
import traceback

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

        # --- ESTADO DE LA SESIÓN / FIN DE CARRERA ---
        self.session_uid = None
        self.carrera_terminada = False
        self.momento_fin_carrera = None
        self.GRACIA_MENSAJE_FIN_S = 5  # segundos mínimos que el aviso se mantiene visible

        # Mapeo de trackId (paquete de sesión) a nombre de circuito
        self.FASTF1_TRACK_DICT = {
            0: "Australia", 1: "France", 2: "China", 3: "Bahrain",
            4: "Spain", 5: "Monaco", 6: "Canada", 7: "Great Britain", 8: "Germany",
            9: "Hungary", 10: "Belgium", 11: "Italy", 12: "Singapore",
            13: "Japan", 14: "Abu Dhabi", 15: "United States", 16: "Brazil", 17: "Austria",
            18: "Russia", 19: "Mexico", 20: "Azerbaijan", 26: "Netherlands",
            27: "Emilia Romagna", 28: "Portugal", 29: "Saudi Arabia", 30: "Miami"
        }

    def actualizar_telemetria(self):
        terminada_en_este_ciclo = False
        try:
            while True:
                packet_data, addr = self.sock.recvfrom(2048)
                header_data = packet_data[0:self.header_size]
                unpacked_header = struct.unpack(self.header_format, header_data)
                
                packet_id = unpacked_header[4]
                self.player_car_index = unpacked_header[8]

                # --- DETECCIÓN DE SESIÓN NUEVA (sessionUID cambia entre practica/quali/carrera) ---
                # No reseteamos el aviso de fin de carrera si: (a) se acaba de activar en ESTE
                # mismo ciclo de lectura (el juego puede mandar paquetes de la sesión siguiente
                # mezclados con el de Final Classification), o (b) todavía no pasó el tiempo
                # mínimo de gracia — así el mensaje siempre alcanza a mostrarse en pantalla.
                nuevo_session_uid = unpacked_header[5]
                if self.session_uid is not None and nuevo_session_uid != self.session_uid:
                    tiempo_desde_fin = (
                        time.time() - self.momento_fin_carrera
                        if self.momento_fin_carrera is not None else None
                    )
                    puede_resetear = (
                        not terminada_en_este_ciclo
                        and (tiempo_desde_fin is None or tiempo_desde_fin > self.GRACIA_MENSAJE_FIN_S)
                    )
                    if puede_resetear:
                        self.carrera_terminada = False
                        self.momento_fin_carrera = None
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

                        nuevo_track_id = unpacked[6]
                        if nuevo_track_id != self.track_id:
                            self.track_id = nuevo_track_id
                            self.track_name = self.FASTF1_TRACK_DICT.get(nuevo_track_id, f"Track {nuevo_track_id}")

                elif packet_id == 4:
                    self.get_race_participants(packet_data)

                elif packet_id == 8:
                    # Final Classification: el juego lo envía una sola vez, justo al terminar la carrera.
                    if not self.carrera_terminada:
                        self.carrera_terminada = True
                        self.momento_fin_carrera = time.time()
                        terminada_en_este_ciclo = True
                        self._lanzar_analisis_curvas()

                elif packet_id in [0, 2, 6, 10] and self.drivers:
                    sizes = {0: 60, 2: 43, 6: 60, 10: 42}
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
                                elif packet_id == 10:
                                    self.drivers[i].get_driver_car_damage(car_block)
                

        except BlockingIOError:
            pass  # Esto es completamente normal en sockets no bloqueantes
        except Exception as e:
            print("\n💥 ¡CHOQUE DE DATOS EN EL MOTOR UDP!")
            import traceback
            traceback.print_exc()  # Esto revelará la línea exacta que falla

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

        if yo.posicion > 1 and (yo.posicion - 2) < len(pilotos):
            p_adelante = pilotos[yo.posicion - 2]
            gaps["piloto_adelante"] = p_adelante.nombre
            gaps["gap_adelante_m"] = abs(p_adelante.distancia - yo.distancia)

        if yo.posicion < len(pilotos):
            p_atras = pilotos[yo.posicion]
            gaps["piloto_atras"] = p_atras.nombre
            gaps["gap_atras_m"] = abs(yo.distancia - p_atras.distancia)

        return gaps