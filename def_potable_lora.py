from machine import UART, Pin
import time

# Définition des broches selon votre montage
M0 = Pin(19, Pin.OUT)
M1 = Pin(18, Pin.OUT)

# 1. Passage en Mode Sommeil (Mode 3) pour la configuration
M0.value(1)
M1.value(1)
time.sleep(0.1) # Temps de stabilisation

# Initialisation de l'UART2 sur l'ESP32
# Vitesse par défaut du module : 9600 bps [cite: 81]
uart = UART(2, baudrate=9600, tx=17, rx=16)

def configure_fixed_transmission():
    # Commande de configuration (6 octets)
    # C0 : Enregistrement permanent [cite: 81]
    # 00 01 : Adresse haute et basse (ADDH/ADDL)
    # 1A : Vitesse (8N1, 9600bps, Air Rate 2.4k) [cite: 85, 86]
    # 06 : Canal (868MHz par défaut) 
    # C4 : Registre OPTION
    #      Bit 7 = 1 -> Active la TRANSMISSION FIXE 
    #      Bit 2 = 1 -> FEC ON (Correction d'erreur) [cite: 92]
    
    config_cmd = bytes([0xC0, 0x00, 0x01, 0x1A, 0x06, 0xC4])
    
    print("Envoi de la commande de configuration...")
    uart.write(config_cmd)
    
    # Attente de la réponse de confirmation
    time.sleep(0.5)
    if uart.any():
        response = uart.read()
        print("Réponse du module (HEX) :", response.hex())
    else:
        print("Aucune réponse. Vérifiez les branchements.")

# Exécuter la configuration
configure_fixed_transmission()

# 2. Retour au Mode Normal (Mode 0) pour communiquer
M0.value(0)
M1.value(0)
print("Mode Normal activé. Prêt à émettre/recevoir.")

def send_fixed_message(addh, addl, chan, text):
    # Format : [ADDH] [ADDL] [CHAN] + Données [cite: 40]
    header = bytes([addh, addl, chan])
    payload = header + text.encode('utf-8')
    uart.write(payload)

# Exemple d'utilisation vers le module 0x0005 sur le canal 0x04
send_fixed_message(0x00, 0x05, 0x04, "Hello World")

def set_mode(mode):
    """
    Change le mode du module LoRa (0 à 3)
    """
    if mode == 0:     # Mode Normal
        m1.value(0)
        m0.value(0)
    elif mode == 1:   # Mode Wake-up
        m1.value(0)
        m0.value(1)
    elif mode == 2:   # Mode Power-saving
        m1.value(1)
        m0.value(0)
    elif mode == 3:   # Mode Sleep / Config
        m1.value(1)
        m0.value(1)
    
    # Le manuel recommande d'attendre un court instant que le mode soit effectif
    # La commutation est complète dans la milliseconde après que AUX passe à 1 [cite: 61]
    time.sleep_ms(10) 

# Utilisation simple :
set_mode(3) # Passage en mode config
# ... envoyer vos commandes de config ...
set_mode(0) # Retour en mode normal pour communiquer

def safe_set_mode(mode_target):
    # Attendre que le module ne soit plus occupé (AUX doit être à 1) [cite: 60, 63]
    while aux.value() == 0:
        time.sleep_ms(1)
        
    # Appliquer les niveaux sur M0 et M1
    m1.value(1 if mode_target in [2, 3] else 0)
    m0.value(1 if mode_target in [1, 3] else 0)
    
    # Attendre la fin du basculement (environ 2ms selon le manuel [cite: 62])
    time.sleep_ms(5)
    
    print(f"Mode {mode_target} actif.")