from machine import I2C, Pin, Timer
import time

# Initialisation du bus I2C
# Pins configurable
# Fréquence 400 kHz = Fast Mode I2C
i2c = I2C(0, sda=Pin(23), scl=Pin(25), freq=400000)

dist1, dist2, dist3, hauteur = 0, 0, 0, 0 		# Stockage des 3 dernières valeurs et de la moyenne
error, count = 0, 0 							# Valeurs des erreurs et du compteur
max_error, max_marge = 2, 10   					# Nombre d'erreurs tolérées et variation maximale autorisée (en cm) entre deux mesures
timer_period_ms, error_period_ms = 1000, 250	# Fréquence de mesure normale / erreur détectée
att_moy = 100									# Attente en ms entre chaque distance mesurée
mesure_hauteur = 0
prep = 2

def get_firmware_version(addr):
    """
        Cette fonction permet de récupérer la version du capteur détecté.
        On envoie d'abord la commande à l'adresse du capteur pour récupérer sa version puis on lit sa réponse.
        On formate ensuite les octets qui nous intéresse dans une variable.
        
        Args:
            addr (string): Adresse du capteur
            
        Returns:
            string: Version du capteur trouvée
    """
    try:
        # Commande version du firmware
        i2c.writeto(addr, b'\x5a\x04\x01\x5f')
        time.sleep_ms(20) # Temps d'attente ajusté pour éviter le gel du bus
        
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
    
    # Première adresse trouvée = capteur principal
    TFMINI_ADDR = devices[0]
else:
    # Echec scan = adresse par défaut (0x10 pour le TFMini Plus en mode I2C)
    print("\nAucun capteur détecté. Utilisation adresse par défaut 0x10")
    TFMINI_ADDR = 0x10
    sensor_info[0x10] = "Inconnue"

def get_distance():
    """
        Cette fonction permet de récupérer la distance mesurée par un capteur.
        La commande de lecture de distance est envoyée au capteur et sa réponse est stocker dans la variable data.
        On vérifie qu'elle soit au bon format puis on récupère les octets indiquant la distance.
        Un correctif est appliqué sur la distance mais n'est pas obligatoire sur tous les capteurs.
        
        Args:
            ...
            
        Returns:
            int: Distance mesurée en cm
    """
    try:
        # Commande demande de mesure de distance
        i2c.writeto(TFMINI_ADDR, b'\x5a\x05\x00\x01\x60')
        time.sleep_ms(15) # Laisse le temps au capteur de préparer la trame de données
        
        # Lecture 9 octets de données de mesure
        data = i2c.readfrom(TFMINI_ADDR, 9)
        
        # Vérification protocole standard TFMini
        if len(data) >= 9 and data[0] == 0x59 and data[1] == 0x59:
            # Distance codée sur 2 octets
            # Octet 2 (poids faible) + octet 3 (poids fort) décalé de 8 bits vers la gauche
            distance = data[2] + (data[3] << 8)
            distance = round(distance * 1.05)
            return distance
    except:
        print("\nErreur dans la récupération de la mesure.")
        return None
    
    return None


def use_data():
    """
        Cette fonction affiche et gère les mesures.
        On initialise toutes nos variables à la première mesure pour éviter une erreur en début de boucle.
        On vérifie si la distance est prise en compte par le capteur et on compare la moyenne avec la précédente.
        Une fois acceptée, on peut calculer une moyenne à partir de trois valeurs successives puis on affiche les informations.
        Si la différence entre les deux dernières moyennes est plus élevée que la marge configurée, une erreur est comptée.
        Trop d'erreur de suite indique qu'il s'agit d'une valeur correcte.
        
        Args:
            timer (timer): Timer par interruption
            
        Returns:
            ...
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
                # Sécurité au cas où une mesure intermédiaire renverrait None
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
                
                # Après réinitialisation erreurs: retour au cycle normal
                if error == 0:
                    timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)
                        
                return hauteur
            
            else:
                # Variance trop élevée = ignorée + erreur + temps de mesure raccourci
                timer_sensor.init(mode=Timer.PERIODIC, period=error_period_ms, callback=interrupt_hauteur)
                error += 1
                if count > prep:
                    print(f"{error} erreur(s)\n")
            
                if error > max_error:
                    # Erreurs maximales atteintes = réinitialisation des variables + reprise du cycle normal
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
            # Donnée lue mais en dehors des limites du capteur
            count += 1
            print("[Adresse: {}]\nHors limite ({} cm)\n\n".format(hex(TFMINI_ADDR), mesure))
            
            return hauteur
            
def interrupt_hauteur(timer):
    global mesure_hauteur
    mesure_hauteur = 1
    return mesure_hauteur
            
timer_sensor = Timer(0)
timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)

print("Démarrage du programme de mesure...")
while True:
    if mesure_hauteur == 1:
        hauteur = use_data()
        mesure_hauteur = 0
    time.sleep_ms(10)  # Petite pause pour soulager le processeur et stabiliser la boucle principale
