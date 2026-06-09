from machine import I2C, Pin, Timer
import time

# Initialisation du bus I2C (Fréquence 400 kHz = Fast Mode I2C)
i2c = I2C(0, sda=Pin(22), scl=Pin(23), freq=400000)


def get_firmware_version(addr):
    """Récupère la version du firmware du capteur TFMini (ou compatible) via I2C."""
    try:
        # Commande version du firmware
        i2c.writeto(addr, b'\x5a\x04\x01\x5f')
        time.sleep_ms(100)
        
        # Lecture 7 octets de réponse
        res = i2c.readfrom(addr, 7)
        
        # Vérification trame reçue (7 octets, octet 0 entête 0x5A, octet 2 confirmation ID commande 0x01)
        if len(res) >= 7 and res[0] == 0x5a and res[2] == 0x01:
            # Formatage version
            return "V{}.{}.{}".format(res[3], res[4], res[5])
    except:
        pass
    
    return "Inconnue"


print("Recherche de capteurs I2C...")
# Scan bus I2C adresses matérielles connectées
devices = i2c.scan()
sensor_info = {} 								# Dictionnaire stock adresse et version capteur(s)

if devices:
    for d in devices:
        version = get_firmware_version(d)
        sensor_info[d] = version
        print("Trouvé : Adresse {} | Version : {}".format(hex(d), version))
else:
    print("Aucun capteur détecté.")

# --- CONFIGURATION INDIVIDUELLE DES DEUX CAPTEURS ---
# Le capteur 1 est resté à l'adresse d'usine (0x10)
# Le capteur 2 a bien enregistré son adresse modifiée (0x11)
sensors = {
    0x10: {"name": "Capteur_Droit",  "dist1": 0, "dist2": 0, "error": 0, "count": 0},
    0x11: {"name": "Capteur_Gauche", "dist1": 0, "dist2": 0, "error": 0, "count": 0}
}

max_error = 2  								# Nombre d'erreurs tolérées
max_marge = 10  								# Variation maximale autorisée (en cm) entre deux mesures
timer_period_ms, error_period_ms = 3000, 1000	# Fréquence de mesure normale / erreur détectée

def get_distance(addr):
    try:
        # Commande demande de mesure de distance envoyée à l'adresse spécifique
        i2c.writeto(addr, b'\x5a\x05\x00\x01\x60')
        
        # Lecture 9 octets de données de mesure
        data = i2c.readfrom(addr, 9)
        
        # Vérification protocole standard TFMini
        if len(data) >= 9 and data[0] == 0x59 and data[1] == 0x59:
            # Distance codée sur 2 octets
            # Octet 2 (poids faible) + octet 3 (poids fort) décalé de 8 bits vers la gauche
            distance = data[2] + (data[3] << 8)
            return distance
    except:
        return None
    
    return None


def get_data(timer):
    global timer_sensor
    any_error_active = False
    
    # On parcourt chaque capteur l'un après l'autre par son adresse
    for addr, state in sensors.items():
        mesure = get_distance(addr)
            
        if mesure is not None:
            # CORRECTION BUG INITIALISATION : Si c'est le premier démarrage, on valide directement
            if state["dist1"] == 0:
                state["dist1"] = mesure
                state["dist2"] = mesure
                state["error"] = 0
                state["count"] += 1
                print("[{} | Adresse: {}] Initialisation réussie : {} cm\n".format(state["name"], hex(addr), mesure))
                continue # On passe directement au capteur suivant pour ce tour
                
            # Vérification mesure physiquement possible
            if 10 < mesure < 1200:
                
                # Accepte la valeur si écart avec mesure précédente correct et erreurs maximales non atteintes
                if abs(mesure - state["dist1"]) <= max_marge and state["error"] <= max_error:
                    
                    # Décalage des valeurs
                    state["dist2"] = state["dist1"]
                    state["dist1"] = mesure
                    
                    # Réinitialise le compteur d'erreurs car valeur valide
                    state["error"] = 0
                    
                    # Incrémente le compteur global du capteur
                    state["count"] += 1
                    
                    # Formatage pour l'affichage
                    addr_h = hex(addr)
                    ver = sensor_info.get(addr, "N/A")
                    
                    # Affiche les résultats en spécifiant quel capteur parle
                    print("[{} | Adresse: {} | Version: {}]\nDistance n°{}: {} cm\n\n".format(state["name"], addr_h, ver, state["count"], state["dist2"]))
                    
                else:
                    # Variance trop élevée = ignorée + erreur
                    state["error"] += 1
                    any_error_active = True
                    print(f"{state['name']} (Adresse {hex(addr)}): {state['error']} erreur(s) (Variance)\n")
                    
                    if state["error"] > max_error:
                        # Erreurs maximales atteintes = réinitialisation des variables
                        print(f"{state['name']} (Adresse {hex(addr)}): Erreurs multiples, recalibrage...\n\n")
                        state["error"] = 0
                        state["dist1"] = mesure
                        state["dist2"] = mesure
                    
            else:
                # Donnée lue mais en dehors des limites du capteur
                state["count"] += 1
                print("[{} | Adresse: {}]\nHors limite ({} cm)\n\n".format(state["name"], hex(addr), mesure))
        else:
            # Pas de réponse de cette adresse spécifique
            state["error"] += 1
            any_error_active = True
            print(f"{state['name']} (Adresse {hex(addr)}): Impossible de communiquer\n")


    if any_error_active:
        timer_sensor.init(mode=Timer.PERIODIC, period=error_period_ms, callback=get_data)
    else:
        timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=get_data)


timer_sensor = Timer(0)
timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=get_data)

while True:
    pass
