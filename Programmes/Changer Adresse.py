from machine import I2C, Pin
import time

OLD_ADDR = 0x14  # Adresse originale
NEW_ADDR = 0x10  # Nouvelle adresse

i2c = I2C(0, scl=Pin(23), sda=Pin(22), freq=100000)
time.sleep(2)

# Construction dynamique de la commande avec Checksum
cmd_base = [0x5A, 0x05, 0x0B, NEW_ADDR]
# Calcul du Checksum (somme des 4 premiers octets, masquée sur 8 bits)
checksum = sum(cmd_base) & 0xFF
cmd_base.append(checksum)

cmd_change_addr = bytes(cmd_base)
cmd_save = bytes([0x5A, 0x04, 0x11, 0x6F])

# Envoi modification à l'adresse originale
i2c.writeto(OLD_ADDR, cmd_change_addr)
time.sleep(0.1)

# Sauvegarde paramètres à l'adresse originale
i2c.writeto(OLD_ADDR, cmd_save)
time.sleep(1.0)

print(f"Adresse modifiée avec succès de {hex(OLD_ADDR)} à {hex(NEW_ADDR)} !")