import struct

def formater_trame_complete(temp, humid, batt):
    # Format : < (Little Endian)
    # c : Tag Temp ('T')
    # f : Valeur Temp
    # c : Tag Humid ('H')
    # f : Valeur Humid
    # B : Niveau Batterie (0-100)
    format_chaine = '<cfcfcB'
    
    trame = struct.pack(format_chaine, 
                        b'T', temp, 
                        b'H', humid, 
                        b'B', batt)
    return trame

ma_trame = formater_trame_complete(25.4, 60.2, 98)
# On envoie 'ma_trame' directement au module LoRa via uart.write()

target_addr = 0x0001
target_chan = 0x04

# En-tête E32 (Big Endian pour les adresses réseau souvent)
header = struct.pack('>HB', target_addr, target_chan)

# Trame finale = [Header E32] + [Tes données structurées]


def decoder_donnees(trame_recue):
    # On sait que notre trame fait 11 octets (1+4 + 1+4 + 1)
    if len(trame_recue) == 11:
        # On extrait selon le même format
        data = struct.unpack('<cfcfcB', trame_recue)
        
        # data ressemble à : (b'T', 25.4, b'H', 60.2, 98)
        print(f"Capteur : {data[0].decode()} | Valeur : {data[1]} °c\n")
        print(f"Capteur : {data[2].decode()} | Valeur : {data[3]} %%\n")
        print(f"Batterie : {data[4].decode()} | Valeur : {data[5]} %%\n")
        
envoi_final = header + ma_trame
#print(envoi_final)

decoder_donnees(envoi_final)
