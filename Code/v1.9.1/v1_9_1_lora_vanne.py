from machine import UART, Pin, Timer
import time
from LORAE32_lib import *

lora = LORAE32(uart_id=2, tx_pin=17, rx_pin=16, m0_pin=19, m1_pin=18, aux_pin=22)
timer_send_data   = Timer(1)

ad_mo_h =  0x00
ad_mo_l = 0x02
ad_mo_chanel = 23

ad_va_h =  0x00
ad_va_l = 0x01
ad_va_chanel = 23

lora.setup_config(ad_va_h, ad_va_l, ad_va_chanel)

compteur_trame =0
compteur_trame_valide= 0
compteur_trame_invalide =0
flag_recv = False
flag_send = False

def send_data_ready(timer_send_data):
    global flag_send  # Pas de traitement long ici !
    flag_send = True  # données à envoter
    
def uart_handler(uart):    
    global flag_recv  # Pas de traitement long ici !
    flag_recv = True  # Présence données reçues sur RX !
    
lora.uart.irq(handler=uart_handler, trigger=UART.IRQ_RXIDLE)  # Active IRQ sur RX
timer_send_data.init(mode=Timer.PERIODIC, period=5000, callback=send_data_ready)


while True:
    lora.wait_aux()
    if flag_recv:
        compteur_trame, compteur_trame_valide, compteur_trame_invalide = lora.receive_trame(compteur_trame, compteur_trame_valide, compteur_trame_invalide)
        print(f"Data R :{compteur_trame}")
        print(f"Data V :{compteur_trame_valide}")
        print(f"Data F :{compteur_trame_invalide}")
        flag_recv = False
        #print(f"flag recv: {flag_recv}")
    
    if flag_send:
        lora.send_trame(ad_mo_h, ad_mo_l, ad_mo_chanel)
        #print(f"flag send : {flag_send}")
        flag_send = False
        #print(f"flag send : {flag_send}")
    
