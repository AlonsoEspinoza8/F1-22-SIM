import struct

class Driver:
    def __init__(self, driverId, teamId, car_index):
        self.driverId = driverId
        self.teamId = teamId
        self.car_index = car_index
        
        # El nombre temporal. La clase Race lo sobrescribirá casi instantáneamente.
        self.nombre = f"Piloto {self.driverId}"
        
        # Atributos en Tiempo Real
        self.x = 0.0
        self.z = 0.0
        self.distancia = 0.0
        self.tiempo_vuelta = 0.0
        self.velocidad = 0
        self.acelerador = 0.0
        self.freno = 0.0
        self.marcha = 0
        self.posicion = 0

        # --- NUEVO: Variables de Cronometraje ---
        self.vuelta_actual = 1
        self.sector_actual = 0
        self.tiempo_s1_ms = 0
        self.tiempo_s2_ms = 0
        self.tiempo_vuelta_actual_ms = 0
        
        # --- EL HISTORIAL (La lista de diccionarios que querías) ---
        self.historial_vueltas = []
        
        self.lap_data_points = []

        # --- NEUMÁTICOS: desgaste por rueda (%), orden del juego: RL, RR, FL, FR ---
        self.desgaste_neumaticos = {
            "FL": 0.0, "FR": 0.0, "RL": 0.0, "RR": 0.0
        }

        # --- TELEMETRÍA POR DISTANCIA (para comparar curva a curva entre vueltas) ---
        self.buffer_vuelta_actual = []     # muestras {distancia, velocidad, acelerador, freno} de la vuelta EN CURSO
        self.mejor_vuelta_telemetria = []  # snapshot completo de la MEJOR vuelta ya completada
        self.mejor_vuelta_tiempo_ms = None

    def get_driver_motion(self, car_data):
        if len(car_data) >= 12:
            x, y, z = struct.unpack("<fff", car_data[0:12])
            self.x, self.z = x, z

    def get_driver_car_telemetry(self, car_data, player_index=-1):
        try:
            if len(car_data) >= 60:
                unpacked = struct.unpack("<HfffBbH", car_data[0:18])
                self.velocidad = unpacked[0]
                self.acelerador = unpacked[1]
                self.freno = unpacked[3]
                self.marcha = unpacked[5]

                # Guardamos la muestra (distancia ya viene de la Lap Data más reciente)
                # para poder graficar velocidad/acelerador/freno vs distancia recorrida.
                self.buffer_vuelta_actual.append({
                    "distancia": self.distancia,
                    "velocidad": self.velocidad,
                    "acelerador": self.acelerador,
                    "freno": self.freno
                })
                
                # # --- RADAR NUCLEAR (Solo se activa para tu auto) ---
                # if self.car_index == player_index:
                #     print(f"\n🏎️ [TU AUTO - P{self.car_index}] Vel: {self.velocidad} | Acel: {self.acelerador}")
                #     print(f"📦 BYTES CRUDOS: {car_data[0:18]}")
                # # ---------------------------------------------------
                
        except Exception as e:
            print(f"⚠️ Error en telemetría (Piloto {self.car_index}): {e}")

    def get_driver_lap_data(self, car_data):
        if len(car_data) >= 43:
            unpacked_tiempos = struct.unpack("<IIHH", car_data[0:12])
            last_lap_ms = unpacked_tiempos[0]
            current_lap_ms = unpacked_tiempos[1]
            s1_ms = unpacked_tiempos[2]
            s2_ms = unpacked_tiempos[3]
            
            vuelta = struct.unpack("<B", car_data[25:26])[0]
            sector = struct.unpack("<B", car_data[28:29])[0]

            # --- POSICIÓN Y DISTANCIA (esenciales para leaderboard, gaps y minimapa) ---
            self.posicion = struct.unpack("<B", car_data[24:25])[0]
            self.distancia = struct.unpack("<f", car_data[12:16])[0]
            
            # --- LA SOLUCIÓN AL SECTOR 3 ---
            # Guardamos el último registro válido de S1 y S2 antes de que el juego los ponga en 0 al cruzar la meta
            if not hasattr(self, 'ultimo_s1_ms'): self.ultimo_s1_ms = 0
            if not hasattr(self, 'ultimo_s2_ms'): self.ultimo_s2_ms = 0
            if not hasattr(self, 'ultimo_last_lap_ms'): self.ultimo_last_lap_ms = 0
            
            if s1_ms > 0: self.ultimo_s1_ms = s1_ms
            if s2_ms > 0: self.ultimo_s2_ms = s2_ms

            # 2. DETECTAR VUELTA COMPLETADA Y GUARDAR EL DICCIONARIO
            # Usamos el CAMBIO en last_lap_ms (se actualiza al cruzar la meta) en vez de
            # esperar a que 'vuelta' se incremente: en la ÚLTIMA vuelta de la carrera nunca
            # hay una "vuelta siguiente" que dispare ese incremento, así que ese registro
            # se perdía y su tiempo nunca podía aparecer como mejor tiempo.
            if last_lap_ms > 0 and last_lap_ms != self.ultimo_last_lap_ms:
                # Calculamos el S3 usando nuestra memoria caché en lugar de los valores en 0
                tiempo_s3_ms = last_lap_ms - (self.ultimo_s1_ms + self.ultimo_s2_ms)
                
                registro_vuelta = {
                    "vuelta": self.vuelta_actual,
                    "tiempo_total_ms": last_lap_ms,
                    "sector_1_ms": self.ultimo_s1_ms,
                    "sector_2_ms": self.ultimo_s2_ms,
                    "sector_3_ms": tiempo_s3_ms if tiempo_s3_ms > 0 else 0
                }
                
                self.historial_vueltas.append(registro_vuelta)
                self.ultimo_last_lap_ms = last_lap_ms

                # --- ¿Fue esta la MEJOR vuelta hasta ahora? Guardamos su telemetría completa ---
                if self.mejor_vuelta_tiempo_ms is None or last_lap_ms < self.mejor_vuelta_tiempo_ms:
                    self.mejor_vuelta_tiempo_ms = last_lap_ms
                    self.mejor_vuelta_telemetria = list(self.buffer_vuelta_actual)

                # Empezamos a acumular la telemetría de la vuelta que recién comienza
                self.buffer_vuelta_actual = []

            if vuelta > self.vuelta_actual:
                self.vuelta_actual = vuelta

            # 3. ACTUALIZAR TIEMPOS EN VIVO
            self.tiempo_vuelta_actual_ms = current_lap_ms
            self.tiempo_s1_ms = s1_ms
            self.tiempo_s2_ms = s2_ms
            self.sector_actual = sector

    def get_driver_car_damage(self, car_data):
        """
        Parsea el paquete Car Damage (packet_id 10). Los primeros 16 bytes son
        m_tyresWear[4] (floats, % de desgaste), en el orden del juego: RL, RR, FL, FR.
        """
        if len(car_data) >= 16:
            rl, rr, fl, fr = struct.unpack("<ffff", car_data[0:16])
            self.desgaste_neumaticos = {
                "FL": fl, "FR": fr, "RL": rl, "RR": rr
            }