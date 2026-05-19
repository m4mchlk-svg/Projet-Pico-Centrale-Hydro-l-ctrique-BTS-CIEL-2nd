from machine import UART, Pin, Timer
from LoRaE32_Pupitre_Lib import *   # Fichier à télécharger dans l’ESP32 :  class LoRaE32 
import time, random

class Color:
    R = '\033[31m'  # Rouge
    G = '\033[32m'  # Vert
    B = '\033[34m'  # Bleu
    Y = '\033[33m'  # Jaune
    END = '\033[0m' # Reset

# Cablage de l'ESP32 sur le module Lora
UART2 = 2  # deuxième port UART de l'ESP32
RX    = 17
TX    = 16
AUX   = 22
M0    = 21
M1    = 19

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

reception_flag = False     # interruption RX valide si données séries reçues 

#Instanciation de la liaison serie LORA-ESP32 avec interruption
uart = UART(UART2, baudrate=DEBIT, tx=TX, rx=RX)
#Instanciation du module Lora
lora_pupitre = LoRaE32('900T30D', uart, AUX, M0, M1)
lora_pupitre.begin()
# Instanciation du timer 1
timer_send_data   = Timer(1)

# Configuration du module Lora
lora_pupitre.config['CHANNEL'] = CANAL              # fréquence 868 MHz (canal 6)
lora_pupitre.config['ADDR_H']  = addr_high_pupitre  # adresse pupitre MSB
lora_pupitre.config['ADDR_L']  = addr_low_pupitre   # adresse pupitre LSB
lora_pupitre.config['OPTION']  = CONF               # mode fixe à 30 dBm
lora_pupitre.set_config(save=True)

# ******************   SOUS PROGRAMMES INTERRUPTION ****************
# interruption matérielle uart 2 :
def uart_handler(uart):    
    global reception_flag  # Pas de traitement long ici !
    reception_flag = True  # Présence données reçues sur RX !

# ******************   SOUS PROGRAMMES *****************************
def print_config(config):   # Afficher la configuration du module LoRa
    print("=== CONFIGURATION du module LoRa ===")
    for key in ['HEAD', 'ADDR_H', 'ADDR_L', 'SPED','CHANNEL','OPTION']:
        print(f"{key}: {config[key]}")
    print("\n")

# ****************   PROGRAMME PRINCIPAL *******************************

# Vérification de la configuration du module : attention pour changer de configuration
# il faut rebooter le module !

print("\nTest de configuration du module LORA du pupitre de commande :\n")
config = lora_pupitre.get_configuration()
if config:
    print_config(config)
else:
    print(" --> Erreur ou timeout")  # PB liaison série ou autre...

# **** Activation des interruption ****
uart.irq(handler=uart_handler, trigger=UART.IRQ_RXIDLE)  # Active IRQ sur RX

print("Réception activée, attente...")

# **** Communication en boucle ****
# Trame reçue de la forme: $ val1 # val2 # texte1 # crc16
# Trame émise de la forme: $ val3 # val4 # texte2 # crc16

compteur_trames_valides,compteur_trames_invalides = 0, 0
compteur_trames_emises = 0

while True:
    if reception_flag :
        print(Color.Y)
        trame = lecture_trame()
        if isinstance(trame, dict):
            for key in ['val1', 'val2', 'texte1', 'crc16']:
                print(f"\t * {key}: {trame[key]}")  # On affiche les données reçues
            compteur_trames_valides += 1
            print(f"Nombre de trames valides reçues du barrage : {compteur_trames_valides}")
            print(f"Nombre de trames non valides reçues du barrage : {compteur_trames_invalides}") 
        elif trame == "erreur":
            print("\t * trame non valide !")   # trame non valide à rejeter
            compteur_trames_invalides += 1
            print(f"Nombre de trames valides reçues du barrage : {compteur_trames_valides}")
            print(f"Nombre de trames non valides reçues du barrage : {compteur_trames_invalides}") 
        reception_flag = False   # prochaines données en attente par flag interruption 

        print(Color.G)
        envoyer_trame()
        compteur_trames_emises += 1   # On compte les trames envoyées
        print(f"Nombre de trames envoyées par le module pupitre : {compteur_trames_emises}")
        emission_flag = False   # Attente timer pour prochaines données à envoyer