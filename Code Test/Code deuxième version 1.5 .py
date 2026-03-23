from machine import UART, Pin
import time
import random

# --- Configuration UART ---
uart = UART(2, 57600, tx=17, rx=16)
uart.init(57600, bits=8, parity=None, stop=1)

# --- Fonctions utilitaires ---
def send_at(command, delay=1, flush=True, ignore_error_cmds=None):
    """
    Envoie une commande AT, attend la réponse, et affiche un message spécial si l'erreur est attendue.
    ignore_error_cmds : liste de commandes pour lesquelles ERROR n'est pas bloquant
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
    # Gestion des erreurs attendues
    if "ERROR" in decoded and command in ignore_error_cmds:
        print(f"Réponse: {decoded.strip()} (erreur attendue, sans conséquence)")
    else:
        print(f"Réponse: {decoded.strip()}")
    return decoded

def get_network_time_and_cell():
    # Active la mise à jour automatique de l'heure (optionnel, à faire une fois)
    send_at('AT+CTZU=1', 1)
    # Récupère la date et l'heure
    resp_time = send_at('AT+CCLK?', 1)
    date_heure = "Indisponible"
    for line in resp_time.split('\n'):
        if '+CCLK:' in line:
            date_heure = line.strip().replace('+CCLK: ', '').replace('"','')
    # Récupère la localisation de l'antenne (Cell ID et LAC)
    resp_cell = send_at('AT+CEREG?', 1)
    lac = cellid = "Indisponible"
    for line in resp_cell.split('\n'):
        if '+CEREG:' in line:
            champs = line.strip().split(',')
            if len(champs) >= 5:
                lac = champs[2].replace('"','')
                cellid = champs[3].replace('"','')
    print(f"Date/heure du réseau GSM : {date_heure}")
    print(f"LAC (zone): {lac} | Cell ID (antenne): {cellid}")
    return date_heure, lac, cellid


def wait_for_network(timeout=120):
    print("Attente de l'enregistrement réseau...")
    start = time.time()
    while time.time() - start < timeout:
        resp = send_at('AT+CEREG?', 2)
        if ("+CEREG: 0,1" in resp or "+CEREG: 0,5" in resp or "+CEREG: 2,5" in resp):
            print("Module enregistré sur le réseau !")
            return True
        time.sleep(2)
    print("Erreur : module non enregistré sur le réseau.")
    return False

def is_pdp_active(resp):
    lines = resp.split('\n')
    for line in lines:
        if '+CNACT: 1,1' in line and '0.0.0.0' not in line:
            return True
    return False

def wait_for_pdp_activation(apn="iot.1nce.net", timeout=120):
    print("Attente de l'activation DATA/PDP réelle...")
    start = time.time()
    while time.time() - start < timeout:
        resp = send_at('AT+CNACT=1,1', 5, ignore_error_cmds=['AT+CNACT=1,1'])
        if "OK" in resp or "+APP PDP: 1,ACTIVE" in resp:
            # On vérifie si le contexte est vraiment actif
            resp2 = send_at('AT+CNACT?', 2)
            if is_pdp_active(resp2):
                print("Contexte PDP DATA actif !")
                return True
        print("PDP pas encore prêt, nouvelle tentative dans 5s...")
        time.sleep(5)
    print("Impossible d'activer le contexte PDP après attente.")
    return False

def wait_for_pdp(timeout=30):
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
    # On tente de fermer proprement, mais on ignore l'erreur
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])
    send_at(f'AT+SHCONF="URL","{url}"', 1)
    send_at('AT+SHCONF="BODYLEN",1024', 1)
    send_at('AT+SHCONF="HEADERLEN",350', 1)
    resp = send_at('AT+SHCONN', 5)
    if 'OK' not in resp:
        print(f"Erreur : impossible d’ouvrir la connexion HTTP vers {url}.")
        return False
    send_at(f'AT+SHREQ="{get_path}",1', 5)
    resp = send_at('AT+SHREAD=0,100', 2, ignore_error_cmds=['AT+SHREAD=0,100'])
    if "ERROR" in resp:
        print("Aucune donnée à lire ou réponse vide (normal pour ThingSpeak).")
    else:
        print(f"Réponse serveur {url} :", resp)
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])
    return True

def send_thingspeak(api_key, value):
    # Config APN et PDP
    send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)
    send_at('AT+CNACT=1,1', 5, ignore_error_cmds=['AT+CNACT=1,1'])
    if not wait_for_pdp():
        return False
    time.sleep(2)
    send_at('AT+CDNSCFG="8.8.8.8","8.8.4.4"', 1)
    time.sleep(1)
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])
    # Vérifie réseau juste avant HTTP
    resp = send_at('AT+CEREG?', 2)
    if not ("+CEREG: 0,1" in resp or "+CEREG: 0,5" in resp or "+CEREG: 2,5" in resp):
        print("Réseau perdu avant HTTP, attente du retour du réseau...")
        if not wait_for_network():
            return False
    # Envoi HTTP vers ThingSpeak
    url = "http://api.thingspeak.com"
    get_path = f'/update?api_key={api_key}&field1={value}'
    print("\n--- Test HTTP sur ThingSpeak ---")
    ok = test_http(url, get_path)
    return ok

# --- Programme principal ---
print("Initialisation SIM7080...")

# Initialisation module
send_at('AT', 1)
send_at('AT+CPIN?', 1)
send_at('AT+CSQ', 1)
send_at('AT+CFUN=1', 2)
send_at('AT+CNMP=38', 2)
send_at('AT+CMNB=1', 2)
send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)
send_at('AT+COPS=0', 2)
send_at('AT+CEREG=2', 2)

# Attendre enregistrement réseau
if not wait_for_network():
    print("Erreur réseau, arrêt du programme.")
    raise SystemExit

print("Attente de stabilisation du réseau (8 secondes)...")
time.sleep(8)

# Attendre que la DATA/PDP soit vraiment prête
if not wait_for_pdp_activation():
    print("Impossible d'activer la DATA, arrêt du programme.")
    raise SystemExit

# --- Paramètres ThingSpeak ---
api_key = "BET2MXURJRI3AVQD"
temps = 30  # Temps d'attente en secondes entre chaque envoi
compteur_succes = 0 # Initialisation du compteur

print(f"\nLancement du monitoring (Intervalle : {temps}s)")

# --- Boucle Infinie d'Envoi ---
while True:
    value = random.randint(1, 30)
    print(f"\n--- Cycle d'envoi ---")
    print(f"Valeur à envoyer : {value}")
    
    # Logique de tentatives (5 essais par cycle)
    MAX_ATTEMPTS = 5
    envoi_reussi_ce_cycle = False
    
    for attempt in range(MAX_ATTEMPTS):
        print(f"Tentative {attempt+1}/{MAX_ATTEMPTS}...")
        ok = send_thingspeak(api_key, value)
        
        if ok:
            compteur_succes += 1 # On incrémente le compteur global
            print(f"SUCCÈS ! Donnée transmise.")
            print(f"Nombre total d'envois réussis depuis le démarrage : {compteur_succes}")
            envoi_reussi_ce_cycle = True
            break
        else:
            print("Échec technique, nouvelle tentative dans 10s...")
            time.sleep(10)
    
    if not envoi_reussi_ce_cycle:
        print(f"ALERTE : Le cycle a échoué après {MAX_ATTEMPTS} tentatives.")
        print(f"Score actuel : {compteur_succes} envois réussis au total.")

    # Petit check réseau avant de dormir
    get_network_time_and_cell()

    print(f"Pause de {temps} secondes...")
    time.sleep(temps)