# ******************************************************************
#   PROJET BTS CIEL 2026 - Pico-centrale hydroélectrique
#   Module LoRa E32-900T30D / barrage sur ESP32 VROOM 32U  
#   By OH  - Mars / 2026   -    Version 1.0
# ******************************************************************

# Ce fichier contient la class LoRaE32 qui permet d'instancier des objets
# permettant de programmer le module LoRa E32-900T30D. Il doit être stoché dans
# la mémoire de l'ESP32. Les versions pour le pupitre et pour le barrage sont
# identiques. Il n'y a que l'adresse initiale du module qui change...
#  LoRaE32-Barage.py  --> adresse module LoRa 0X0000
#  LoRaE32-pupitre.py --> adresse module LoRa 0X0001

import time
from machine import UART, Pin

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
            'ADDR_L': 0x00,    #  ***  adresse du barrage ***
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
    
    def check_config(self):
        """
        Compare la configuration physique du module avec la configuration 
        logicielle définie dans l'objet lora_pupitre.
        """
        print("Vérification de la cohérence de la configuration...")
        
        # Lecture de la configuration réelle du module (retourne un dictionnaire de strings)
        config_reelle = self.get_configuration()
        
        if not config_reelle:
            print(f"Erreur : Impossible de lire le module.")
            return False

        # Liste des clés à comparer (on ignore HEAD qui est une commande de mode)
        cles_a_verifier = ['ADDR_H', 'ADDR_L', 'CHANNEL', 'OPTION']
        erreurs = 0

        for cle in cles_a_verifier:
            # Valeur attendue (dans lora_pupitre.config)
            val_attendue = self.config[cle]
            
            # Valeur lue (on convertit le string hexadécimal "0xXX" en entier pour comparer)
            # Note : CHANNEL est déjà un entier dans votre lib, les autres sont des strings
            val_lue = config_reelle[cle]
            if isinstance(val_lue, str) and val_lue.startswith("0x"):
                val_lue = int(val_lue, 16)
            
            if val_lue == val_attendue:
                print(f"  [OK] {cle}: {val_attendue}")
            else:
                print(f"[DEFAUT] {cle}: Attendu {val_attendue}, Lu {val_lue}\n")
                erreurs += 1

        if erreurs == 0:
            print(f"Sychronisation parfaite : le module est bien configuré.\n")
            return True
        else:
            print(f"Alerte : {erreurs} paramètre(s) ne correspondent pas.\n")
            return False
