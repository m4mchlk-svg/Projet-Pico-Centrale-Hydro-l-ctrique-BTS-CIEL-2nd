from machine import I2C, Pin
import time

class TFMiniPlus:
    def __init__(self, i2c_id=0, sda_pin=22, scl_pin=23, freq=400000, address=None):
        """
        Initialise le capteur TFMini Plus sur le bus I2C.
        """
        self.i2c = I2C(i2c_id, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=freq)
        
        # Détection de l'adresse
        if address is None:
            devices = self.i2c.scan()
            self.address = devices[0] if devices else 0x10
        else:
            self.address = address
            
        self.version = self._get_firmware_version()
        
        # Variables d'état et de traitement
        self.dist1 = 0
        self.dist2 = 0
        self.dist3 = 0
        self.moyenne = 0
        self.error = 0
        
        # Paramètres de configuration
        self.max_error = 2
        self.max_marge = 10
        self.att_moy = 100

    def _get_firmware_version(self):
        """Récupère la version du firmware du capteur."""
        try:
            self.i2c.writeto(self.address, b'\x5a\x04\x01\x5f')
            time.sleep_ms(100)
            res = self.i2c.readfrom(self.address, 7)
            
            if len(res) >= 7 and res[0] == 0x5a and res[2] == 0x01:
                return "V{}.{}.{}".format(res[3], res[4], res[5])
        except Exception:
            pass
        return "Inconnue"

    def read_raw_distance(self):
        """Récupère la distance brute du capteur."""
        try:
            self.i2c.writeto(self.address, b'\x5a\x05\x00\x01\x60')
            data = self.i2c.readfrom(self.address, 9)
            
            if len(data) >= 9 and data[0] == 0x59 and data[1] == 0x59:
                distance = data[2] + (data[3] << 8)
                return round(distance * 1.05)
        except Exception:
            return None
        return None

    def get_distance(self):
        """
        Gère les mesures, le filtrage (erreurs/marges) et la moyenne.
        Retourne la distance moyenne en cm, ou -1 si hors limite, ou None si erreur.
        """
        mesure = self.read_raw_distance()
        
        if mesure is None:
            return None

        # Initialisation lors de la première mesure valide
        if self.dist1 == 0:
            self.moyenne = mesure
            self.dist1 = self.dist2 = self.dist3 = mesure

        # Vérification des limites physiques
        if 10 < mesure < 1200:
            # Accepte la valeur si l'écart est correct et le max d'erreurs non atteint
            if abs(mesure - self.moyenne) <= self.max_marge and self.error <= self.max_error:
                
                self.dist3 = mesure
                time.sleep_ms(self.att_moy)
                self.dist2 = self.read_raw_distance() or self.dist2
                
                time.sleep_ms(self.att_moy)
                self.dist1 = self.read_raw_distance() or self.dist1
                
                self.moyenne = round((self.dist1 + self.dist2 + self.dist3) / 3)
                self.error = 0  # Réinitialise les erreurs car valeur valide
                
                return self.moyenne
            else:
                self.error += 1
                if self.error > self.max_error:
                    # Recalibrage après trop d'erreurs
                    self.error = 0
                    self.dist1 = self.dist2 = self.dist3 = self.moyenne = mesure
                    return self.moyenne
                # En cas d'erreur ignorée (en attendant le recalibrage)
                return None
        else:
            return -1 # Code pour signifier "Hors limite"
            
    def get_distance_bytes(self):
        """Retourne la distance sous forme de 2 octets (LSB, MSB)."""
        dist = self.get_distance()
        if dist is not None and dist != -1:
            lsb = dist & 0xFF
            msb = (dist >> 8) & 0xFF
            return bytes([lsb, msb])
        return None
