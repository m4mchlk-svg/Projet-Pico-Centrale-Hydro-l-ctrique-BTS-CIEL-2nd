+  Doc_perso_MICHALAK_... : Rapport de projet Vx.y ,Update frequente ou ajout de pdf supplementaire
+  Datasheet Module
+  Code LoRa Emission : sur wipi
+  Code LoRa Reception : sur wipi
+  V1_LoRa : les fonctions marches mais la communication ne se fait pas
+  def_potable : fonctions potentiellements utilisable ou inspirable pour la suite
+  v1.2_LoRa : communication faite , envoie de texte reussi et reception obtenue
+  v1.3_LoRa : communication faite , envoie d'une valeur apres passage en string et reception obtenue
+  com_esp_LoRa : schéma de cablage du module a l'ESP32
+  readme_def : description des fonction du code


# Wiki-code du LoRa 

## Library :
```
from machine import UART, Pin
import time
```
## Pin Config :
```
uart = UART(2, baudrate=9600, tx=17, rx=16, timeout=200)
m0 = Pin(19, Pin.OUT)
m1 = Pin(18, Pin.OUT)
aux = Pin(22, Pin.IN)
```

## Fonction Configuration :

### controle aux 
```
def wait_aux():
    while aux.value() == 0:
        time.sleep_ms(1)
    time.sleep_ms(2)
```
>Cette definition sert a mettre en place le controle de l'`aux` car cette pin indique si le module est occupé ou si il est possible de pouvoir communiquer avec le module ou tout simplement de transmettre ou recevoir une information
>>AUX(0) -> Busy / AUX(1) -> Open

### choix du mode
```
def set_mode(mode):
    """ Change le mode du module (0 à 3) proprement """
    wait_aux()
    if mode == 0:     # NORMAL : Envoi/Réception
        m1.value(0); m0.value(0)
    elif mode == 1:   # WAKE-UP 
        m1.value(0); m0.value(1)
    elif mode == 2:   # POWER-SAVING 
        m1.value(1); m0.value(0)
    elif mode == 3:   # SLEEP : Configuration / Lecture
        m1.value(1); m0.value(1)
    
    time.sleep_ms(20) # Temps de stabilisation du mode
    wait_aux()
    print(f"Mode {mode} active")
```
>Cette definition sert a mettre en place le changement de mode du module celon les besoins
>> - `mode(0)` -> Normal : Emmission-Reception
>> - `mode(1)` -> Wake-Up : Emmission only ... mode(0) mais rajoute des data pour reveiller le recepteur en mode(3)
>> - `mode(2)` -> Power-Saving : Reception only ... attends le reveil du emmetteur en mode(1)pour faire quelque-chose
>> - `mode(3)` -> Sleep : Sleep-Configuration ... traite les parametres de config si necessaire et dort 

### configuration module en fixe
```
def setup_fixed_transmission(addr_h, addr_l, channel):
    set_mode(3) # Mode config 
    
    # Trame : C0 (Permanent) + ADDR_H + ADDR_L + 1A (9600bps/2.4k) + CHAN + C4 (Fixe)
    config_cmd = bytes([0xC0, addr_h, addr_l, 0x1A, channel, 0xC4])
    
    print(f"Envoi configuration fixe : {config_cmd.hex().upper()}")
    uart.write(config_cmd)
    
    time.sleep_ms(200)
    if uart.any():
        response = uart.read()
        print(f"Confirmation module : {response.hex().upper()}")
    
    set_mode(0) # Retour au mode normal
```
>Cette definition sert a mettre en place la configuration du module en vu d'une communication par un protocole en liaison fixe ,c'est a dire entre deux modules specifiques.
Elle sert a configurer le composant en lui donnant une adresse et un canal pour etablir la communication

| No.| Item| Desc|
| :-: | :-: | :-: |
| 0| HEAD| this frame data is ctrl.cmd.|
| 1| ADDH| high address byte |
| 2| ADDL| low address byte|
| 3| SPED| UART parity + data and baud rate|
| 4| CHAN| channel byte|
| 5| OPTN| fixed or broadcast tsm. ,IO drive and tsm.power|
>Exemple de la configuration utilisé - address : 1 - canal : 23

| Byte | B0 | B1 | B2 | B3 | B4 | B5 |
| --- | --- | --- | --- | --- | --- | --- |
| Hex | 0xC0 | 0x00 | 0x01 | 0x1A | 0x17 | 0xC4 |

## Fonction Transmission :

### Envoie de variable au format texte
```
def send_point_to_point_v(target_h, target_l, target_chan, message):
    wait_aux()
    header = bytes([target_h, target_l, target_chan])
    message_txt = str(message)
    uart.write(header + " " + message_txt)
    print(f"Envoyé à {target_h:02x}{target_l:02x} sur canal {target_chan}")
```
>Cette definition sert a mettre en place l'envoie d'une variable numerique entiere au format texte a un module specifique
>>La variable `message` prend la variable numerique mise en parametre

### Envoie de texte a un module precis
```
def send_point_to_point_txt(target_h, target_l, target_chan, message):
    wait_aux()
    header = bytes([target_h, target_l, target_chan])
    uart.write(header + message.encode('utf-8'))
    print(f"Envoyé à {target_h:02x}{target_l:02x} sur canal {target_chan}")
```
>Cette definition sert a mettre en place l'envoie d'un texte a un module specifique
>>La variable `message` prend le string mis en parametre

### Envoie de texte a tout un canal
```
def send_broadcast(target_chan, message):
    wait_aux()
    header = bytes([0xFF, 0xFF, target_chan])
    uart.write(header + message.encode('utf-8'))
    print(f"Broadcast envoyé sur canal {target_chan}")
```
>Cette definition sert a mettre en place l'envoie d'un texte a tout les modules du canal choisi
>>La variable `message` prend le string mis en parametre

## Fonction Reception : 

### Reception txt + Affichage  
```
def receive_monitoring():
    """ MODE 3 : Ecouter les messages entrants """
    if uart.any():
        data = uart.read()
        try:
            print(f"Message reçu : {data.decode('utf-8')}")
        except:
            print(f"Message reçu (HEX) : {data.hex()}")
        return data
    return None
```
>Cette definition sert a mettre en place l'affichage console du message envoyer par le module transmetteur

### Reception txt + trad var + Affichage 
```
def receive_v():
    if uart.any():
        global data 
        data = uart.read()
        int_data = int(data)
        try:
            if debug: 
                print(f"Message reçu : {int_data.decode('utf-8')}")
                print(int_data)
        except:
            if debug: 
                print(f"Message reçu (HEX) : {int_data.hex()}")
        return data
    return None
```
>Cette definition sert a mettre en place l'affichage console du message envoyer par le module transmetteur


