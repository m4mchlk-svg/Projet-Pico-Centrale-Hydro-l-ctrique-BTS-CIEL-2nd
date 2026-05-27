
import network
import urequests
import time

#wifi 
ssid="Nothing Matheis"
key="math_mchlk"

#thingspeak
write_api_key = "LUD0LQLX2449HEXT"
read_api_key =  "ERFC6HFDNV8NFFES"
read_channel = 3271210
n_res = 12
url_update = "http://api.thingspeak.com/update?"
url_read =   "https://api.thingspeak.com/channels/{read_channel}/fields/1.json?results={n_res}"

def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('Connexion au WiFi...')
        wlan.connect(ssid, key)
        while not wlan.isconnected():
            pass
    if wlan.isconnected():
        print('WiFi Connecté ! IP:', wlan.ifconfig()[0])

def read_nres_data():
    # On utilise results=20 dans l'URL
    url = "http://api.thingspeak.com/channels/{}/fields/1.json?api_key={}&results={}".format(read_channel, read_api_key, n_res)
    
    try:
        print("Récupération des {} dernières données...".format(n_res))
        response = urequests.get(url)
        data = response.json()
        
        liste_donnees = data['feeds']
        indice=0
        print("--- Historique du Field 1 ---")
        for entree in liste_donnees:
            valeur = entree['field1']
            indice+=1
            
            # Note : On vérifie si la valeur n'est pas None (vide)
            if valeur is not None:
                print("Valeur: {} | Numero: {}".format(valeur, indice))
            else:
                print("Donnée vide à cette position.")
        
        response.close()
        return liste_donnees # Retourne la liste complète si besoin de calculs
        
    except Exception as e:
        print("Erreur de lecture :", e)
        return None

# Utilisation
wifi_connect()
read_nres_data()

