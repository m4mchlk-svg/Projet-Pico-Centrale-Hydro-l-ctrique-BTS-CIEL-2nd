from machine import I2C, Pin
import time

# Adresse I2C par défaut TFmini Plus
TFMINI_ADDR = 0x10 

# Initialisation bus I2C
i2c = I2C(0, scl=Pin(23), sda=Pin(22), freq=400000)

cmd_to_uart = bytes([0x5A, 0x05, 0x0A, 0x00, 0x69])	# Passer en UART
cmd_save    = bytes([0x5A, 0x04, 0x11, 0x6F])		# Sauvegarder
cmd_reboot  = bytes([0x5A, 0x04, 0x02, 0x60])		# Redémarrer

time.sleep(2)

# Envoi vers adresse I2C capteur
i2c.writeto(TFMINI_ADDR, cmd_to_uart)
time.sleep(0.1)

# Sauvegarde
i2c.writeto(TFMINI_ADDR, cmd_save)
time.sleep(1.0)

# Redémarrage
i2c.writeto(TFMINI_ADDR, cmd_reboot)
print("Capteur configuré en UART !")