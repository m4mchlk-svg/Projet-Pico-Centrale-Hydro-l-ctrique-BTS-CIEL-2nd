from machine import Pin, SoftI2C, Timer
import time

# Utilisation de SoftI2C pour plus de flexibilité sur les broches de l'ESP32
# Branchements : Pin 2 SDA (Fil Vert) sur GPIO 21, Pin 3 SCL (Fil Blanc) sur GPIO 22
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=100000)

TF_LUNA_ADDR = 0x10 # Adresse par défaut

# Variables de calcul
dist1, dist2, dist3, moyenne, error, count = 0, 0, 0, 0, 0, 0
max_error, max_marge, timer_period_ms = 2, 10, 1000

def check_sensor():
    """Vérifie si le capteur répond sur le bus I2C"""
    devices = i2c.scan()
    if TF_LUNA_ADDR in devices:
        print("TF-Luna détecté sur l'adresse 0x10. Démarrage...\n")
        return True
    else:
        print("ERREUR : Capteur TF-Luna introuvable !")
        print("Checklist : Broche 5 au GND ? Alimenté en 5V ? SDA/SCL croisés ?")
        return False

def get_distance():
    try:
        # Lecture de 4 octets (Distance L/H + Amplitude L/H)
        data = i2c.readfrom_mem(TF_LUNA_ADDR, 0x00, 4)
        
        # Reconstruction (Little Endian)
        distance = data[0] + (data[1] << 8)
        amp = data[2] + (data[3] << 8)
        
        # Le signal est trop faible ou saturé
        if amp < 100 or amp == 65535:
            return None
            
        return distance
        
    except Exception:
        # On ne print l'erreur qu'une fois pour ne pas spammer la console
        return -1

def get_data(timer):
    global max_marge, max_error, dist1, dist2, dist3, moyenne, error, count
    mesure = get_distance()
    
    if mesure == -1:
        print("Erreur I2C : Vérifiez les fils (SDA/SCL) et la broche 5.")
        return

    if mesure is not None:
        # Plage fiable : 20 cm à 800 cm
        if 20 <= mesure <= 800:
            if abs(mesure - dist1) <= max_marge or error >= max_error:
                dist3 = dist2
                dist2 = dist1
                dist1 = mesure
                moyenne = int((dist1 + dist2 + dist3) / 3)
                error = 0
            else:
                error += 1
            
            count += 1
            print(f"Mesure n°{count}: {dist1} cm")
            print(f"Moyenne (3 val): {moyenne} cm | Force Signal: OK\n")
        else:
            print(f"Hors limite : {mesure} cm (Trop proche ou trop loin)")
    else:
        print("Signal trop faible (Amplitude < 100).")

# --- INITIALISATION ---
if check_sensor():
    timer_sensor = Timer(1)
    timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=get_data)
else:
    # Si le capteur n'est pas détecté, on arrête le script ici
    import sys
    sys.exit()

while True:
    # Le travail se fait dans le callback du Timer
    time.sleep(1)