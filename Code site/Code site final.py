import network
import socket
import urequests
import time
from machine import ADC, Pin

adc_bat = ADC(Pin(34))
adc_conso = ADC(Pin(32))    # Eau
adc_courant = ADC(Pin(33))  # Vanne
adc_panneau = ADC(Pin(35))

THINGSPEAK_WRITE_KEY = "Z5R36BOW4YA29JFK"
THINGSPEAK_URL = "https://api.thingspeak.com/update"
last_upload = 0

# WiFi (MARCHE)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('BTS_SN_IoT', 'BOU_BTS_SN')
print("Connexion WiFi...")
while not wlan.isconnected():
    time.sleep(1)
print("WiFi OK:", wlan.ifconfig()[0])

def read_local_sensors():
    bat_raw = adc_bat.read_u16()
    eau_raw = adc_conso.read_u16()
    vanne_raw = adc_courant.read_u16()
    panneau_raw = adc_panneau.read_u16()
    
    print("RAW: B=",bat_raw,"E=",eau_raw,"V=",vanne_raw,"P=",panneau_raw)
    
    # Seuils selon tes RAW
    if bat_raw < 500: bat = "----"
    else: bat = round(bat_raw * 3.3 / 65535 * 2, 1)
    if eau_raw < 10000: eau = "----"
    else: eau = int(eau_raw / 65535 * 200)
    if vanne_raw < 5000: vanne = "----"
    else: vanne = int(vanne_raw / 65535 * 50)
    if panneau_raw < 500: panneau = "----"
    else: panneau = round(panneau_raw / 65535 * 10, 1)
        
    return bat, eau, vanne, panneau

def send_thingspeak(eau, vanne):
    global last_upload
    test_count = 0  # Compteur test
    try:
        # FORCE TEST : envoie 125/32 TOUT LE TEMPS
        r = urequests.get(THINGSPEAK_URL + "?api_key=" + THINGSPEAK_WRITE_KEY + "&field1=125&field2=32")
        test_count += 1
        print("FORCE OK [",test_count,"]:", r.text)
        r.close()
        last_upload = time.time()
    except Exception as e:
        print("FORCE ERREUR:", str(e)[:30])


def json_data():
    return f"{read_local_sensors()[0]},{read_local_sensors()[1]},{read_local_sensors()[2]},{read_local_sensors()[3]}"

html_page = '''<html><head><meta name="viewport" content="width=device-width"><title>Monitoring</title><style>body{background:white;color:black;font-family:Arial;padding:20px;}h1{text-align:center;color:black;}.box{background:#f0f0f0;padding:20px;margin:10px;border:2px solid black;}.title{font-size:20px;}.value{font-size:50px;}.no-sensor{color:#ff4444;}.ok{color:#00aa00;}</style><script>function updateValues(){fetch("/data").then(r=>r.text()).then(d=>{const v=d.split(",");document.getElementById("bat").innerHTML=v[0];document.getElementById("conso").innerHTML=v[1];document.getElementById("courant").innerHTML=v[2];document.getElementById("panneau").innerHTML=v[3];colorStatus("bat",v[0]);colorStatus("conso",v[1]);colorStatus("courant",v[2]);colorStatus("panneau",v[3]);});}function colorStatus(id,val){const el=document.getElementById(id);el.className=(val=="----")?"value no-sensor":"value ok";}setInterval(updateValues,2000);updateValues();</script></head><body><h1>PROJET PICO</h1><div class="box"><div class="title">Batterie</div><div class="value no-sensor" id="bat">----</div><div>V</div></div><div class="box"><div class="title">Hauteur eau</div><div class="value no-sensor" id="conso">----</div><div>cm</div></div><div class="box"><div class="title">Hauteur vanne</div><div class="value no-sensor" id="courant">----</div><div>cm</div></div><div class="box"><div class="title">Panneau</div><div class="value no-sensor" id="panneau">----</div><div>A</div></div></body></html>'''

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)

print("FULL SYSTEM OK ! IP:", wlan.ifconfig()[0])

while True:
    if time.time() - last_upload > 20:
        bat, eau, vanne, panneau = read_local_sensors()
        send_thingspeak(eau, vanne)
    
    conn, addr = s.accept()
    request = conn.recv(1024)
    req = str(request)
    
    if '/data' in req:
        response = json_data()
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: text/plain\n')
        conn.send('Connection: close\n\n')
        conn.send(response)
    else:
        response = html_page
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: text/html\n')
        conn.send('Connection: close\n\n')
        conn.send(response)
    
    conn.close()
