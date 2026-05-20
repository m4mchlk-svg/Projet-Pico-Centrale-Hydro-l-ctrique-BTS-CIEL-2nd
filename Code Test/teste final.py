from machine import UART, Pin, reset
import time
import random

# ==============================================================================
# CONFIGURATION DU RESET AUTOMATIQUE
# ==============================================================================
MAX_ECHECS_CONSECUTIFS = 10  
MAX_ECHECS_INIT = 3          
DELAI_RESET = 5              

echecs_consecutifs = 0        
tentatives_init = 0           

# ==============================================================================
# CONFIGURATION DE LA LIAISON SÉRIE (UART)
# ==============================================================================
uart = UART(2, 57600, tx=17, rx=16)
uart.init(57600, bits=8, parity=None, stop=1)

# ==============================================================================
# FONCTIONS UTILITAIRES
# ==============================================================================

def soft_reset_modem():
    print("\n[RESET MODEM] Reset logiciel du modem en cours...")
    uart.write('AT+CFUN=1,1\r\n')
    time.sleep(10) # Laisse le temps au modem de redémarrer et réafficher l'UART
    print("[RESET MODEM] Modem redémarré, reprise de l'initialisation.")

def hard_reset():
    print(f"\n[RESET TOTAL] Redémarrage du microcontrôleur dans {DELAI_RESET}s...")
    time.sleep(DELAI_RESET)
    reset()

def send_at(command, delay=1, flush=True, ignore_error_cmds=None):
    if ignore_error_cmds is None:
        ignore_error_cmds = []

    print(f"Envoi: {command}")
    
    # Nettoyage du buffer d'entrée avant d'envoyer pour éviter les résidus
    while uart.any():
        uart.read()
        
    uart.write(command + '\r\n')
    time.sleep(delay)

    response = b''
    while uart.any():
        response += uart.read()

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
            # Remplacement des espaces pour homogénéiser le format de réponse
            line_clean = line.strip().replace(' ', '')
            champs = line_clean.split(',')
            # Sécurité anti-crash : On valide qu'on a bien reçu le LAC et le Cell ID
            if len(champs) >= 4:
                lac    = champs[2].replace('"', '')
                cellid = champs[3].replace('"', '')

    print(f"Date/heure du réseau GSM : {date_heure}")
    print(f"LAC (zone): {lac} | Cell ID (antenne): {cellid}")
    return date_heure, lac, cellid

def wait_for_network(timeout=120):
    print("Attente de l'enregistrement réseau...")
    start = time.time()
    while time.time() - start < timeout:
        resp = send_at('AT+CEREG?', 2)
        # Nettoyage des espaces pour éviter les faux négatifs de parsing
        resp_clean = resp.replace(" ", "")
        if ("+CEREG:0,1" in resp_clean or 
            "+CEREG:0,5" in resp_clean or 
            "+CEREG:2,1" in resp_clean or 
            "+CEREG:2,5" in resp_clean):
            print("Module enregistré sur le réseau !")
            return True
        time.sleep(2)
    print("Erreur : module non enregistré sur le réseau.")
    return False

def is_pdp_active(resp):
    # Nettoyage des espaces pour le parsing stable
    resp_clean = resp.replace(" ", "")
    if '+CNACT:1,1' in resp_clean and '0.0.0.0' not in resp_clean:
        return True
    return False

def wait_for_pdp_activation(timeout=120):
    print("Attente de l'activation DATA/PDP réelle...")
    start = time.time()
    while time.time() - start < timeout:
        resp = send_at('AT+CNACT=1,1', 4, ignore_error_cmds=['AT+CNACT=1,1'])
        resp2 = send_at('AT+CNACT?', 2)
        if is_pdp_active(resp2):
            print("Contexte PDP DATA actif !")
            return True
        print("PDP pas encore prêt, nouvelle tentative dans 5s...")
        time.sleep(5)
    print("Impossible d'activer le contexte PDP après attente.")
    return False

def test_http(url, get_path):
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])
    send_at(f'AT+SHCONF="URL","{url}"', 1)
    send_at('AT+SHCONF="BODYLEN",1024', 1)
    send_at('AT+SHCONF="HEADERLEN",350', 1)

    resp = send_at('AT+SHCONN', 6) # Augmentation légère du délai de connexion
    if 'OK' not in resp:
        print(f"Erreur : impossible d'ouvrir la connexion HTTP vers {url}.")
        return False

    send_at(f'AT+SHREQ="{get_path}",1', 6)
    resp = send_at('AT+SHREAD=0,100', 2, ignore_error_cmds=['AT+SHREAD=0,100'])
    
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])
    return True

def send_thingspeak(api_key, value1, value2):
    # On vérifie l'état du réseau avant d'émettre
    resp = send_at('AT+CEREG?', 2)
    resp_clean = resp.replace(" ", "")
    if not ("+CEREG:0,1" in resp_clean or "+CEREG:0,5" in resp_clean or "+CEREG:2,1" in resp_clean or "+CEREG:2,5" in resp_clean):
        print("Réseau perdu avant HTTP, tentative de reconnexion...")
        if not wait_for_network():
            return False

    # On s'assure que les DNS sont configurés (Utile si perte de bail IP)
    send_at('AT+CDNSCFG="8.8.8.8","8.8.4.4"', 1)

    url = "http://api.thingspeak.com"
    get_path = f'/update?api_key={api_key}&field1={value1}&field2={value2}'
    print(f"\n--- Envoi vers ThingSpeak (F1:{value1}, F2:{value2}) ---")
    return test_http(url, get_path)

def init():
    print("\nInitialisation SIM7080...")

    if not send_at('AT', 1):
        print("Le module ne répond pas correctement.")
        return False

    send_at('ATE0', 0.5)
    
    reponse = send_at('AT+CPIN?')
    if not (reponse and "+CPIN: READY" in reponse):
        print("Problème carte SIM...")
        return False

    send_at('AT+CSQ', 1)
    
    reponse = send_at('AT+CFUN=1', 2)
    if not (reponse and "OK" in reponse):
        print("Problème activation du modem...")
        return False

    send_at('AT+CNMP=38', 2) # LTE Only
    send_at('AT+CMNB=1', 2)  # NB-IoT Only
    send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)
    send_at('AT+COPS=0', 2)
    send_at('AT+CEREG=2', 2) # Mode 2 requis pour capter le LAC/CellID automatiquement

    print("\nInitialisation terminée avec succès !")
    return True # CORRIGÉ : Renvoie un vrai Booléen

# ==============================================================================
# DÉMARRAGE AVEC RESET AUTOMATIQUE
# ==============================================================================
while not init():
    tentatives_init += 1
    print(f"\n[INIT] Échec tentative {tentatives_init}/{MAX_ECHECS_INIT}")

    if tentatives_init >= MAX_ECHECS_INIT:
        print("[INIT] Trop d'échecs d'initialisation → reset total.")
        hard_reset()
    else:
        soft_reset_modem()

print("Modem initialisé avec succès.")
tentatives_init = 0 

if not wait_for_network():
    print("[RÉSEAU] Réseau indisponible → reset total.")
    hard_reset()

print("Attente de stabilisation du réseau (8 secondes)...")
time.sleep(8)

if not wait_for_pdp_activation():
    print("[PDP] Impossible d'activer la DATA → reset total.")
    hard_reset()

# ==============================================================================
# PARAMÈTRES DE SESSION & BOUCLE PRINCIPALE
# ==============================================================================
api_key = "BET2MXURJRI3AVQD"  
temps = 15                       
compteur_succes = 0              

print(f"\nLancement du monitoring (Intervalle : {temps}s)")

while True:
    val1 = random.randint(1, 49)    
    val2 = random.randint(50, 100)  

    print(f"\n--- Cycle d'envoi ---")
    MAX_ATTEMPTS = 5
    envoi_reussi_ce_cycle = False

    for attempt in range(MAX_ATTEMPTS):
        print(f"Tentative {attempt+1}/{MAX_ATTEMPTS}...")
        if send_thingspeak(api_key, val1, val2):
            compteur_succes += 1
            echecs_consecutifs = 0
            print(f"SUCCÈS ! Données transmises. Total réussis : {compteur_succes}")
            envoi_reussi_ce_cycle = True
            break
        else:
            print("Échec technique, nouvelle tentative dans 10s...")
            time.sleep(10)

    if not envoi_reussi_ce_cycle:
        echecs_consecutifs += 1
        print(f"ALERTE : Échec après {MAX_ATTEMPTS} tentatives.")
        print(f"Échecs consécutifs : {echecs_consecutifs}/{MAX_ECHECS_CONSECUTIFS}")

        if echecs_consecutifs >= MAX_ECHECS_CONSECUTIFS:
            print(f"\n[WATCHDOG] {MAX_ECHECS_CONSECUTIFS} échecs consécutifs. Tentative Soft Reset Modem...")
            soft_reset_modem()

            if init() and wait_for_network() and wait_for_pdp_activation():
                print("[WATCHDOG] Récupération réussie après soft reset.")
                echecs_consecutifs = 0
            else:
                print("[WATCHDOG] Soft reset insuffisant → Reset matériel du microcontrôleur.")
                hard_reset()

    # Récupération des métadonnées de l'antenne relais active
    get_network_time_and_cell()

    print(f"Pause de {temps} secondes...")
    time.sleep(temps)
