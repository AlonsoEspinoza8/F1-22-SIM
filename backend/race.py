import socket
import struct
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
        self.longitud_pista = 5000.0

    def actualizar_telemetria(self):
        try:
            while True:
                packet_data, addr = self.sock.recvfrom(2048)
                header_data = packet_data[0:self.header_size]
                unpacked_header = struct.unpack(self.header_format, header_data)
                
                packet_id = unpacked_header[4]
                self.player_car_index = unpacked_header[8]

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

                elif packet_id == 4:
                    self.get_race_participants(packet_data)

                elif packet_id in [0, 2, 6] and self.drivers:
                    sizes = {0: 60, 2: 43, 6: 60}
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

    def imprimir_resumen_carrera(self):
        """
        Genera y muestra una tabla ordenada en la terminal con la clasificación actual,
        incluyendo la telemetría en vivo.
        """
        pilotos = self.get_leaderboard()
        
        if not pilotos:
            return 
            
        datos_tabla = []
        
        for p in pilotos:
            # ¡LA CLAVE!: Extraemos la velocidad usando la palabra en español exacta
            velocidad_actual = getattr(p, 'velocidad', 0)
            
            fila = [
                p.posicion,
                getattr(p, 'nombre', f"Piloto {p.driverId}"),
                p.teamId,
                p.car_index,
                f"{velocidad_actual} km/h"  # Añadimos la velocidad a la fila de tabulate
            ]
            datos_tabla.append(fila)
            
        # Actualizamos los encabezados para incluir la nueva columna
        encabezados = ["POS", "PILOTO", "TEAM ID", "CAR INDEX", "VELOCIDAD"]
        
        print("\n=== CLASIFICACIÓN EN VIVO ===")
        print(tabulate(datos_tabla, headers=encabezados, tablefmt="fancy_grid", numalign="center", stralign="center"))
        
        # Dashboard del jugador
        gaps = self.get_player_gaps()
        if gaps:
            yo = self.drivers[self.player_car_index]
            
            # Nuevamente, usamos el español para tus pedales
            velocidad = getattr(yo, 'velocidad', 0)
            aceleracion = getattr(yo, 'acelerador', 0.0)
            freno = getattr(yo, 'freno', 0.0)
            
            acel_pct = int(aceleracion * 100) if aceleracion <= 1.0 else int(aceleracion)
            freno_pct = int(freno * 100) if freno <= 1.0 else int(freno)

            print("\n--- INFORME DE INGENIERO ---")
            print(f"Tu Posición : P{gaps['mi_posicion']}")
            print(f"P. Delante  : {gaps['piloto_adelante']} a {gaps['gap_adelante_m']:.1f} m")
            print(f"P. Detrás   : {gaps['piloto_atras']} a {gaps['gap_atras_m']:.1f} m")
            print(f"Telemetría  : {velocidad} km/h | Acel: {acel_pct}% | Freno: {freno_pct}%")
        print("=============================\n")