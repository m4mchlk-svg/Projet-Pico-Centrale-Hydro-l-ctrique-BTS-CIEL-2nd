from machine import UART, Pin
import time

# Initialisation UART (Débit par défaut capteur : 115200)
uart = UART(2, baudrate=115200, tx=17, rx=16, bits=8, parity=None, stop=1)

# Trames de commandes Benewake (Format octets / bytes)
cmd_to_i2c = bytes([0x5A, 0x05, 0x0A, 0x01, 0x6A])	# Passer en I2C
cmd_save   = bytes([0x5A, 0x04, 0x11, 0x6F])		# Sauvegarder
cmd_reboot = bytes([0x5A, 0x04, 0x02, 0x60])		# Redémarrer

time.sleep(2)

# Envoi changement mode
uart.write(cmd_to_i2c)
time.sleep(0.1)

# Sauvegarde paramètres
uart.write(cmd_save)
time.sleep(1.0)

# Redémarrage
uart.write(cmd_reboot)
print("Capteur configuré en I2C !")