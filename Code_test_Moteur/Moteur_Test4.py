from machine import Pin, PWM, Timer
import time

# Configuration des broches
STEP = Pin(0, Pin.OUT)   
DIR = Pin(2, Pin.OUT)
M0 = Pin(4, Pin.OUT)
M1 = Pin(5, Pin.OUT)
M2 = Pin(15, Pin.OUT)   
DEC0 = Pin(16, Pin.OUT)
DEC1 = Pin(17, Pin.OUT)
DEC2 = Pin(18, Pin.OUT)
EN = Pin(19, Pin.OUT)   
TRQ = Pin(21, Pin.OUT)
FAULT = Pin(22, Pin.OUT)
SLEEP = Pin(23, Pin.OUT)

# Configuration de la direction
DIR.value(1)

EN.value(0)
SLEEP.value(0) 

go = input("Return pour start")

EN.value(1)
SLEEP.value(1) 

pwm_step = PWM(STEP)
pwm_step.freq(1000)      
pwm_step.duty_u16(32768)

fin = input("Return pour stop")
EN.value(0)
SLEEP.value(0) 
pwm_step.deinit()


while True:
    pass
