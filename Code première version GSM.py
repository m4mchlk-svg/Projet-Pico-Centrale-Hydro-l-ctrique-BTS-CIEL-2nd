import time
from machine import UART

uart1 = UART(1, baudrate=115200, tx=16, rx=17)
uart1.write('AT\r\n') 

time.sleep(1)

if uart1.any():
    result = uart1.read()
    answer = result.decode('utf-8')
    answer = answer.strip()
    print(answer)