"""
sys.path: ECVD_SIM7080_ThingSpeak.py
====================================

Système de communication cellulaire pour le projet Pico-centrale Hydroélectrique (Viseta).
Ce script est développé dans le cadre du BTS CIEL Option B (Électronique et Réseau).
Il correspond aux travaux de l'Étudiant n°4 (Chris GAVO) sur le système ECVD 
(Électronique de Contrôle de la Vanne de Décharge).

Sa tâche principale est de piloter un modem SIM7080 via des commandes AT depuis 
l'ESP32 afin d'établir un contexte de données (PDP), de récupérer l'heure et l'antenne
de rattachement du réseau, et d'envoyer les mesures de supervision sur ThingSpeak.

.. note::
   - Utilisation de l'UART 2 de l'ESP32 (Broche 16 pour RX, Broche 17 pour TX).
   - Vitesse de communication fixée à 57600 bauds.
   - Carte SIM configurée sur le réseau IoT 1NCE.

:Version: 1.1
:Date: Mai 2026
:Auteur: Chris GAVO - Étudiant n°4
"""

from machine import UART, Pin
import time
import random

# --- Configuration de l'interface UART de l'ESP32 ---
# Utilisation de l'UART 2, configuré à 57600 bauds pour communiquer avec le modem SIM7080
uart = UART(2, 57600, tx=21, rx=22)
uart.init(57600, bits=8, parity=None, stop=1)


def send_at(command, delay=1, flush=True, ignore_error_cmds=None):
    """Envoie une commande AT au module SIM7080 et récupère la réponse.

    Cette fonction utilitaire automatise l'écriture sur le bus UART, applique
    une temporisation nécessaire au traitement de la commande par le modem,
    puis extrait et décode la réponse textuelle renvoyée.

    :param command: La commande AT à transmettre (sans le caractère de retour à la ligne).
    :type command: str
    :param delay: Le temps d'attente en secondes après l'envoi pour laisser le modem répondre, par défaut 1.
    :type delay: int, optional
    :param flush: Si True, vide complètement les buffers de l'UART après lecture, par défaut True.
    :type flush: bool, optional
    :param ignore_error_cmds: Liste de commandes pour lesquelles l'affichage d'un message "ERROR" ne doit pas être bloquant, par défaut None.
    :type ignore_error_cmds: list of str, optional
    :return: La chaîne de caractères décodée contenant la réponse du module.
    :rtype: str
    """
    if ignore_error_cmds is None:
        ignore_error_cmds = []
    print(f"Envoi: {command}")
    uart.write(command + '\r\n')
    time.sleep(delay)
    
    response = b''
    while uart.any():
        response += uart.read()
        
    if flush:
        while uart.any():
            uart.read()
            
    try:
        decoded = response.decode('utf-8')
    except Exception:
        decoded = str(response)
        
    if "ERROR" in decoded and command in ignore_error_cmds:
        print(f"Réponse: {decoded.strip()} (erreur attendue, sans conséquence)")
    else:
        print(f"Réponse: {decoded.strip()}")
        
    return decoded


def get_network_time_and_cell():
    """Récupère l'horodatage réseau ainsi que les identifiants de la cellule de l'antenne relais.

    Permet d'extraire l'heure interne du réseau GSM (CCLK) pour dater les mesures, 
    ainsi que le LAC (Location Area Code) et le Cell ID afin d'avoir un diagnostic de 
    localisation du système sur le terrain.

    :return: Un tuple contenant la date/heure, le code de zone LAC, et l'identifiant de cellule.
    :rtype: tuple (str, str, str)
    """
    send_at('AT+CTZU=1', 1)  # Activation de la mise à jour automatique du temps par le réseau
    resp_time = send_at('AT+CCLK?', 1)
    
    date_heure = "Indisponible"
    for line in resp_time.split('\n'):
        if '+CCLK:' in line:
            date_heure = line.strip().replace('+CCLK: ', '').replace('"', '')
            
    resp_cell = send_at('AT+CEREG?', 1)
    lac = cellid = "Indisponible"
    for line in resp_cell.split('\n'):
        if '+CEREG:' in line:
            champs = line.strip().split(',')
            if len(champs) >= 5:
                lac = champs[2].replace('"', '')
                cellid = champs[3].replace('"', '')
                
    print(f"Date/heure du réseau GSM : {date_heure}")
    print(f"LAC (zone): {lac} | Cell ID (antenne): {cellid}")
    return date_heure, lac, cellid


def wait_for_network(timeout=120):
    """Attend l'enregistrement effectif du modem sur le réseau cellulaire (LTE-M / NB-IoT).

    Boucle de manière non-bloquante jusqu'à obtenir un code d'état d'enregistrement 
    indiquant que l'appareil est connecté en mode local ou en roaming (itinérance).

    :param timeout: Temps maximum d'attente en secondes avant abandon, par défaut 120.
    :type timeout: int, optional
    :return: True si l'enregistrement réseau est validé, False en cas de timeout.
    :rtype: bool
    """
    print("Attente de l'enregistrement réseau...")
    start = time.time()
    while time.time() - start < timeout:
        resp = send_at('AT+CEREG?', 2)
        if "+CEREG: 0,1" in resp or "+CEREG: 0,5" in resp or "+CEREG: 2,5" in resp:
            print("Module enregistré sur le réseau !")
            return True
        time.sleep(2)
    print("Erreur : module non enregistré sur le réseau.")
    return False


def is_pdp_active(resp):
    """Analyse la réponse de la commande AT+CNACT? pour vérifier le statut DATA.

    :param resp: La chaîne de caractères brute renvoyée par le modem.
    :type resp: str
    :return: True si le contexte PDP est actif avec une adresse IP valide assignée, False sinon.
    :rtype: bool
    """
    lines = resp.split('\n')
    for line in lines:
        if '+CNACT: 1,1' in line and '0.0.0.0' not in line:
            return True
    return False


def wait_for_pdp_activation(apn="iot.1nce.net", timeout=120):
    """Force et attend l'activation du contexte de paquets de données (PDP Context).

    Envoie la commande d'activation réseau et vérifie en boucle l'obtention d'une
    adresse IP fournie par l'opérateur internet IoT.

    :param apn: Nom du point d'accès de l'opérateur réseau utilisé, par défaut "iot.1nce.net".
    :type apn: str, optional
    :param timeout: Temps maximum d'attente en secondes, par défaut 120.
    :type timeout: int, optional
    :return: True si la connexion DATA est pleinement établie, False sinon.
    :rtype: bool
    """
    print("Attente de l'activation DATA/PDP réelle...")
    start = time.time()
    while time.time() - start < timeout:
        resp = send_at('AT+CNACT=1,1', 5, ignore_error_cmds=['AT+CNACT=1,1'])
        if "OK" in resp or "+APP PDP: 1,ACTIVE" in resp:
            resp2 = send_at('AT+CNACT?', 2)
            if is_pdp_active(resp2):
                print("Contexte PDP DATA actif !")
                return True
        print("PDP pas encore prêt, nouvelle tentative dans 5s...")
        time.sleep(5)
    print("Impossible d'activer le contexte PDP après attente.")
    return False


def wait_for_pdp(timeout=30):
    """Vérifie périodiquement si le contexte DATA est toujours actif sur le modem.

    :param timeout: Temps maximum d'interrogation en secondes, par défaut 30.
    :type timeout: int, optional
    :return: True si le statut est actif, False sinon.
    :rtype: bool
    """
    print("Attente de l'activation du contexte PDP...")
    start = time.time()
    while time.time() - start < timeout:
        resp = send_at('AT+CNACT?', 2)
        if is_pdp_active(resp):
            print("Contexte PDP actif !")
            return True
        time.sleep(2)
    print("Erreur : contexte PDP non activé.")
    return False


def test_http(url, get_path):
    """Initialise, configure et exécute une requête HTTP GET vers un serveur distant.

    Gère l'allocation de la mémoire tampon pour les entêtes et le corps de message du 
    client HTTP embarqué dans le SIM7080, effectue la requête et lit le résultat.

    :param url: L'URL racine du serveur de destination (ex: "http://api.thingspeak.com").
    :type url: str
    :param get_path: Le chemin de la ressource incluant l'API Key et les paramètres des champs.
    :type get_path: str
    :return: True si la transaction HTTP s'est finalisée avec succès, False sinon.
    :rtype: bool
    """
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])  # Déconnexion préventive d'une session précédente
    send_at(f'AT+SHCONF="URL","{url}"', 1)
    send_at('AT+SHCONF="BODYLEN",1024', 1)
    send_at('AT+SHCONF="HEADERLEN",350', 1)
    
    resp = send_at('AT+SHCONN', 5)  # Demande d'ouverture de connexion HTTP
    if 'OK' not in resp:
        print(f"Erreur : impossible d’ouvrir la connexion HTTP vers {url}.")
        return False
        
    send_at(f'AT+SHREQ="{get_path}",1', 5)  # Émission de la requête GET (paramètre '1' pour GET)
    resp = send_at('AT+SHREAD=0,100', 2, ignore_error_cmds=['AT+SHREAD=0,100'])
    
    if "ERROR" in resp:
        print("Aucune donnée à lire ou réponse vide (normal pour ThingSpeak).")
    else:
        print(f"Réponse serveur {url} :", resp)
        
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])  # Clôture proprement la session HTTP
    return True


def send_thingspeak(api_key, value1, value2):
    """Supervise et sécurise l'acheminement des données vers ThingSpeak.

    Cette fonction vérifie l'état du réseau avant l'envoi, configure les serveurs DNS
    de Google (8.8.8.8) pour la résolution du nom de domaine, structure la chaîne de 
    requête GET avec l'API Key d'écriture et les deux champs de données, puis appelle le client HTTP.

    :param api_key: Clé d'écriture unique du canal ThingSpeak de l'installation.
    :type api_key: str
    :param value1: Valeur numérique du premier paramètre à envoyer (ex: Hauteur d'eau).
    :type value1: int or float
    :param value2: Valeur numérique du second paramètre à envoyer (ex: Niveau de charge batterie).
    :type value2: int or float
    :return: True si le téléversement a réussi, False en cas de rupture de communication.
    :rtype: bool
    """
    send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)
    send_at('AT+CNACT=1,1', 5, ignore_error_cmds=['AT+CNACT=1,1'])
    
    if not wait_for_pdp():
        return False
        
    time.sleep(2)
    send_at('AT+CDNSCFG="8.8.8.8","8.8.4.4"', 1)  # Spécification des serveurs DNS de secours
    time.sleep(1)
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])
    
    resp = send_at('AT+CEREG?', 2)
    if not ("+CEREG: 0,1" in resp or "+CEREG: 0,5" in resp or "+CEREG: 2,5" in resp):
        print("Réseau perdu avant HTTP, attente du retour du réseau...")
        if not wait_for_network():
            return False
            
    url = "http://api.thingspeak.com"
    # Formatage de la requête HTTP incluant les deux champs imposés par le protocole du projet
    get_path = f'/update?api_key={api_key}&field1={value1}&field2={value2}'
    print(f"\n--- Envoi vers ThingSpeak (F1:{value1}, F2:{value2}) ---")
    
    ok = test_http(url, get_path)
    return ok


def init_sim7080():
    """Initialise de bout en bout les paramètres de configuration du modem SIM7080.

    Exécute le cycle complet d'initialisation : vérification de la présence de la carte SIM,
    contrôle de la puissance du signal (CSQ), forçage du modem sur le réseau LTE (AT+CNMP=38),
    sélection du mode NB-IoT/eMTC (AT+CMNB=1) et attente finale de la stabilisation DATA.

    :raises SystemExit: Interrompt définitivement l'exécution du script en cas de panne matérielle réseau non résolue.
    :return: None
    """
    print("Initialisation SIM7080...")

    send_at('AT', 1)
    send_at('AT+CPIN?', 1)    # Vérification de l'état du code PIN de la carte SIM
    send_at('AT+CSQ', 1)     # Mesure de la qualité de réception du signal RSSI
    send_at('AT+CFUN=1', 2)   # Activation complète des fonctionnalités RF du module
    send_at('AT+CNMP=38', 2)  # Forçage du mode de réseau : LTE uniquement
    send_at('AT+CMNB=1', 2)   # Sélection de la préférence de bande de transmission : CAT-M (eMTC)
    send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)  # Définition du contexte APN
    send_at('AT+COPS=0', 2)   # Sélection automatique de l'opérateur réseau
    send_at('AT+CEREG=2', 2)  # Active l'enregistrement réseau avec données de localisation (LAC/Cell ID)

    if not wait_for_network():
        print("Erreur réseau, arrêt du programme.")
        raise SystemExit

    print("Attente de stabilisation du réseau (8 secondes)...")
    time.sleep(8)

    if not wait_for_pdp_activation():
        print("Impossible d'activer la DATA, arrêt du programme.")
        raise SystemExit


# =============================================================================
# POINT D'ENTRÉE PRINCIPAL / BOUCLE SURVEILLANCE
# =============================================================================

if __name__ == "__main__":
    # Étape 1 : Initialisation matérielle et protocolaire du modem
    init_sim7080()

    # Configuration des variables d'environnement de supervision
    api_key = "BET2MXURJRI3AVQD"  # Clé d'accès du canal ThingSpeak de démonstration
    temps = 30                    # Fréquence d'envoi fixée à 30s pour la phase de soutenance/tests
    compteur_succes = 0           # Compteur logiciel d'acquittements serveurs réussis

    print(f"\nLancement du monitoring (Intervalle : {temps}s)")

    while True:
        # Étape 2 : Acquisition/Simulation des deux grandeurs physiques requises par le cahier des charges
        val1 = random.randint(1, 50)     # Simulation Hauteur d'eau moyenne (Élève 1 / Capteur ultrason)
        val2 = random.randint(51, 100)   # Simulation Pourcentage Batterie / Santé (Élève 5 / Energie)
        
        print(f"\n--- Cycle d'envoi ---")
        MAX_ATTEMPTS = 5
        envoi_reussi_ce_cycle = False
        
        # Algorithme de résilience : Gestion de 5 tentatives max en cas de perte de liaison transitoire
        for attempt in range(MAX_ATTEMPTS):
            print(f"Tentative {attempt+1}/{MAX_ATTEMPTS}...")
            ok = send_thingspeak(api_key, val1, val2)
            
            if ok:
                compteur_succes += 1 
                print(f"SUCCÈS ! Données transmises.")
                print(f"Nombre total d'envois réussis : {compteur_succes}")
                envoi_reussi_ce_cycle = True
                break
            else:
                print("Échec technique, nouvelle tentative dans 10s...")
                time.sleep(10)
                
        if not envoi_reussi_ce_cycle:
            print(f"ALERTE : Échec après {MAX_ATTEMPTS} tentatives.")

        # Récupération de l'heure et diagnostic antenne pour enrichir le journal de bord
        get_network_time_and_cell()
        
        print(f"Pause de {temps} secondes...")
        time.sleep(temps)