import time
from machine import UART

def envoyer_commande_at(commande, timeout_sec=1):
    """Envoie une commande AT au modem et récupère sa réponse textuelle.

    Cette fonction centralise la communication série avec le modem SIM7080G.
    Elle ajoute automatiquement les caractères de fin de ligne, attend la
    réponse pendant le délai imparti, puis gère le décodage des données reçues.

    Args:
        commande (str): La commande AT à envoyer (ex: 'AT', 'AT+SHCONN').
        timeout_sec (int, float): Le temps d'attente en secondes laissé au 
            modem pour répondre (par défaut: 1).

    Returns:
        str: La réponse du modem nettoyée et décodée, ou une chaîne vide 
            si le modem n'a pas répondu.
    """
    # 1. Configuration de la liaison série (UART 2)
    uart = UART(2, 57600, tx=17, rx=16)
    uart.init(57600, bits=8, parity=None, stop=1)

    # 2. Nettoyage préventif du buffer (évite de lire de vieux résidus)
    while uart.any():
        uart.read()

    # 3. Envoi de la commande avec le retour à la ligne obligatoire (\r\n)
    uart.write(commande + '\r\n') 

    # 4. Temporisation pour laisser le modem formuler sa réponse
    time.sleep(timeout_sec)

    # 5. Lecture et traitement de la réponse
    if uart.any():
        donnees_brutes = uart.read()
        
        # Décodage sécurisé : 'ignore' évite un crash si un caractère bizarre arrive
        reponse_decodee = donnees_brutes.decode('utf-8', errors='ignore')
        
        # Suppression des espaces et sauts de ligne inutiles (strip)
        return reponse_decodee.strip()
    
    return ""

# ==============================================================================
# EXEMPLE D'UTILISATION
# ==============================================================================
if __name__ == "__main__":
    # Test de la commande de connexion HTTP
    cmd = 'AT+SHCONN'
    resultat = envoyer_commande_at(cmd, timeout_sec=1)
    
    print(f"Commande envoyée : {cmd}")
    print(f"Réponse du modem :\n{resultat}")