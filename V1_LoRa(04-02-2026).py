from machine import UART, Pin
import time

# --- INITIALISATION DES OBJETS ---
# On définit les pins globalement pour qu'elles soient accessibles partout

# UART2 sur ESP32 : TX=GPIO 17, RX=GPIO 16
uart = UART(2, baudrate=9600, tx=17, rx=16)
m0 = Pin(19, Pin.OUT)
m1 = Pin(18, Pin.OUT)
aux = Pin(22, Pin.IN)
busy =False
def is_busy():
    if aux==0:
        busy=True
    else:
        busy=False

def set_mode(mode):
    """ Change le mode du module (0 à 3) en attendant que AUX soit prêt """
    # Le manuel (p.11) dit : attendre que AUX soit à 1 avant de changer de mode
    
        while aux.value() == 0:
        pass
    
    if mode == 0:     # NORMAL
        m1.value(0); m0.value(0)
    elif mode == 1:   # WAKE-UP
        m1.value(0); m0.value(1)
    elif mode == 2:   # POWER-SAVING
        m1.value(1); m0.value(0)
    elif mode == 3:   # SLEEP (CONFIG)
        m1.value(1); m0.value(1)
    
    print(f"Mode {mode} active")

def configure_fixed_transmission(addr_h, addr_l, channel):
    """ Configure le module en Fixed Transmission (Bit 7 de OPTION à 1) """
    # 1. Passer en mode sommeil pour la config
    set_mode(3)
    time.sleep(0.1)
    # Commande selon le manuel : 
    # C0 (Permanent), ADDR_H, ADDR_L, 
    # SPED (0x1A = 8N1, 9600bps, 2.4kbps)
    # CHAN (Fréquence), 
    # OPTION (0xC4 = Transmission fixe + 1W + FEC)
    config_cmd = bytes([0xC0, addr_h, addr_l, 0x1A, channel, 0xC4])
    print(f"Envoi config: {config_cmd.hex()}")
    while aux.value() == 0:
        pass
    uart.write(config_cmd)
    time.sleep_ms(500)
    while aux.value() == 0:
        if uart.any():
            response = uart.read()
            print(f"Réponse module: {response.hex()}")
    time.sleep_ms(500)
    # 2. Revenir en mode normal
    set_mode(0)

# --- EXECUTION ---

# 1. Configurer le module une bonne fois pour toutes
configure_fixed_transmission(addr_h=0x00, addr_l=0x02, channel=24)

# 2. Exemple d'envoi en mode fixe vers module 0x0001 canal 23
# def send_fixed(target_h, target_l, target_chan, message):
#     header = bytes([target_h, target_l, target_chan])
#     uart.write(header + message.encode())
#     print("Message envoyé: ", message )
# 
# # Test d'envoi
# send_fixed(0x00, 0x01, 23, "Hello!")
