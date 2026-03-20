from machine import UART, Pin, Timer
import time
from LORAE32_lib import LORAE32

UART2 = 2  # deuxième port UART de l'ESP32
RX    = 17
TX    = 16
AUX   = 22
M0    = 21
M1    = 19

DEBIT = 9600               	# Débit communication série
SPED = 0x1A 		#Default param 9600bps baud rate /2.4k bps air rate
HEAD  = 0xC0		#working parameters head
OPTION =0xC4 		# mode fixe à 30 dBm

ad_va_h =  0x00
ad_va_l = 0x01
ad_va_chanel = 23

ad_mo_h =  0x00
ad_mo_l = 0x02
ad_mo_chanel = 23

flag_recv = False
flag_send = False
timer_send = Timer(2)

uart2 = UART(UART2, baudrate=DEBIT, tx=TX, rx=RX)
lora = LORAE32(uart=uart2, m0_pin=M0, m1_pin=M1, aux_pin=AUX)
lora.setup_config(HEAD, ad_mo_h, ad_mo_l,SPED, ad_mo_chanel, OPTION)

def inter_uart_recv(uart2):
    global flag_recv
    flag_recv = True
    
def inter_uart_send(timer_send):
    global flag_send
    flag_send = True

uart2.irq(handler=inter_uart_recv, trigger=UART.IRQ_RXIDLE)  # Active IRQ sur RX
timer_send.init(mode=Timer.PERIODIC, period=5000, callback=inter_uart_send)


compteur_trame_valide = 0

while True:
    lora.wait_aux()
    if flag_recv:    
        lora.receive_trame(compteur_trame_valide, flag_recv)
        
    if flag_send:
        lora.send_trame(ad_va_h, ad_va_l, ad_va_chanel, flag_send)
    
