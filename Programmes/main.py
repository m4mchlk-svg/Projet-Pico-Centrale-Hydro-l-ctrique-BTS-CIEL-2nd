from machine import Timer
from tfmini import TFMiniPlus # Importe classe depuis librairie

# Initialisation de capteur
print("Recherche et initialisation du capteur...")
capteur = TFMiniPlus(i2c_id=0, sda_pin=22, scl_pin=23)

print("Capteur trouvé à l'adresse :", hex(capteur.address))
print("Version du firmware :", capteur.version)

count = 0

# Fonction appelée par Timer
def update_sensor(timer):
    global count
    
    # Demande la distance à la librairie
    distance = capteur.get_distance()
    
    if distance == -1:
        print("[Hors limite]")
    elif distance is not None:
        count += 1
        octets = capteur.get_distance_bytes()
        print(f"Distance n°{count} | Distance : {distance} cm | Octets : {octets}")
    else:
        print("Erreur de lecture ou variance trop élevée (en attente de recalibrage...)")

# Lancement du Timer
timer_period_ms = 3000
timer_sensor = Timer(0)
timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=update_sensor)

# Boucle principale (le microcontrôleur peut faire autre chose ici)
while True:
    pass
