"""
Script de Test de Communication Série UART pour ESP32 et Modem SIM7080G.

Ce script configure le canal UART 2 de l'ESP32 pour communiquer à 57600 bauds.
Il envoie une commande AT spécifique (AT+SHCONN) pour demander au modem de
se connecter à un serveur HTTP, attend une seconde pour la réponse, puis
lit, décode et affiche tout texte reçu du modem dans la console MicroPython.

Configuration Matérielle (par défaut) :
- Vitesse : 57600 bauds
- Broche TX ESP32 (Envoi) : GPIO 17
- Broche RX ESP32 (Réception) : GPIO 16
"""

import time
from machine import UART

# 1. Configuration de la liaison série
uart = UART(2, 57600, tx=17, rx=16)
uart.init(57600, bits=8, parity=None, stop=1)

# 2. Teste de commande AT (demande de connexion HTTP)
# \r\n sont les caractères invisibles "Entrée" obligatoires pour valider la commande
uart.write('AT+SHCONN\r\n') 

# 3. Pause d'une seconde pour laisser le modem traiter l'ordre et répondre
time.sleep(1)

# 4. Vérification et lecture de la réponse
if uart.any():
    # Lecture des données brutes (octets)
    result = uart.read()
    # Traduction des octets en texte lisible (UTF-8)
    answer = result.decode('utf-8')
    # Nettoyage des espaces/retours à la ligne inutiles
    answer = answer.strip()
    # Affichage du résultat final dans la console
    print(answer)
