from lora_e32 import LoRaE32
import time

# Initialisation
lora = LoRaE32(uart_id=2, tx=17, rx=16, m0_pin=19, m1_pin=18, aux_pin=22)

# Configuration : Adresse 0x0001, Canal 23
lora.setup_fixed_transmission(0x00, 0x02, 23)

compteur = 1
while True:
    lora.receive_txt()
    lora.wait_aux()
