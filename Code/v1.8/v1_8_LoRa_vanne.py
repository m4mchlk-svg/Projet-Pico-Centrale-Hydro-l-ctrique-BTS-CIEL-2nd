from machine import UART, Pin
from LORAE32_lib import LORAE32
import time, random

# --- CONFIGURATION MATÉRIELLE ---
# UART2 : TX=GPIO 17 (vers RX LoRa), RX=GPIO 16 (vers TX LoRa)
lora = LORAE32(uart_id=2, tx_pin=17, rx_pin=16, m0_pin=19, m1_pin=18, aux_pin=22)
lora.setup_config(0x00, 0x01, 23)

ad_mo_h =  0x00
ad_mo_l = 0x02
ad_mo_chanel = 23

while True:
    data_send  = lora.get_trame()
    crc = lora.crc16(data_send)
    trame_send = data_send + crc
    lora.send_point_to_point_txt(ad_mo_h, ad_mo_l, ad_mo_chanel, trame_send)
    print(trame_send)
    time.sleep(10)
