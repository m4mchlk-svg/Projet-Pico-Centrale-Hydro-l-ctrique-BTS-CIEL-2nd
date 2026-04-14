import network
import socket
import urequests
import time
from machine import ADC, Pin, SoftI2C, Timer

# ========= CONFIGURATION CAPTEUR I2C (MB7040) =========
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=50000)
MB7040_ADDR = 0x70 
CMD_RANGE = 0x51 

# Variables globales pour le capteur
dist1, dist2, dist3, moyenne, error, count = 0, 0, 0, 0, 0, 0
max_error, max_marge = 2, 10

# ========= CAPTEURS ADC (Autres mesures) =========
adc_bat = ADC(Pin(34))      
adc_panneau = ADC(Pin(35))  

# ========= THINGSPEAK =========
THINGSPEAK_WRITE_KEY = "Z5R36BOW4YA29JFK"
THINGSPEAK_URL = "https://api.thingspeak.com/update"
last_upload = 0

# ========= WIFI (AP + STA) =========
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='PROJET_PICO', password='1234')

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('BTS_SN_IoT', 'BOU_BTS_SN')

print("Connexion WiFi BTS...")
while not wlan.isconnected():
    time.sleep(1)
ip_bts = wlan.ifconfig()[0]
print("BTS IP:", ip_bts)
print("Hotspot: 192.168.4.1")

# ========= FONCTIONS CAPTEUR MB7040 =========
def get_distance():
    try:
        i2c.writeto(MB7040_ADDR, bytes([CMD_RANGE]))
        time.sleep_ms(100)
        data = i2c.readfrom(MB7040_ADDR, 2)
        return (data[0] << 8) | data[1]
    except:
        return -1

def update_sensor_data(timer):
    """Fonction appelée par le Timer pour mettre à jour la moyenne de distance"""
    global max_marge, max_error, dist1, dist2, dist3, moyenne, error, count
    mesure = get_distance()
    
    if 20 <= mesure <= 765:
        if abs(mesure - dist1) <= max_marge or error >= max_error:
            dist3, dist2, dist1 = dist2, dist1, mesure
            moyenne = int((dist1 + dist2 + dist3) / 3)
            error = 0
        else:
            error += 1
        count += 1

def read_all_values():
    """Récupère toutes les données pour le web et ThingSpeak"""
    # 1. Valeur du capteur I2C (Distance Eau)
    eau = moyenne
    
    # 2. Simulation de la vanne (30cm sous l'eau comme dans ton code)
    vanne = eau - 30 if eau > 30 else 0
    
    # 3. Lectures ADC (Batterie / Panneau)
    # On peut convertir les valeurs brutes ici si nécessaire
    bat = "----" 
    panneau = "----"
    
    return bat, eau, vanne, panneau

# ========= SERVEUR WEB =========
html_page = '''<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROJET PICO</title>
    <style>
        body { background: #f4f6f9; color: #2c3e50; font-family: sans-serif; padding: 20px; }
        h1 { text-align: center; }
        .card { background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); padding: 15px 20px; margin: 10px 0; display: flex; align-items: center; justify-content: space-between; }
        .card-title { font-size: 16px; color: #7f8c8d; }
        .card-value { font-size: 36px; font-weight: 700; }
        .unit { font-size: 14px; color: #7f8c8d; }
        .ok { color: #27ae60; }
        .no-sensor { color: #e74c3c; }
    </style>
    <script>
        function updateValues(){
            fetch("/data").then(r => r.text()).then(d => {
                const v = d.split(",");
                document.getElementById("bat").innerHTML = v[0];
                document.getElementById("conso").innerHTML = v[1];
                document.getElementById("courant").innerHTML = v[2];
                document.getElementById("panneau").innerHTML = v[3];
            });
        }
        setInterval(updateValues, 2000);
    </script>
</head>
<body>
    <h1>SYSTEME MB7040</h1>
    <div class="card"><div><div class="card-title">Batterie</div><div class="card-value" id="bat">----</div></div><div class="unit">V</div></div>
    <div class="card"><div><div class="card-title">Hauteur eau (Réelle)</div><div class="card-value ok" id="conso">0</div></div><div class="unit">cm</div></div>
    <div class="card"><div><div class="card-title">Calcul Vanne (-30cm)</div><div class="card-value ok" id="courant">0</div></div><div class="unit">cm</div></div>
    <div class="card"><div><div class="card-title">Panneau</div><div class="card-value" id="panneau">----</div></div><div class="unit">A</div></div>
</body>
</html>'''

# ========= INITIALISATION SERVEUR & TIMER =========
# Vérification capteur
devices = i2c.scan()
if MB7040_ADDR not in devices:
    print("ALERTE: Capteur MB7040 non trouvé !")

# Lancement du Timer de mesure (1 seconde)
timer_sensor = Timer(1)
timer_sensor.init(mode=Timer.PERIODIC, period=1000, callback=update_sensor_data)

# Ouverture Socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)

# ========= BOUCLE PRINCIPALE =========
while True:
    try:
        # 1. Gestion ThingSpeak (toutes les 15 secondes pour respecter les quotas)
        if time.time() - last_upload > 15:
            _, eau, vanne, _ = read_all_values()
            try:
                url = f"{THINGSPEAK_URL}?api_key={THINGSPEAK_WRITE_KEY}&field1={eau}&field2={vanne}"
                r = urequests.get(url)
                r.close()
                last_upload = time.time()
                print(f"ThingSpeak mis à jour: {eau}cm")
            except:
                print("Erreur ThingSpeak")

        # 2. Serveur Web (Non-bloquant via accept avec timeout court si nécessaire)
        # Note: accept() est bloquant, donc la boucle attend une connexion web pour continuer
        conn, addr = s.accept()
        request = conn.recv(1024)
        req = str(request)

        if '/data' in req:
            bat, eau, vanne, panneau = read_all_values()
            response = f"{bat},{eau},{vanne},{panneau}"
            conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n' + response.encode())
        else:
            conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n' + html_page.encode())
        
        conn.close()
    except Exception as e:
        print("Erreur boucle:", e)
