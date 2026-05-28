from machine import Timer
from tfmini import TFMiniPlus # Importe la classe depuis notre nouvelle librairie

# 1. Initialisation de l'objet capteur
# Tu peux changer les pins ici facilement sans toucher à la librairie
print("Recherche et initialisation du capteur...")
capteur = TFMiniPlus(i2c_id=0, sda_pin=22, scl_pin=23)

print("Capteur trouvé à l'adresse :", hex(capteur.address))
print("Version du firmware :", capteur.version)

count = 0

# 2. Fonction appelée par le Timer (Callback)
def update_sensor(timer):
    global count
    
    # On demande la distance traitée à la librairie
    distance = capteur.get_distance()
    
    if distance == -1:
        print("[Hors limite]")
    elif distance is not None:
        count += 1
        octets = capteur.get_distance_bytes()
        print(f"Mesure n°{count} | Distance : {distance} cm | Octets : {octets}")
    else:
        # Correspond au cas où l'erreur est tolérée avant le recalibrage, ou si lecture échoue
        print("Erreur de lecture ou variance trop élevée (en attente de recalibrage...)")

# 3. Lancement du Timer
timer_period_ms = 3000
timer_sensor = Timer(0)
timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=update_sensor)

# Boucle principale (le microcontrôleur peut faire autre chose ici)
try:
    while True:
        pass
except KeyboardInterrupt:
    timer_sensor.deinit()
    print("Programme arrêté.")
