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
            
            # --- LA SOLUCIÓN AL SECTOR 3 ---
            # Guardamos el último registro válido de S1 y S2 antes de que el juego los ponga en 0 al cruzar la meta
            if not hasattr(self, 'ultimo_s1_ms'): self.ultimo_s1_ms = 0
            if not hasattr(self, 'ultimo_s2_ms'): self.ultimo_s2_ms = 0
            
            if s1_ms > 0: self.ultimo_s1_ms = s1_ms
            if s2_ms > 0: self.ultimo_s2_ms = s2_ms

            # 2. DETECTAR CAMBIO DE VUELTA Y GUARDAR EL DICCIONARIO
            if vuelta > self.vuelta_actual:
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
                self.vuelta_actual = vuelta

            # 3. ACTUALIZAR TIEMPOS EN VIVO
            self.tiempo_vuelta_actual_ms = current_lap_ms
            self.tiempo_s1_ms = s1_ms
            self.tiempo_s2_ms = s2_ms
            self.sector_actual = sector