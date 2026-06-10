from machine import UART, Pin, Timer
import time

# Initialisation du bus UART pour le TFmini Plus
# Port 1, Vitesse par défaut : 115200 bauds
uart = UART(1, baudrate=115200, tx=17, rx=16, bits=8, parity=None, stop=1)

dist1, dist2, dist3, hauteur = 0, 0, 0, 0 		# Stockage des 3 dernières valeurs et de la moyenne
error, count = 0, 0 							# Valeurs des erreurs et du compteur
max_error, max_marge = 2, 10   					# Nombre d'erreurs tolérées et variation maximale autorisée (en cm) entre deux mesures
timer_period_ms, error_period_ms = 1000, 250	# Fréquence de mesure normale / erreur détectée
att_moy = 100									# Attente en ms entre chaque distance mesurée
mesure_hauteur = 0
prep = 2

def get_firmware_version(port):
    """
        Cette fonction permet de récupérer la version du capteur détecté.
    """
    try:
        if uart.any():
            uart.read()
            
        uart.write(b'\x5a\x04\x01\x5f')
        time.sleep_ms(100)
        
        res = uart.read(7)
        if res and len(res) >= 7 and res[0] == 0x5a and res[2] == 0x01:
            return "V{}.{}.{}".format(res[3], res[4], res[5])
    except:
        pass
    
    return "Inconnue"


print("Recherche du capteur UART...")
sensor_info = {} 								

TFMINI_ADDR = 0x11 # Identifiant fictif simulant l'adresse UART

version = get_firmware_version(uart)
sensor_info[TFMINI_ADDR] = version
print("Trouvé : Capteur UART | Version : {}".format(version))


def get_distance():
    """
        Cette fonction récupère la distance mesurée par le capteur en se synchronisant
        strictement sur l'en-tête de trame standard 0x59 0x59.
    """
    try:
        # Recherche active de l'en-tête double 0x59 0x59
        header_found = False
        timeout = 50  # Sécurité pour éviter de bloquer la fonction (50 tentatives max)
        
        while timeout > 0:
            timeout -= 1
            if uart.any() >= 2:
                # On cherche le premier octet d'en-tête 0x59
                b1 = uart.read(1)
                if b1 and b1[0] == 0x59:
                    # On vérifie immédiatement si le suivant est aussi un 0x59
                    b2 = uart.read(1)
                    if b2 and b2[0] == 0x59:
                        header_found = True
                        break
            else:
                time.sleep_ms(1)
                
        if not header_found:
            return None

        # Une fois l'en-tête trouvé, on attend les 7 octets restants de la trame
        # (Distance L/H, Strength L/H, Temp L/H, Checksum)
        retry = 10
        while uart.any() < 7 and retry > 0:
            time.sleep_ms(1)
            retry -= 1
            
        if uart.any() < 7:
            return None
            
        tail = uart.read(7)
        if not tail or len(tail) < 7:
            return None
            
        # Reconstruction complète des données à des fins de vérification de la Checksum (optionnel mais recommandé)
        # byte0 et byte1 sont implicitement 0x59
        checksum = (0x59 + 0x59 + sum(tail[:6])) & 0xFF
        if checksum != tail[6]:
            # Erreur de corruption de données transmises, on ignore la mesure
            return None

        # Extraction de la distance (tail[0] = Dist_L, tail[1] = Dist_H)
        distance = tail[0] + (tail[1] << 8)
        
        # Application de votre correctif d'origine
        distance = round(distance * 1.05)
        return distance
        
    except Exception as e:
        print("\nErreur dans la récupération de la mesure:", e)
        return None


def use_data():
    """
        Cette fonction affiche et gère les mesures.
    """
    global dist1, dist2, dist3, hauteur, error, count, att_moy, prep
    mesure = get_distance()
        
    if mesure is not None:
        if dist1 == 0:
            hauteur = mesure
            dist1 = mesure
            dist2 = mesure
            dist3 = mesure
        # Vérification mesure physiquement possible
        if 10 < mesure < 1200:
            
            # Accepte la valeur si écart avec mesure précédente correct et erreurs maximales non atteintes
            if abs(mesure - hauteur) <= max_marge:
                
                # Prise de mesure décalée pour calculer une moyenne
                dist3 = mesure
                
                time.sleep_ms(att_moy)
                mesure = get_distance()
                if mesure is None: mesure = dist3
                dist2 = mesure
                
                time.sleep_ms(att_moy)
                mesure = get_distance()
                if mesure is None: mesure = dist2
                dist1 = mesure
                
                hauteur = round((dist1 + dist2 + dist3)/3)
                
                # Conversion en 2 octets
                lsb = hauteur & 0xFF
                msb = (hauteur >> 8) & 0xFF
                octets_distance = bytes([lsb, msb])
                
                # Réinitialise le compteur d'erreurs car valeur valide
                error = 0
                
                # Incrémente le compteur global
                count += 1
                
                # Formatage pour l'affichage
                addr_h = hex(TFMINI_ADDR)
                ver = sensor_info.get(TFMINI_ADDR, "N/A")
                
                # Affiche les résultats
                if count > prep:
                    print("[Adresse: {} | Version: {}]\nDistance n°{}: {} cm\nFormat bytes: {}\n\n".format(addr_h, ver, count, hauteur, octets_distance))
                
                if error == 0:
                    timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)
                        
                return hauteur
            
            else:
                timer_sensor.init(mode=Timer.PERIODIC, period=error_period_ms, callback=interrupt_hauteur)
                error += 1
                if count > prep:
                    print(f"{error} erreur(s)\n")
            
                if error > max_error:
                    if count > prep:
                        print("Erreurs multiples, recalibrage...\n\n")
                    error = 0
                    hauteur = mesure
                    dist1 = mesure
                    dist2 = mesure
                    dist3 = mesure
                    timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)
                    
                return hauteur
            
        else:
            count += 1
            print("[Adresse: {}]\nHors limite ({} cm)\n\n".format(hex(TFMINI_ADDR), mesure))
            return hauteur
            
def interrupt_hauteur(timer):
    global mesure_hauteur
    mesure_hauteur = 1
    return mesure_hauteur
            
timer_sensor = Timer(0)
timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)

while True:
    if mesure_hauteur == 1:
        hauteur = use_data()
        mesure_hauteur = 0