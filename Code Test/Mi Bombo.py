from machine import UART, Pin
import time

# --- CONFIGURATION MATÉRIELLE ---
# UART(2) pour ESP32 : TX=GPIO17, RX=GPIO16
uart = UART(2, 57600, tx=17, rx=16)
uart.init(57600, bits=8, parity=None, stop=1)

# --- VOS PARAMÈTRES THINGSPEAK ---
CHANNEL_ID = "3297574"
READ_API_KEY = "4JTRK09UH8OOZZK8" # À remplacer par votre Read API Key
FIELD_NUMBER = 1

# --- FONCTIONS DE COMMUNICATION ---

def send_at(command, delay=1, ignore_error=False):
    """Envoie une commande et retourne la réponse décodée."""
    print(f"Envoi: {command}")
    uart.write(command + '\r\n')
    time.sleep(delay)
    response = b''
    while uart.any():
        response += uart.read()
    
    try:
        decoded = response.decode('utf-8')
    except:
        decoded = str(response)
    
    if not ignore_error:
        print(f"Réponse: {decoded.strip()}")
    return decoded

def setup_connection():
    print("\n--- Diagnostic Réseau ---")
    send_at('AT+CPIN?', 1)       # Vérifie si la SIM est détectée et déverrouillée
    send_at('AT+CSQ', 1)         # Vérifie la force du signal (doit être > 10)
    send_at('AT+CNMP=38', 1)     # LTE Only
    send_at('AT+CMNB=1', 1)      # CAT-M
    send_at('AT+CGDCONT=1,"IP","iot.1nce.net"', 1)
    
    print("\nAttente enregistrement...")
    for i in range(40):
        resp = send_at('AT+CEREG?', 2)
        # Analyse de la réponse :
        # 0,1 = Enregistré local | 0,5 = Enregistré en Roaming (souvent le cas avec 1nce)
        if "+CEREG: 0,1" in resp or "+CEREG: 0,5" in resp or "+CEREG: 2,5" in resp:
            print("Connecté à l'antenne !")
            break
        else:
            print(f"Tentative {i}... Toujours pas de signal.")
        time.sleep(1)
    else:
        return False

    print("\nActivation DATA...")
    send_at('AT+CNACT=1,1', 5)
    return "+CNACT: 1,1" in send_at('AT+CNACT?', 2)
    
    # Vérification si l'IP est bien attribuée
    resp_pdp = send_at('AT+CNACT?', 2)
    if '+CNACT: 1,1' in resp_pdp and '0.0.0.0' not in resp_pdp:
        print("Connexion DATA active.")
        return True
    return False

def get_last_value_json():
    """Récupère la dernière valeur du champ via l'API JSON."""
    host = "api.thingspeak.com"
    # Utilisation du format .json pour répondre à votre demande
    path = f'/channels/{CHANNEL_ID}/fields/{FIELD_NUMBER}/last.json?api_key={READ_API_KEY}'
    
    # Reset HTTP
    send_at('AT+SHDISC', 0.5)
    
    # Configuration session HTTP
    send_at(f'AT+SHCONF="URL","http://{host}"', 1)
    send_at('AT+SHCONF="BODYLEN",1024', 0.5)
    send_at('AT+SHCONF="HEADERLEN",350', 0.5)
    
    if 'OK' not in send_at('AT+SHCONN', 5):
        print("Erreur: Connexion au serveur HTTP impossible.")
        return None

    # Requête GET
    send_at(f'AT+SHREQ="{path}",1', 5)
    
    # Lecture du résultat (256 octets suffisent pour le JSON 'last')
    raw_data = send_at('AT+SHREAD=0,256', 2)
    
    # Extraction manuelle du champ JSON sans bibliothèque externe
    # Exemple de format : {"created_at":"...","entry_id":12,"field1":"22.5"}
    search_key = f'"field{FIELD_NUMBER}":"'
    
    if search_key in raw_data:
        try:
            # On découpe après la clé et on prend ce qu'il y a avant le guillemet fermant
            valeur = raw_data.split(search_key)[1].split('"')[0]
            return valeur
        except:
            return "Erreur de découpage"
    else:
        return "Champ vide ou introuvable"

# --- BOUCLE PRINCIPALE ---

print("=== PROGRAMME DE LECTURE SEULE THINGSPEAK ===")

if setup_connection():
    while True:
        try:
            val = get_last_value_json()
            if val:
                print(f"\n[RÉSULTAT] Dernière valeur enregistrée : {val}")
            
            print("-" * 30)
            print("Prochaine lecture dans 15 secondes...")
            time.sleep(15)
            
        except KeyboardInterrupt:
            print("\nArrêt du programme.")
            break
else:
    print("Initialisation échouée. Vérifiez votre antenne ou votre couverture réseau.")