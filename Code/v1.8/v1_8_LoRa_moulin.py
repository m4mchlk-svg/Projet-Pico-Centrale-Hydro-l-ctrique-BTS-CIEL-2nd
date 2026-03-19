from machine import UART, Pin
from LORAE32_lib import LORAE32
import time

lora = LORAE32(uart_id=2, tx_pin=17, rx_pin=16, m0_pin=19, m1_pin=18, aux_pin=22)
lora.setup_config(0x00, 0x02, 23)

compteur_trame_valide = 0

while True:
    lora.wait_aux()
    data = lora.receive()
    if data :
        data_rep = data.decode('utf-8').strip()
        print(f"MESSAGE BRUT : {data_rep}")
        if data.startswith('$') and lora.crc_valide(data_rep) :
            resultat = lora.decoupage(data_rep)
            for key in ['val1', 'val2', 'texte1', 'crc16']:
                    print(f"\t * {key}: {resultat[key]}")  # On affiche les données reçues
            compteur_trame_valide +=1
            print(f"Data Validé :{compteur_trame_valide}")
