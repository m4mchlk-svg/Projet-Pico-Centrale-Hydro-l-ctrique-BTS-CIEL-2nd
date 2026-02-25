from machine import UART, Pin
import time

# --- CONFIGURATION MATÉRIELLE ---
# UART2 : TX=GPIO 17 (vers RX LoRa), RX=GPIO 16 (vers TX LoRa)
uart = UART(2, baudrate=9600, tx=17, rx=16, timeout=200)
m0 = Pin(19, Pin.OUT)
m1 = Pin(18, Pin.OUT)
aux = Pin(22, Pin.IN)

# --- FONCTIONS DE BASE (GESTION AUX ET MODES) ---

debug = True 

def wait_aux():
    """ Attend que le module soit prêt (AUX=1) selon la datasheet section 5.6 """
    while aux.value() == 0:
        time.sleep_ms(1)
    time.sleep_ms(2) # Petite marge de sécurité après la remontée du signal

def set_mode(mode):
    """ Change le mode du module (0 à 3) proprement """
    wait_aux()
    if mode == 0:     # NORMAL : Envoi/Réception
        m1.value(0); m0.value(0)
    elif mode == 1:   # WAKE-UP : Ajoute un préambule long
        m1.value(0); m0.value(1)
    elif mode == 2:   # POWER-SAVING : Réception intermittente
        m1.value(1); m0.value(0)
    elif mode == 3:   # SLEEP : Configuration / Lecture
        m1.value(1); m0.value(1)
    
    time.sleep_ms(20) # Temps de stabilisation du mode
    wait_aux()
    if debug :
        print(f"Mode {mode} active")

# --- FONCTIONS DE CONFIGURATION ---

def setup_fixed_transmission(addr_h, addr_l, channel):
    """ Configure le module en Transmission Fixe (Sauvegarde Permanente C0) """
    set_mode(3) # Mode config obligatoire
    
    # Trame : C0 (Permanent) + ADDR_H + ADDR_L + 1A (9600bps/2.4k) + CHAN + C4 (Fixe)
    config_cmd = bytes([0xC0, addr_h, addr_l, 0x1A, channel, 0xC4])
    
    print(f"Envoi configuration fixe : {config_cmd.hex().upper()}")
    uart.write(config_cmd)
    
    time.sleep_ms(200)
    if uart.any():
        response = uart.read()
        if debug : 
            print(f"Confirmation module : {response.hex().upper()}")
    
    set_mode(0) # Retour au mode normal

# --- LES 3 MODES DE COMMUNICATION ---

compteur=1
def send_point_to_point_v(target_h, target_l, target_chan, message):
    """ MODE 1 : Envoyer à un récepteur précis """
    wait_aux()
    header = bytes([target_h, target_l, target_chan])
    message_txt = str(message)
    uart.write(header + " " + message_txt)
    if debug: 
        print(f"Envoyé à {target_h:02x}{target_l:02x} sur canal {target_chan}")
    
def send_point_to_point_txt(target_h, target_l, target_chan, message):
    """ MODE 1 : Envoyer à un récepteur précis """
    wait_aux()
    header = bytes([target_h, target_l, target_chan])
    uart.write(header + message.encode('utf-8'))
    if debug: 
        print(f"Envoyé à {target_h:02x}{target_l:02x} sur canal {target_chan}")

def send_broadcast(target_chan, message):
    """ MODE 2 : Envoyer à TOUS les modules sur un canal précis (FFFF) """
    wait_aux()
    header = bytes([0xFF, 0xFF, target_chan])
    uart.write(header + message.encode('utf-8'))
    if debug: 
        print(f"Broadcast envoyé sur canal {target_chan}")

def receive_monitoring():
    """ MODE 3 : Ecouter les messages entrants """
    if uart.any():
        global data 
        data = uart.read()
        try:
            if debug: 
                print(f"Message reçu : {data.decode('utf-8')}")
        except:
            if debug: 
                print(f"Message reçu (HEX) : {data.hex()}")
        return data
    return None

# --- PROGRAMME PRINCIPAL (EXEMPLE) ---

# 1. On configure notre module : Adresse 0x0001, Canal 23 (891 MHz)
setup_fixed_transmission(0x00, 0x01, 23)

# 2. On vérifie la config par curiosité

print("\nSysteme pret. En attente ou pret a envoyer...")

while True:
    # --- TEST ENVOI ---
    # Pour envoyer un message toutes les 10 secondes au module n°2 (0x0002) :
    #send_point_to_point_txt(0x00, 0x02, 23, "Salut module 2")
    wait_aux()
    send_point_to_point_v(0x00, 0x02, 23, compteur)
    print(compteur)
    compteur +=1
    wait_aux()
    # --- RÉCEPTION ---
    #receive_monitoring()
    
    time.sleep(10)

