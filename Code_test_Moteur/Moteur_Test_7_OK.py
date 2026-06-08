from machine import Pin, PWM, Timer, I2C, Pin
import time

# Configuration des broches
STEP = Pin(18, Pin.OUT)   
DIR = Pin(17, Pin.OUT) 
EN = Pin(19, Pin.OUT)
SLEEP = Pin(16, Pin.OUT)

# définition des constantes
HAUTEUR_SOUHAITE = 40   # valeur de hauteur souhaitée
SEUIL = 10              # seuil de réglagle
PAS = 1000              # temps avance moteur
FREQ = 1100             # fréquence de la PWM
DUTY = 32768            # rapport cyclique de la PWM

pwm_step = PWM(STEP)
pwm_step.freq(FREQ)      
pwm_step.duty_u16(DUTY)

def stop_moteur():
    print("moteur stop")
    EN.value(0)
    SLEEP.value(0) 
    pwm_step.deinit()
    time.sleep_ms(100)

def marche_avant():
    print("marche avant")
    # Configuration de la direction
    SLEEP.value(1)  # Réveillé
    EN.value(0)     # Activé
    DIR.value(0)    # Sens A - avant
    # mise en marche
    EN.value(1)
    SLEEP.value(1) 
    pwm_step = PWM(STEP)
    pwm_step.freq(FREQ)      
    pwm_step.duty_u16(DUTY)
    
def marche_arriere():
    print("marche arriere")
    # Configuration de la direction
    SLEEP.value(1)  # Réveillé
    EN.value(0)     # Activé
    DIR.value(1)    # Sens B - arrière
    # mise en marche
    EN.value(1)
    SLEEP.value(1) 
    pwm_step = PWM(STEP)
    pwm_step.freq(FREQ)      
    pwm_step.duty_u16(DUTY)

marche_avant()
time.sleep_ms(PAS)
stop_moteur()

marche_arriere()
time.sleep_ms(PAS)
stop_moteur()

    
    