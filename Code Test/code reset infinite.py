from machine import UART, Pin, reset   # reset() : redémarre le microcontrôleur en cas d'échec critique
import time
import random

# ==============================================================================
# CONFIGURATION DU RESET AUTOMATIQUE
# ==============================================================================

MAX_ECHECS_CONSECUTIFS = 10   # Nombre d'envois ratés d'affilée avant reset total
MAX_ECHECS_INIT = 3           # Nombre de tentatives d'initialisation avant reset
DELAI_RESET = 5               # Secondes d'attente avant d'effectuer le reset (pour lire les logs)

echecs_consecutifs = 0        # Compteur d'échecs d'envoi consécutifs (remis à 0 à chaque succès)
tentatives_init = 0           # Compteur de tentatives d'initialisation échouées


# ==============================================================================
# CONFIGURATION DE LA LIAISON SÉRIE (UART)
# ==============================================================================

uart = UART(2, 57600, tx=17, rx=16)
uart.init(57600, bits=8, parity=None, stop=1)


# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def soft_reset_modem():
    """
    Effectue un reset logiciel du modem SIM7080G via la commande AT.

    AT+CFUN=1,1 demande au modem de se réinitialiser complètement (équivalent
    d'un redémarrage matériel du modem, sans redémarrer le microcontrôleur).
    On attend ensuite 10 secondes pour laisser le modem redémarrer.

    Utilisé quand le modem est dans un état incohérent mais que le
    microcontrôleur fonctionne encore correctement.
    """
    print("\n[RESET MODEM] Reset logiciel du modem en cours...")
    uart.write('AT+CFUN=1,1\r\n')   # Commande de reset du modem
    time.sleep(10)                   # Attente du redémarrage du modem
    print("[RESET MODEM] Modem redémarré, reprise de l'initialisation.")


def hard_reset():
    """
    Effectue un reset matériel complet du microcontrôleur (ESP32 ou compatible).

    machine.reset() redémarre complètement la carte, comme si on avait coupé
    et rebranché l'alimentation. Tout le programme repart de zéro.

    Utilisé en dernier recours quand le soft reset du modem ne suffit plus,
    ou quand trop d'échecs consécutifs ont été détectés.
    """
    print(f"\n[RESET TOTAL] Redémarrage du microcontrôleur dans {DELAI_RESET}s...")
    time.sleep(DELAI_RESET)
    reset()   # Redémarre le microcontrôleur (machine.reset)


def send_at(command, delay=1, flush=True, ignore_error_cmds=None):
    """
    Envoie une commande AT au modem via UART et retourne sa réponse.

    Paramètres :
        command           : la commande AT à envoyer (ex: 'AT+CSQ')
        delay             : temps d'attente avant lecture de la réponse
        flush             : vide le buffer UART après lecture si True
        ignore_error_cmds : liste de commandes dont les erreurs sont tolérées
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
    except:
        decoded = str(response)

    if "ERROR" in decoded and command in ignore_error_cmds:
        print(f"Réponse: {decoded.strip()} (erreur attendue, sans conséquence)")
    else:
        print(f"Réponse: {decoded.strip()}")

    return decoded


def get_network_time_and_cell():
    """
    Récupère l'heure réseau GSM et les infos de localisation de l'antenne.
    Retourne la date/heure, le LAC (zone) et le Cell ID (antenne).
    """
    send_at('AT+CTZU=1', 1)
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
                lac    = champs[2].replace('"', '')
                cellid = champs[3].replace('"', '')

    print(f"Date/heure du réseau GSM : {date_heure}")
    print(f"LAC (zone): {lac} | Cell ID (antenne): {cellid}")
    return date_heure, lac, cellid


def wait_for_network(timeout=120):
    """
    Attend que le modem soit enregistré sur le réseau GSM/NB-IoT.
    Retourne True si enregistré dans le délai, False sinon.
    """
    print("Attente de l'enregistrement réseau...")
    start = time.time()
    while time.time() - start < timeout:
        resp = send_at('AT+CEREG?', 2)
        if ("+CEREG: 0,1" in resp or
                "+CEREG: 0,5" in resp or
                "+CEREG: 2,5" in resp):
            print("Module enregistré sur le réseau !")
            return True
        time.sleep(2)
    print("Erreur : module non enregistré sur le réseau.")
    return False


def is_pdp_active(resp):
    """
    Vérifie si le contexte PDP est actif avec une adresse IP valide.
    Retourne True si actif, False sinon.
    """
    lines = resp.split('\n')
    for line in lines:
        if '+CNACT: 1,1' in line and '0.0.0.0' not in line:
            return True
    return False


def wait_for_pdp_activation(apn="iot.1nce.net", timeout=120):
    """
    Active et attend que le contexte de données PDP soit opérationnel.
    Retourne True si actif, False en cas d'échec.
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
    """
    Vérifie rapidement que le contexte PDP est actif.
    Retourne True si actif, False sinon.
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
    """
    Effectue une requête HTTP GET via les commandes AT du modem SIM7080G.
    Retourne True si la connexion a été établie avec succès.
    """
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])
    send_at(f'AT+SHCONF="URL","{url}"', 1)
    send_at('AT+SHCONF="BODYLEN",1024', 1)
    send_at('AT+SHCONF="HEADERLEN",350', 1)

    resp = send_at('AT+SHCONN', 5)
    if 'OK' not in resp:
        print(f"Erreur : impossible d'ouvrir la connexion HTTP vers {url}.")
        return False

    send_at(f'AT+SHREQ="{get_path}",1', 5)
    resp = send_at('AT+SHREAD=0,100', 2, ignore_error_cmds=['AT+SHREAD=0,100'])
    if "ERROR" in resp:
        print("Aucune donnée à lire ou réponse vide (normal pour ThingSpeak).")
    else:
        print(f"Réponse serveur {url} :", resp)

    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])
    return True


def send_thingspeak(api_key, value1, value2):
    """
    Envoie deux valeurs vers ThingSpeak via HTTP GET.
    Retourne True si l'envoi a réussi.
    """
    send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)
    send_at('AT+CNACT=1,1', 5, ignore_error_cmds=['AT+CNACT=1,1'])

    if not wait_for_pdp():
        return False

    time.sleep(2)
    send_at('AT+CDNSCFG="8.8.8.8","8.8.4.4"', 1)
    time.sleep(1)
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])

    resp = send_at('AT+CEREG?', 2)
    if not ("+CEREG: 0,1" in resp or
            "+CEREG: 0,5" in resp or
            "+CEREG: 2,5" in resp):
        print("Réseau perdu avant HTTP, attente du retour du réseau...")
        if not wait_for_network():
            return False

    url = "http://api.thingspeak.com"
    get_path = f'/update?api_key={api_key}&field1={value1}&field2={value2}'
    print(f"\n--- Envoi vers ThingSpeak (F1:{value1}, F2:{value2}) ---")
    ok = test_http(url, get_path)
    return ok


def init():
    """
    Initialise le modem SIM7080G étape par étape via des commandes AT.
    Retourne la fonction init (valeur truthy) si succès, False sinon.
    """
    print("\nInitialisation SIM7080...")

    if send_at('AT'):
        print("Module SIM7080 présent - liaison série ok !")
    else:
        print("Le module ne répond pas correctement.")
        return False

    reponse = send_at('ATE0', 0.5)
    if reponse:
        print("L'écho est désactivé")
    else:
        print("Problème désactivation de l'écho...")

    reponse = send_at('AT+CPIN?')
    if reponse and "+CPIN: READY" in reponse:
        print("Carte SIM détectée et prête")
    else:
        print("Problème carte SIM...")
        return False

    reponse = send_at('AT+CSQ')
    if reponse and "+CSQ" in reponse:
        print("Signal radio détecté - " + reponse.strip())
    else:
        print("Signal radio introuvable...")

    reponse = send_at('AT+CFUN=1', 2)
    if reponse and "OK" in reponse:
        print("Modem en mode pleine fonctionnalité")
    else:
        print("Problème activation du modem...")
        return False

    reponse = send_at('AT+CNMP=38', 2)
    if reponse and "OK" in reponse:
        print("Mode réseau : LTE uniquement")
    else:
        print("Problème configuration mode réseau...")
        return False

    reponse = send_at('AT+CMNB=1', 2)
    if reponse and "OK" in reponse:
        print("Mode NB-IoT activé")
    else:
        print("Problème activation NB-IoT...")
        return False

    reponse = send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)
    if reponse and "OK" in reponse:
        print("Contexte PDP configuré - APN : iot.1nce.net")
    else:
        print("Problème configuration APN...")
        return False

    reponse = send_at('AT+COPS=0', 2)
    if reponse and "OK" in reponse:
        print("Sélection opérateur : automatique")
    else:
        print("Problème sélection opérateur...")
        return False

    reponse = send_at('AT+CEREG=2', 2)
    if reponse and "OK" in reponse:
        print("Notifications d'enregistrement réseau activées")
    else:
        print("Problème activation CEREG...")
        return False

    print("\nInitialisation terminée avec succès !")
    return init


# ==============================================================================
# DÉMARRAGE AVEC RESET AUTOMATIQUE SI L'INIT ÉCHOUE
# ==============================================================================

# Boucle de démarrage : tente d'initialiser le modem jusqu'à MAX_ECHECS_INIT fois.
# Si toutes les tentatives échouent, un reset matériel complet est déclenché.
while not init():
    tentatives_init += 1
    print(f"\n[INIT] Échec tentative {tentatives_init}/{MAX_ECHECS_INIT}")

    if tentatives_init >= MAX_ECHECS_INIT:
        # Trop d'échecs d'init → reset total du microcontrôleur
        print("[INIT] Trop d'échecs d'initialisation → reset total.")
        hard_reset()
    else:
        # Avant de réessayer, on tente un soft reset du modem
        print("[INIT] Tentative de reset du modem avant nouvel essai...")
        soft_reset_modem()

print("Modem prêt, on peut envoyer des données.")
tentatives_init = 0   # Remise à zéro du compteur d'init après succès


# --- Attente du réseau avec reset si indisponible ---
# Si le réseau n'est pas disponible après le timeout, reset matériel complet
if not wait_for_network():
    print("[RÉSEAU] Réseau indisponible → reset total.")
    hard_reset()

print("Attente de stabilisation du réseau (8 secondes)...")
time.sleep(8)


# --- Activation DATA avec reset si impossible ---
# Si le contexte PDP ne peut pas être activé, reset matériel complet
if not wait_for_pdp_activation():
    print("[PDP] Impossible d'activer la DATA → reset total.")
    hard_reset()


# ==============================================================================
# PARAMÈTRES DE SESSION
# ==============================================================================

api_key = "BET2MXURJRI3AVQD"   # Clé d'écriture ThingSpeak
temps = 15                       # Intervalle en secondes entre chaque cycle d'envoi
compteur_succes = 0              # Compteur cumulatif des envois réussis

print(f"\nLancement du monitoring (Intervalle : {temps}s)")


# ==============================================================================
# BOUCLE PRINCIPALE — s'exécute indéfiniment
# ==============================================================================

while True:

    # --- Génération de données simulées ---
    val1 = random.randint(1, 49)    # Simule un capteur (ex : température)
    val2 = random.randint(50, 100)  # Simule un second capteur (ex : humidité)

    print(f"\n--- Cycle d'envoi ---")

    MAX_ATTEMPTS = 5
    envoi_reussi_ce_cycle = False

    # --- Tentatives d'envoi avec mécanisme de retry ---
    for attempt in range(MAX_ATTEMPTS):
        print(f"Tentative {attempt+1}/{MAX_ATTEMPTS}...")
        ok = send_thingspeak(api_key, val1, val2)

        if ok:
            # Succès : on remet le compteur d'échecs consécutifs à zéro
            compteur_succes += 1
            echecs_consecutifs = 0
            print(f"SUCCÈS ! Données transmises.")
            print(f"Nombre total d'envois réussis : {compteur_succes}")
            envoi_reussi_ce_cycle = True
            break
        else:
            print("Échec technique, nouvelle tentative dans 10s...")
            time.sleep(10)

    # --- Gestion des échecs consécutifs ---
    if not envoi_reussi_ce_cycle:
        echecs_consecutifs += 1
        print(f"ALERTE : Échec après {MAX_ATTEMPTS} tentatives.")
        print(f"Échecs consécutifs : {echecs_consecutifs}/{MAX_ECHECS_CONSECUTIFS}")

        if echecs_consecutifs >= MAX_ECHECS_CONSECUTIFS:
            # Seuil critique atteint : le système est probablement bloqué
            # On tente d'abord un soft reset du modem avant le hard reset
            print(f"\n[WATCHDOG] {MAX_ECHECS_CONSECUTIFS} échecs consécutifs détectés !")
            print("[WATCHDOG] Tentative de reset du modem...")
            soft_reset_modem()

            # Après le soft reset, on retente l'initialisation complète
            if init() and wait_for_network() and wait_for_pdp_activation():
                print("[WATCHDOG] Récupération réussie après soft reset du modem.")
                echecs_consecutifs = 0   # Le modem répond à nouveau : on repart à zéro
            else:
                # Le soft reset n'a pas suffi → reset matériel complet
                print("[WATCHDOG] Soft reset insuffisant → reset total du microcontrôleur.")
                hard_reset()

    # --- Récupération des infos réseau après chaque cycle ---
    get_network_time_and_cell()

    # --- Pause avant le prochain cycle ---
    print(f"Pause de {temps} secondes...")
    time.sleep(temps)