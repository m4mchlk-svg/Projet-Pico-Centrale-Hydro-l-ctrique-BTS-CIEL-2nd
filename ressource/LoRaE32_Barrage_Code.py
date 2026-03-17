# ******************************************************************
#   PROJET BTS CIEL 2026 - Pico-centrale hydroélectrique
#   Module LoRa E32-900T30D  sur ESP32 VROOM 32U  
#   By OH  - Mars / 2026   -    Version 1.0
#   --- Programme côté barrage ---
# ******************************************************************

# Ce programme génère aléatoirement des trames à émettre vers le module LoRa côté
# pupitre. Les trames émises ont le format :  $ val1 # val2 # texte1 # crc16
# Le caractère de début de trame "$" et le rajout du CRC16 permettent de détecter
# les erreurs de transmission. les caractères "#" sont des séparateurs de données.
# Le nombre de trames émises est affiché pour les statistiques de fiabilité ou de
# portée.

from machine import UART, Pin
from LoRaE32_Barrage_Lib import *  # A télécharger dans l’ESP32 :  class LoRaE32 
import time, random

# Cablage de l'ESP32 sur le module Lora
UART2 = 2  # deuxième port UART de l'ESP32
RX    = 16
TX    = 17
AUX   = 22
M0    = 19
M1    = 18

# Configuration des modules LoRa - Envoi simple de données en point à point
# Adresse du module Lora sur le barrage 
addr_high_barrage = 0x00
addr_low_barrage  = 0x00
# Adresse du module Lora sur le pupitre de commande 
addr_high_pupitre = 0x00
addr_low_pupitre  = 0x01
# Canal de communication
CANAL = 0x06               # fréquence 868 MHz (canal 6)
DEBIT = 9600               # Débit communication série
CONF  = 0xC0               # mode fixe à 30 dBm 

#Instanciation de la liaison serie LORA-ESP32
uart = UART(UART2, baudrate=DEBIT, tx=TX, rx=RX)

#Instanciation du module Lora
lora_barrage = LoRaE32('900T30D', uart, AUX, M0, M1)
lora_barrage.begin()

# Configuration puissance max, choix du canal et adresse du module...
lora_barrage.config['CHANNEL'] = CANAL              # fréquence 868 MHz (canal 6)
lora_barrage.config['ADDR_H']  = addr_high_barrage
lora_barrage.config['ADDR_L']  = addr_low_barrage
lora_barrage.config['OPTION']  = CONF               # mode fixe à 30 dBm
lora_barrage.set_config(save=True)

# ****************   SOUS PROGRAMMES **************************************
def print_config(config):  # Afficher la configuration du module LoRa
    print("=== CONFIGURATION du module LoRa ===")
    for key in ['HEAD', 'ADDR_H', 'ADDR_L', 'SPED','CHANNEL','OPTION']:
        print(f"{key}: {config[key]}")
    print("\n")
    
def crc16(texte): # Contrôle de redondance cyclique : détecter erreurs de transmission
    crc = 0xFFFF
    for char in texte:
        crc ^= ord(char)
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    print(f"\t * crc16: {crc:04X}")           
    return f"{crc:04X}"

def get_trame():   # Création d'une trame sous la forme: $ val1 # val2 # texte #  
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    val1 = random.randint(100, 1000)
    val2 = random.randint(100, 1000)
    texte =  ''.join(random.choice(alphabet) for _ in range(4))
    print(f"\t * val1: {val1}")
    print(f"\t * val2: {val2}")
    print(f"\t * texte1: {texte}")
    return "$"+str(val1) + "#" + str(val2) + "#" + texte + "#" 

# ****************   PROGRAMME PRINCIPAL *******************************

# Vérification de la configuration du module : attention pour changer de configuration
# il faut rebooter le module !

print("\nTest de configuration du module LORA du barrage :\n")
config = lora_barrage.get_configuration()
if config:
    print_config(config)
else:
    print(" --> Erreur ou timeout")  # PB liaison série ou autre...

# Communication en boucle pour l'emission de trame formatée : $val1 #val2 #texte #crc16
print("Emission activée...")
compteur_trame = 1

while True:
    print(f"\nNombre de trames envoyées : {compteur_trame}")
    trame_emision = get_trame()        # Sous la forme: "  $ val1 # val2 # texte #  "
    crc = crc16(trame_emision)         # calcul du crc16 de la trame à émettre
    message = trame_emision + crc      # Sous la forme: "  $ val1 # val2 # texte # crc16  "
    lora_barrage.send_data(addr_high_pupitre, addr_low_pupitre, CANAL, message.encode('utf-8'))  
    print("Envoyer la trame :", message.encode('utf-8'))
    compteur_trame += 1   # On compte les trames envoyées
    time.sleep(2)         # On envoie une trame toutes les 5 secondes...
