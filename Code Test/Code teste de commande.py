import time
from machine import UART

uart = UART(2, 57600, tx=17, rx=16)
uart.init(57600, bits=8, parity=None, stop=1)
uart.write('AT+SHCONN\r\n') 

time.sleep(1)

if uart.any():
    result = uart.read()
    answer = result.decode('utf-8')
    answer = answer.strip()
    print(answer)
