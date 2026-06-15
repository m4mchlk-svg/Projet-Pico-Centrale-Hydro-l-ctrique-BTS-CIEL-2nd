# ******************************************************************
#   PROJET BTS CIEL 2026 - Pico-centrale hydroélectrique
#   Module LoRa E32-900T30D / pupitre sur ESP32 VROOM 32U  
#   By OH  - Mars / 2026   -    Version 1.0
# ******************************************************************

import time
from machine import UART, Pin
import time, random

class LoRaE32:
    def __init__(self, model, uart, aux_pin=None, m0_pin=None, m1_pin=None):
        self.uart = uart
        self.aux = Pin(aux_pin, Pin.IN) if aux_pin is not None else None
        self.m0 = Pin(m0_pin, Pin.OUT) if m0_pin is not None else None
        self.m1 = Pin(m1_pin, Pin.OUT) if m1_pin is not None else None
        self.model = model
        self.config = {
            'HEAD':   0xC0,
            'ADDR_H': 0x00,
            'ADDR_L': 0x01,    #  ***  adresse du pupitre ***
            'SPED':   0x1F,    #  9600bps 8N1 (défaut)
            'CHANNEL': 6,      # fréquence 868 MHz (canal 6)
            'OPTION': 0xC0     # Puissance max, mode fixe (point à point)
        }

    def _set_mode(self, mode):
        if self.m0 and self.m1:
            self.m0.value(mode & 1)
            self.m1.value((mode >> 1) & 1)
        time.sleep_ms(100)  # Stabilisation
        # Attendre que le module soit prêt via pin AUX
        if self.aux:
            while not self.aux.value():
                time.sleep_ms(10)
    
    def begin(self):
        # Passer en mode normal avant toute opération
        self._set_mode(0)
        time.sleep(0.1)
        return 0
 
    def send_data(self, dest_addr_high, dest_addr_low, dest_channel, data: bytes):
        # Forcer mode normal avant envoi
        self._set_mode(0)
        time.sleep(0.05)
        # Format du paquet : addr_h, addr_l, canal + data bytes
        packet = bytes([dest_addr_high, dest_addr_low, dest_channel]) + data  
        self.uart.write(packet)
        if self.aux:
            # attendre fin transmission
            while not self.aux.value():
                time.sleep_ms(10)

    def get_data(self):
        if self.uart.any():
            data = self.uart.read()
            if data :
                return data  
        return None

    def set_config(self, save=True):
        packet = bytes([
            self.config['HEAD'],
            self.config['ADDR_H'],
            self.config['ADDR_L'],
            self.config['SPED'],
            self.config['CHANNEL'],
            self.config['OPTION'],
            ])
        self._set_mode(3)  # Mode CONFIG obligatoire
        time.sleep_ms(10)
        self.uart.write(packet)
        time.sleep_ms(10)
        if save:
            save_cmd = bytes([0xC1, 0xC1, 0xC1])  # Cmd SAVE (3 octets)
            self.uart.write(save_cmd)
            time.sleep_ms(100)  # Flash write
        self._set_mode(0)

    def get_configuration(self):
        """Récupère la config du module E32"""
        self._set_mode(3)  # Mode CONFIG obligatoire
        # Vider buffer
        while self.uart.any():
            self.uart.read()
        # Commande C1 C1 C1
        self.uart.write(b'\xC1\xC1\xC1')
        time.sleep_ms(200)  # Temps réponse
        # Lire réponse (6 octets)
        response = self.uart.read(6)
        self._set_mode(0)  # Retour normal M0=0,M1=0
        if response and len(response) == 6 and response[0] != 0xFF:
            print("✅ Config OK!\n")
            return {
                'HEAD': f"0x{response[0]:02X}",
                'ADDR_H': f"0x{response[1]:02X}",
                'ADDR_L': f"0x{response[2]:02X}",
                'SPED': f"0x{response[3]:02X}",
                'CHANNEL': response[4],
                'OPTION': f"0x{response[5]:02X}"
            }
        return None

    def send_command(self, command):
        self._set_mode(3)  # Mode CONFIG pour toute commande
        time.sleep_ms(10)
        self.uart.write(command)
        time.sleep_ms(50)
        self._set_mode(0)
        if self.uart.any():
            return self.uart.read()
        return None
    
    def crc16(texte):  # Contrôle de redondance cyclique : détecter erreurs de transmission
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

    def get_trame():   # Création d'une trame sous la forme: $ val3 # val4 # texte2 #  
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        val3 = random.randint(100, 1000)
        val4 = random.randint(100, 1000)
        texte2 =  ''.join(random.choice(alphabet) for _ in range(4))
        print(f"\t * val3: {val3}")
        print(f"\t * val4: {val4}")
        print(f"\t * texte2: {texte2}")
        return "$"+str(val3) + "#" + str(val4) + "#" + texte2 + "#" 

    def envoyer_trame():
        print("\n*** Trame à envoyer ***")
        trame_emision = get_trame()        # Sous la forme: "  $ val3 # val4 # texte2 #  "
        crc = crc16(trame_emision)         # calcul du crc16 de la trame à émettre
        message = trame_emision + crc      # Sous la forme: "  $ val1 # val2 # texte # crc16  "
        self.send_data(addr_high_barrage, addr_low_barrage, CANAL, message.encode('utf-8'))  
        print("Message brut envoyé :", message.encode('utf-8'))

    def lecture_trame():
        msg = self.get_data() # Lecture du recepteur LoRa 
        if msg:
            trame_reception = msg.decode('utf-8').strip()
            print(f"\n*** Message brut reçu : {trame_reception}") # affichage trame brute
            if trame_reception.startswith('$') and crc_valide(trame_reception):
                resultat = parse_message(trame_reception)     # trame valide à analyser
                return resultat
            return "erreur"
        return None
