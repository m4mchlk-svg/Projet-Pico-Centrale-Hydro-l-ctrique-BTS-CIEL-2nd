import network
import urequests
import time

#wifi 
ssid="Nothing Matheis"
key="math_mchlk"

#thingspeak
write_api_key = "LUD0LQLX2449HEXT"
url_update = "http://api.thingspeak.com/update?"

# 1. Connexion WiFi
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


# 2. Envoi des données
def send_data(value):
    
    url_write = "api_key={}&field1={}".format(write_api_key, value)
    url = url_update + url_write
    
    try:
        response = urequests.get(url)
        print("Réponse :", response.text)
        response.close() # TRÈS IMPORTANT sur ESP32 pour éviter de saturer la mémoire
    except Exception as e:
        print("Erreur d'envoi :", e)

# Utilisation
wifi_connect()
send_data(11)
