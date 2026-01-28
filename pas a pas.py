import time
from machine import Pin, PWM

dir1 = Pin(16, Pin.OUT)    # create output pin on GPIO0
#p0.on()                 # set pin to "on" (high) level
#p0.off()                # set pin to "off" (low) level
#dir1.value(1)             # set pin to on/high

pwm1 = PWM(Pin(17), freq=10000, duty=512) # create PWM object from a pin

while True:
    dir1.value(1)             # set pin to on/high
    time.sleep(1)
    dir1.value(0)             # set pin to off/low
    time.sleep(1)