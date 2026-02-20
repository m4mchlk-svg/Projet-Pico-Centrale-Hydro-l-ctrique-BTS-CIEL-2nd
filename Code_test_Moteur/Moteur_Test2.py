from machine import Pin, PWM, Timer
import time



def pwm_out(t):
    
    global n1
    global n2

    out1.value(n2)
    out2.value(n1)
    if n1==0 and n2==0:
        n1=0
        n2=1
    elif n1==0 and n2==1:
        n1=1
        n2=1
    elif n1==1 and n2==1:
        n1=1
        n2=0
    elif n1==1 and n2==0:
        n1=0
        n2=0
 
n1=0
n2=0 
 
tim1 = Timer(1)
tim1.init(period=20, mode=Timer.PERIODIC, callback=pwm_out)

# Configuration des broches
dir1 = Pin(16, Pin.OUT)   # Direction
dir2 = Pin(18, Pin.OUT)
out1 = Pin(17, Pin.OUT)
out2 = Pin(19, Pin.OUT)
#pwm1 = PWM(Pin(17), freq=10000, duty=512) # create PWM object from a pin
#pwm2 = PWM(Pin(19), freq=10000, duty=512) # create PWM object from a pin

dir1.value(1)
dir2.value(1) 
time.sleep(1)

while True:
    pass

