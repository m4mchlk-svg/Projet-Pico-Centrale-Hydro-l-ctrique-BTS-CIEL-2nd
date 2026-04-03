from machine import UART, Pin
import time
import random

# --- Configuration UART ---
uart = UART(2, 57600, tx=17, rx=16)
uart.init(57600, bits=8, parity=None, stop=1)

# --- Fonctions utilitaires ---
def send_at(command, delay=1, flush=True, ignore_error_cmds=None):
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
    send_at('AT+CTZU=1', 1)
    resp_time = send_at('AT+CCLK?', 1)
    date_heure = "Indisponible"
    for line in resp_time.split('\n'):
        if '+CCLK:' in line:
            date_heure = line.strip().replace('+CCLK: ', '').replace('"','')
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

# --- MODIFICATION ICI : Ajout de value2 ---
def send_thingspeak(api_key, value1, value2):
    send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)
    send_at('AT+CNACT=1,1', 5, ignore_error_cmds=['AT+CNACT=1,1'])
    if not wait_for_pdp():
        return False
    time.sleep(2)
    send_at('AT+CDNSCFG="8.8.8.8","8.8.4.4"', 1)
    time.sleep(1)
    send_at('AT+SHDISC', 1, ignore_error_cmds=['AT+SHDISC'])
    resp = send_at('AT+CEREG?', 2)
    if not ("+CEREG: 0,1" in resp or "+CEREG: 0,5" in resp or "+CEREG: 2,5" in resp):
        print("Réseau perdu avant HTTP, attente du retour du réseau...")
        if not wait_for_network():
            return False
    
    url = "http://api.thingspeak.com"
    # L'URL contient maintenant les deux champs
    get_path = f'/update?api_key={api_key}&field1={value1}&field2={value2}'
    print(f"\n--- Envoi vers ThingSpeak (F1:{value1}, F2:{value2}) ---")
    ok = test_http(url, get_path)
    return ok

# --- Programme principal ---
print("Initialisation SIM7080...")

send_at('AT', 1)
send_at('AT+CPIN?', 1)
send_at('AT+CSQ', 1)
send_at('AT+CFUN=1', 2)
send_at('AT+CNMP=38', 2)
send_at('AT+CMNB=1', 2)
send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)
send_at('AT+COPS=0', 2)
send_at('AT+CEREG=2', 2)

if not wait_for_network():
    print("Erreur réseau, arrêt du programme.")
    raise SystemExit

print("Attente de stabilisation du réseau (8 secondes)...")
time.sleep(8)

if not wait_for_pdp_activation():
    print("Impossible d'activer la DATA, arrêt du programme.")
    raise SystemExit

api_key = "BET2MXURJRI3AVQD"
temps = 30  
compteur_succes = 0 

print(f"\nLancement du monitoring (Intervalle : {temps}s)")

while True:
    # --- MODIFICATION ICI : Deux valeurs aléatoires ---
    val1 = random.randint(1, 30)
    val2 = random.randint(50, 100) 
    
    print(f"\n--- Cycle d'envoi ---")
    MAX_ATTEMPTS = 5
    envoi_reussi_ce_cycle = False
    
    for attempt in range(MAX_ATTEMPTS):
        print(f"Tentative {attempt+1}/{MAX_ATTEMPTS}...")
        # Appel avec les deux valeurs
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

    get_network_time_and_cell()
    print(f"Pause de {temps} secondes...")
    time.sleep(temps)