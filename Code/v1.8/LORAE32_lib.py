from machine import UART, Pin
import time, random

class LORAE32:
    def __init__(self, uart_id, tx_pin, rx_pin, m0_pin, m1_pin, aux_pin):
        # Configuration matérielle
        self.uart = UART(uart_id, baudrate=9600, tx=tx_pin, rx=rx_pin, timeout=200)
        self.m0 = Pin(m0_pin, Pin.OUT)
        self.m1 = Pin(m1_pin, Pin.OUT)
        self.aux = Pin(aux_pin, Pin.IN)
        self.set_mode(0) # Mode normal par défaut

    def wait_aux(self):
        while self.aux.value() == 0:
            time.sleep_ms(1)
        time.sleep_ms(2)

    def set_mode(self, mode):
        self.wait_aux()
        if mode == 0:   # NORMAL
            self.m1.value(0); self.m0.value(0)
        elif mode == 1: # WAKE-UP
            self.m1.value(0); self.m0.value(1)
        elif mode == 2: # POWER-SAVING
            self.m1.value(1); self.m0.value(0)
        elif mode == 3: # SLEEP / CONFIG
            self.m1.value(1); self.m0.value(1)
        time.sleep_ms(20)
        self.wait_aux()

    def setup_config(self, addr_h, addr_l, channel):
        self.set_mode(3)
        config_cmd = bytes([0xC0, addr_h, addr_l, 0x1A, channel, 0xC4])
        self.uart.write(config_cmd)
        time.sleep_ms(200)
        if self.uart.any():
            data = self.uart.read()
            print(data)
        self.set_mode(0)
        print(f"Configuration fixe appliquée sur canal {channel}")
        
    def get_trame(self):   # Création d'une trame sous la forme: $ val1 # val2 # texte #  
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        val1 = random.randint(100, 1000)
        val2 = random.randint(100, 1000)
        texte =  ''.join(random.choice(alphabet) for _ in range(4))
        print(f"\t * val1: {val1}")
        print(f"\t * val2: {val2}")
        print(f"\t * texte1: {texte}")
        return "$"+str(val1) + "#" + str(val2) + "#" + texte + "#"

    def crc16(self, texte):
        crc = 0xFFFF
        for char in texte:
            crc ^= ord(char)
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return f"{crc:04X}"

    def crc_valide(self, texte):
        """ Calcule le CRC16 de la trame reçue et le compare à celui transmis """
        # On extrait les 4 derniers caractères (le CRC envoyé)
        crc_recu = texte[-4:]
        # On calcule le CRC sur tout le début de la trame (tout sauf les 4 derniers car c le crc)
        # On s'assure que c'est bien une string pour le calcul
        crc_calc = self.crc16(str(texte[0:-4]))
        print(f"  --> CRC calculé : {crc_calc} | Reçu : {crc_recu}", end='')
        if crc_recu == crc_calc:
            print(" * Trame valide !")
            return True
        else:
            print(" ! Erreur CRC")
            return False
    
    def send_point_to_point_v(self, target_h, target_l, target_chan, message):
        """ MODE 1 : Envoyer à un récepteur précis """
        self.wait_aux()
        header = bytes([target_h, target_l, target_chan])
        message_txt = str(message)
        self.uart.write(header + " " + message_txt)
        print(f"Envoyé à {target_h:02x}{target_l:02x} sur canal {target_chan}")
        
    def send_point_to_point_txt(self, target_h, target_l, target_chan, message):
        """ MODE 1 : Envoyer à un récepteur précis """
        self.wait_aux()
        header = bytes([target_h, target_l, target_chan])
        self.uart.write(header + message.encode('utf-8'))
        print(f"Envoyé à {target_h:02x}{target_l:02x} sur canal {target_chan}")

    def send_broadcast(self, target_chan, message):
        """ MODE 2 : Envoyer à TOUS les modules sur un canal précis (FFFF) """
        self.wait_aux()
        header = bytes([0xFF, 0xFF, target_chan])
        self.uart.write(header + message.encode('utf-8'))
        print(f"Broadcast envoyé sur canal {target_chan}")

    
    def decoupage(self, texte):
        """ Analyse la trame reçue ($val1#val2#texte1#crc) et retourne un dictionnaire """
        try:
            parties = texte[1:].split('#')# On enlève le '$' du début et on découpe par les '#'
                                                                # texte[1:] permet de commencer après le premier caractère
            if len(parties) >= 4:
                return {
                    'val1':   int(parties[0]),
                    'val2':   int(parties[1]),
                    'texte1': parties[2],
                    'crc16':  parties[3]
                }
        except Exception as e:
            print(f"Erreur lors du découpage (decoupage) : {e}")
        
        return None

    def receive(self):
        if self.uart.any():
            data =  self.uart.read()
            return data
        return None

# --- EXEMPLE D'UTILISATION ---

# Initialisation
""" lora = LORAE32(uart_id=2, tx_pin=17, rx_pin=16, m0_pin=19, m1_pin=18, aux_pin=22)
lora.setup_config(0x00, 0x02, 23)

while True:
    data = lora.receive()
    validité = crc_valide() 
    if data and validité :
        resultat = lora.decoupage(data)
        if resultat:
            print(f"Données valides : {resultat['texte1']} (V1:{resultat['val1']})") """