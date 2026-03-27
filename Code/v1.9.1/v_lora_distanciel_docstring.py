from machine import UART, Pin
import time, random

class LORAE32:
    def __init__(self, uart_id, tx_pin, rx_pin, m0_pin, m1_pin, aux_pin):
        """
        initialisation materielle :

        variable entrée :
        uart-id : numéro de l'uart utilisé [1;2]
        tx_pin : numéro du tx de l'esp32
        rx_pin : numéro du rx de l'esp32
        m0_pin : numéro du m0 de l'esp32
        m1_pin : numéro du m1 de l'esp32
        aux_pin : numéro de l'AUX de l'esp32

        self.set_mode(0) : mode initialisé en mode normal

        """
        self.uart = UART(uart_id, baudrate=9600, tx=tx_pin, rx=rx_pin, timeout=200)
        self.m0 = Pin(m0_pin, Pin.OUT)
        self.m1 = Pin(m1_pin, Pin.OUT)
        self.aux = Pin(aux_pin, Pin.IN)
        self.set_mode(0) # Mode normal par défaut

    def wait_aux(self):
        """
        controle du signal AUX :

        used method :
        self.aux.value() : controle de la mise a 1 de l'AUX pour etre sur de la liberté d'envoi
        time.sleep_ms() : timing de sécurité

        """
        while self.aux.value() == 0:
            time.sleep_ms(1)
        time.sleep_ms(2)

    def set_mode(self, mode):
        """
        configuration des modes :

        used method :
        self.wait.aux() : vérification de la liberté du module 
        self.m0.value() : mise a 0 ou 1 de m0 selon le mode souhaité
        self.m1.value() : mise a 0 ou 1 de m0 selon le mode souhaité
        [ m0=0 ; m1=0 ] = mode 0 ; mode normal
        [ m0=0 ; m1=1 ] = mode 1 ; mode wake-up
        [ m0=1 ; m1=0 ] = mode 2 ; mode power-saving
        [ m0=1 ; m1=1 ] = mode 3 ; mode sleep/config

        """
        self.wait_aux()
        if mode == 0:   # NORMAL
            self.m1.value(0); self.m0.value(0)
        elif mode == 1: # WAKE-UP
            self.m1.value(0); self.m0.value(1)
        elif mode == 2: # POWER-SAVING
            self.m1.value(1); self.m0.value(0)
        elif mode == 3: # SLEEP / CONFIG
            self.m1.value(1); self.m0.value(1)
        self.wait_aux()

    def setup_config(self, addr_h, addr_l, channel):
        """
        variable entrée :
        addr_h : octet adresse haute du module emetteur
        addr_l : octet adresse basse du module emetteur
        channel : entier du canal du module emetteur

        used method :
        self.set_mode(3) : mise en mode config 
        bytes([0xC0, addr_h, addr_l, 0x1A, channel, 0xC4]) : trame de config du module emetteur
        self.uart.write(config_cmd) : envoyer la trame au module pour configuration
        self.uart.any() - self.uart.read() : lecture de la reponse du module 
        self.set_mode(0) : remise en mode normal pour la suite

        """
        self.set_mode(3)
        config_cmd = bytes([0xC0, addr_h, addr_l, 0x1A, channel, 0xC4])
        self.uart.write(config_cmd)
        time.sleep_ms(200)
        if self.uart.any():
            data = self.uart.read()
            print(f"Confirmation module : {data.hex().upper()}")
        self.set_mode(0)
        print(f"Configuration fixe appliquée sur canal {channel}")
        
    def get_trame(self):   # Création d'une trame sous la forme: $ val1 # val2 # texte #  
        """
        creation de trame aléatoire pour test : 

        used method :
        random.randint(100, 1000) : int aléatoire entre 100 et 1000 en val 1 et 2
        ''.join(random.choice(alphabet) for _ in range(4)) : 4 char aléatoire dans le str alphabet

        variable sortie :
        return "$"+str(val1) + "#" + str(val2) + "#" + texte + "#" : concaténation de tout les éléments pour envoi

        """
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        val1 = random.randint(100, 1000)
        val2 = random.randint(100, 1000)
        texte =  ''.join(random.choice(alphabet) for _ in range(4))
        print(f"\t * val1: {val1}")
        print(f"\t * val2: {val2}")
        print(f"\t * texte1: {texte}")
        return "$"+str(val1) + "#" + str(val2) + "#" + texte + "#"

    def crc16(self, texte):
        """
        variable entrée :
        texte : trame en sortie de get_trame

        variable sortie :
        crc16 : 2 octets pour controle
        
        """
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
        """ 
        Calcule le CRC16 de la trame reçue et le compare à celui transmis :

        variable entrée :
        texte : trame recu moins les 2 octets de crc16

        variable sortie : 
        return True or False selon la validité
        
        """
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
        
    def send_point_to_point(self, target_h, target_l, target_chan, message):
        """ 
        MODE 1 : Envoyer à un récepteur précis :
        
        variable entrée :
        target_h : octet adresse haute du module recepteur
        target_l : octet adresse basse du module recepteur
        target_chan : entier du canal du module recepteur
        message :  trame a envoyer 

        used method : 
        self.wait_aux : vérification de la liberté du module
        bytes([target_h, target_l, target_chan]) : header de la trame a envoyer
        self.uart.write(header + message.encode('utf-8')) : concaténation + envoie sur uart

        """
        self.wait_aux()
        header = bytes([target_h, target_l, target_chan])
        self.uart.write(header + message.encode('utf-8'))
        print(f"Envoyé à {target_h:02x}{target_l:02x} sur canal {target_chan}")

    def send_broadcast(self, target_chan, message):
        """ 
        MODE 2 : Envoyer à TOUS les modules sur un canal précis (FFFF) :
        
        """
        self.wait_aux()
        header = bytes([0xFF, 0xFF, target_chan])
        self.uart.write(header + message.encode('utf-8'))
        print(f"Broadcast envoyé sur canal {target_chan}")

    def decoupage(self, texte):
        """ 
        Analyse la trame reçue ($val1#val2#texte1#crc) et retourne un dictionnaire :
        
        """
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
        """
        used method : 
        self.uart.any() - self.uart.read() : lecture de la reception du module

        variable sortie :
        return data : octet de reception
        
        """
        if self.uart.any:
            data =  self.uart.read()
            return data
        return None
    
    def send_trame(self, ad_mo_h, ad_mo_l, ad_mo_chanel):
        """
        envoie de la trame: 

        variable entrée :
        ad_mo_h : adresse haute du recepteur
        ad_mo_l : adresse basse du recepteur
        ad_mo_chanel : canal du recepteur

        used method:
        self.get_trame() : trame random for test
        self.crc16() : code control
        self.send_point_to_point(ad_h, ad_l, ad_chanel, trame_send)
        """
        data_send  = self.get_trame() #variabilisé
        crc = self.crc16(data_send) #variabilisé
        trame_send = data_send + crc #concaténation
        self.send_point_to_point(ad_mo_h, ad_mo_l, ad_mo_chanel, trame_send) #envoie a un module
        print(trame_send)
        print("\n")
        
    def receive_trame(self, compteur_trame_recu, compteur_trame_recu_valide, compteur_trame_recu_invalide):
        """
        reception d'une trame + validation et affichage:

        variable entrée:
        compteur_trame_recu : nb de trame lu
        compteur_trame_recu_valide : nb de trame validé
        compteur_trame_recu_invalide : nb de trame invalidé

        used method:
        self.receive() : lecture de l'UART
        data.decode('utf-8').strip() : decodage de la trame en ascii pour traitement en texte
        data.startswith('$') : check que la trame commence par un $
        self.crc_valide(data_rep) : vérifie si le crc16 est identique
        self.decoupage(data_rep) : passe la data de string a dictionnaire 

        variable sortie:
        compteur_trame_recu : nb de trame lu
        compteur_trame_recu_valide : nb de trame validé
        compteur_trame_recu_invalide : nb de trame invalidé
        """
        data = self.receive()
        try :
            if data :
                compteur_trame_recu += 1
                data_rep = data.decode('utf-8').strip()
                print(f"MESSAGE B  RUT : {data_rep}")
                if data.startswith('$') and self.crc_valide(data_rep) :
                    resultat = self.decoupage(data_rep)
                    compteur_trame_recu_valide += 1
                    for key in ['val1', 'val2', 'texte1', 'crc16']:
                            print(f"\t * {key}: {resultat[key]}")  # On affiche les données reçues
                    #compteur_trame_valide +=1      
                else:
                    compteur_trame_recu_invalide += 1
                    pass
        except Exception as e:
            print(f"Erreur lors de la reception : {e}")
        return compteur_trame_recu, compteur_trame_recu_valide, compteur_trame_recu_invalide
