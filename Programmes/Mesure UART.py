from machine import UART, Pin, Timer
import time

# Initialisation du bus UART (au lieu de I2C)
# Pins configurable
# Vitesse par défaut du TFmini Plus en UART = 115200 bauds
uart = UART(1, baudrate=115200, tx=Pin(21), rx=Pin(22), bits=8, parity=None, stop=1)

dist1, dist2, dist3, hauteur = 0, 0, 0, 0 		# Stockage des 3 dernières valeurs et de la moyenne
error, count = 0, 0 							# Valeurs des erreurs et du compteur
max_error, max_marge = 2, 10   					# Nombre d'erreurs tolérées et variation maximale autorisée (en cm) entre deux mesures
timer_period_ms, error_period_ms = 3000, 1000	# Fréquence de mesure normale / erreur détectée
att_moy = 100									# Attente en ms entre chaque distance mesurée
mesure_hauteur = 0								# Flag du timer
prep, correctif = 0, 1.1						# Nombre mesure préparation / correctif appliqué à la mesure
calibr = (timer_period_ms*(prep+1))/1000		# Calcul du temps de calibration au démarrage
version_capteur = "Inconnue"                    # Stockage de la version du capteur

def get_firmware_version():
    """
        Cette fonction permet de récupérer la version du capteur détecté.
        On envoie d'abord la commande à l'adresse du capteur pour récupérer sa version puis on lit sa réponse.
        On formate ensuite les octets qui nous intéresse dans une variable.
        
        Args:
            ...
            
        Returns:
            string: Version du capteur trouvée
    """
    try:
        # Nettoyage du tampon série avant envoi *
        if uart.any():
            uart.read(uart.any())
            
        # Commande version du firmware
        uart.write(b'\x5a\x04\x01\x5f')
        time.sleep_ms(50) # Temps d'attente ajusté pour éviter le gel du bus
        
        # Lecture de la réponse *
        if uart.any():
            res = uart.read(uart.any())
            
            # Vérification trame reçue (7 octets, octet 0 entête 0x5A, octet 2 confirmation ID commande 0x01)
            for i in range(len(res) - 6):
                if res[i] == 0x5a and res[i+2] == 0x01:
                    # Formatage version
                    return "V{}.{}.{}".format(res[i+3], res[i+4], res[i+5])
    except:
        pass
    
    return "Inconnue"


print("Recherche de capteurs UART...") # * Modifié pour refléter l'UART
version_capteur = get_firmware_version()
if version_capteur != "Inconnue":
    print("Trouvé : Version : {}".format(version_capteur))
else:
    print("\nAucun capteur détecté. Utilisation de la valeur par défaut")


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
        # * En mode UART, le capteur envoie les données en continu. On lit le tampon série :
        if uart.any() >= 9:
            data = uart.read(uart.any())
            
            # Vérification protocole standard TFMini (Balayage pour trouver l'en-tête)
            for i in range(len(data) - 8):
                if data[i] == 0x59 and data[i+1] == 0x59:
                    # Distance codée sur 2 octets
                    # Octet 2 (poids faible) + octet 3 (poids fort) décalé de 8 bits vers la gauche
                    distance = data[i+2] + (data[i+3] << 8)
                    distance = round(distance * correctif)
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
                ver = version_capteur
                
                # Affiche les résultats
                if count > prep:
                    print("[Interface: UART | Version: {}]\nDistance n°{}: {} cm\nFormat bytes: {}\n\n".format(ver, count, hauteur, octets_distance))
                
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
            print("[Interface: UART]\nHors limite ({} cm)\n\n".format(mesure))
            
            return hauteur
            
def interrupt_hauteur(timer):
    global mesure_hauteur
    mesure_hauteur = 1
    return mesure_hauteur
            
timer_sensor = Timer(0)
timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)

print("Démarrage du programme de mesure...")
print("Mesures de calibration en cours... ({} s)\n\n".format(calibr))
while True:
    if mesure_hauteur == 1:
        hauteur = use_data()
        mesure_hauteur = 0
