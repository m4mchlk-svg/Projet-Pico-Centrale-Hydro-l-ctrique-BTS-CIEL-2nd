# ******************************************************************
#   PROJET BTS CIEL 2026 - Pico-centrale hydroélectrique
#   Module LoRa E32-900T30D  sur ESP32 VROOM 32U  
#   By OH  - Mars / 2026   -    Version 1.0
#   --- Programme côté pupitre de commande ---
# ******************************************************************

# Ce programme reçoit sous interruption des trames du module côté barrage.
# Les trames reçues ont le format :  $ val1 # val2 # texte1 # crc16
# Le caractère de début de trame "$" et le CRC16 permettent de détecter
# les erreurs de transmission. Les trames valident sont analysées.
# Un calcul de taux d'erreurs permettra de faire des tests de portée et de
# fiabilité eventuellement en physique appliquée...  à suivre !

from machine import UART, Pin
from LoRaE32_Pupitre_Lib import *   # Fichier à télécharger dans l’ESP32 :  class LoRaE32 
import time

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

reception_flag = False   # interruption RX valide si données séries reçues

#Instanciation de la liaison serie LORA-ESP32 avec interruption
uart = UART(UART2, baudrate=DEBIT, tx=TX, rx=RX)
#Instanciation du module Lora
lora_pupitre = LoRaE32('900T30D', uart, AUX, M0, M1)
lora_pupitre.begin()

# Configuration du module Lora
lora_pupitre.config['CHANNEL'] = CANAL              # fréquence 868 MHz (canal 6)
lora_pupitre.config['ADDR_H']  = addr_high_pupitre  # adresse pupitre MSB
lora_pupitre.config['ADDR_L']  = addr_low_pupitre   # adresse pupitre LSB
lora_pupitre.config['OPTION']  = CONF               # mode fixe à 30 dBm
lora_pupitre.set_config(save=True)

# ******************   SOUS PROGRAMMES INTERRUPTION ****************
def uart_handler(uart):    
    global reception_flag  # Pas de traitement long ici !
    reception_flag = True  # Présence données reçues sur RX !

# ******************   SOUS PROGRAMMES *****************************
def print_config(config):   # Afficher la configuration du module LoRa
    print("=== CONFIGURATION du module LoRa ===")
    for key in ['HEAD', 'ADDR_H', 'ADDR_L', 'SPED','CHANNEL','OPTION']:
        print(f"{key}: {config[key]}")
    print("\n")

def crc16(texte):  # Contrôle de redondance cyclique : détecter erreurs de transmission
    crc = 0xFFFF
    for char in texte:
        crc ^= ord(char)
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return f"{crc:04X}"

def crc_valide(texte): # calcul le crc16 de la trame reçue et le compare à celui transmis
    crc_recu = texte[-4:]
    #print("crc16 reçu = ",crc_recu)
    crc_calc = crc16(str(texte[0:-4]))
    print("  --> crc16 calculé = ",crc_calc, end='')
    if crc_recu == crc_calc : # si les deux sont identiques : pas d'erreur de transmission
        print(" * trame valide !") # et on valide la trame reçue !
        return True
    return False

def parse_message(texte): # Analyse de la trame reçue et validée
    parties = texte[1:].split('#')  # Enlever $ puis split ( découpage )
    if len(parties) == 4:           # On retourne alors un dictionaire contenant :
        return { 'val1'  : int(parties[0]),  #  val1   : un nombre entier 
                 'val2'  : int(parties[1]),  #  val2   : un nombre entier   
                 'texte1': parties[2],       #  texte1 : une chaine de caractères    
                 'crc16' : parties[3] }      #  Le crc16 : string 4 caractères
    return None    

# ****************   PROGRAMME PRINCIPAL *******************************

# Vérification de la configuration du module : attention pour changer de configuration
# il faut rebooter le module !

print("\nTest de configuration du module LORA du pupitre de commande :\n")
config = lora_pupitre.get_configuration()
if config:
    print_config(config)
else:
    print(" --> Erreur ou timeout")  # PB liaison série ou autre...

# **** Communication en boucle ****
# Trame reçue de la forme: $ val1 # val2 # texte1 # crc16

uart.irq(handler=uart_handler, trigger=UART.IRQ_RXIDLE)  # Active IRQ sur RX
print("Réception activée, attente...")

compteur_trames_valides,compteur_trames_invalides = 0, 0
while True:              # En dehors de l'interruption le programme ne fait rien !
    if reception_flag :  # traitement de la communication sous interuption à traiter.
        msg = lora_pupitre.get_data() # Lecture du recepteur LoRa 
        if msg:
            trame_reception = msg.decode('utf-8').strip()
            print(f"\nMessage brut reçu : {trame_reception}") # affichage trame brute
            if trame_reception.startswith('$') and crc_valide(trame_reception):
                resultat = parse_message(trame_reception)     # trame valide à analyser
                for key in ['val1', 'val2', 'texte1', 'crc16']:
                    print(f"\t * {key}: {resultat[key]}")  # On affiche les données reçues
                compteur_trames_valides += 1
            else :
                print("\t * trame non valide !")   # trame non valide à rejeter
                compteur_trames_invalides += 1
            print(f"\nNombre de trames valides reçues : {compteur_trames_valides}")
            print(f"Nombre de trames non valides reçues : {compteur_trames_invalides}")    
        reception_flag = False   # prochaines données en attente par flag interruption
