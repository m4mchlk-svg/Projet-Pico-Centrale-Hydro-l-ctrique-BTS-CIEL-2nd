import network
import socket
import urequests
import time
from machine import ADC, Pin

# ========= CAPTEURS (réels, debug seulement) =========
# On déclare les entrées ADC pour les 4 capteurs (même si seulement 2 sont utilisés)
adc_bat = ADC(Pin(34))      # Batterie
adc_conso = ADC(Pin(32))    # Hauteur eau (valeur brute)
adc_courant = ADC(Pin(33))  # Hauteur vanne (valeur brute)
adc_panneau = ADC(Pin(35))  # Panneau solaire

# ========= THINGSPEAK =========
# Clé d'écriture de ton canal ThingSpeak
THINGSPEAK_WRITE_KEY = "Z5R36BOW4YA29JFK"
# URL de l'API ThingSpeak pour mettre à jour un canal
THINGSPEAK_URL = "https://api.thingspeak.com/update"
last_upload = 0             # Dernier instant où une donnée a été envoyée

# ========= SIMULATION RÉALISTE =========
# Valeurs de simulation pour remplacer les capteurs réels
eau_val = 175          # Hauteur eau départ (cm)
eau_dir = -1           # Direction : -1 = descend, +1 = monte
vanne_offset = 30      # Vanne toujours 30 cm sous l'eau

# ========= DOUBLE WIFI =========
# Création du point d'accès (hotspot) projet
ap = network.WLAN(network.AP_IF)      # Hotspot PROJET_PICO
ap.active(True)                       # On active le mode AP
ap.config(essid='PROJET_PICO', password='1234')   # Nom + mot de passe

# Création de la connexion STA (client WiFi)
wlan = network.WLAN(network.STA_IF)   # Mode station (se connecter au réseau BTS)
wlan.active(True)                     # On active le mode STA
wlan.connect('BTS_SN_IoT', 'BOU_BTS_SN')  # On se connecte au réseau
print("Connexion BTS...")
while not wlan.isconnected():
    time.sleep(1)
ip_bts = wlan.ifconfig()[0]           # On récupère l'IP obtenue
print("BTS IP:", ip_bts)
print("Hotspot: 192.168.4.1")

def update_fake_values():
    """Simulation RÉALISTE : eau 150↔200cm, vanne=eau-30cm"""
    global eau_val, eau_dir

    # On fait varier la hauteur eau lentement (+/-1cm)
    eau_val += eau_dir
    if eau_val >= 200:
        eau_val = 200
        eau_dir = -1
    elif eau_val <= 150:
        eau_val = 150
        eau_dir = 1

    # Vanne TOUJOURS 30 cm sous l'eau (physique respectée)
    vanne_val = eau_val - vanne_offset
    print(f"SIMUL: Eau={eau_val}cm | Vanne={vanne_val}cm")
    return eau_val, vanne_val   # <-- on retourne les deux valeurs calculées

def read_local_sensors():
    """UNE SEULE fonction : debug ADC + simulation réaliste"""
    # Lecture brute des capteurs (pour le debug dans la console)
    bat_raw = adc_bat.read_u16()
    eau_raw = adc_conso.read_u16()
    vanne_raw = adc_courant.read_u16()
    panneau_raw = adc_panneau.read_u16()
    print("RAW: B=", bat_raw, "E=", eau_raw, "V=", vanne_raw, "P=", panneau_raw)

    # Pour l'instant, batterie et panneau ne sont pas gérés = "----"
    bat = "----"
    panneau = "----"

    # On utilise la simulation réaliste pour eau et vanne
    eau, vanne = update_fake_values()   # <- récupération des valeurs simulées

    return bat, eau, vanne, panneau

def send_thingspeak(eau, vanne):
    """Envoi FORCÉ vers ThingSpeak (même simulation)"""
    global last_upload
    try:
        # Construction de l'URL ThingSpeak avec la clé et les champs
        url = (
            THINGSPEAK_URL +
            "?api_key=" + THINGSPEAK_WRITE_KEY +
            "&field1=" + str(eau) +        # Hauteur eau
            "&field2=" + str(vanne)         # Hauteur vanne
        )
        r = urequests.get(url)
        print("ThingSpeak OK:", r.text)  # "123" = numéro de l'entrée créée
        r.close()
        last_upload = time.time()
    except Exception as e:
        print("ThingSpeak ERREUR:", str(e)[:30])

def json_data():
    """Données pour page web : "----,175,145,----" """
    bat, eau, vanne, panneau = read_local_sensors()
    # On renvoie une chaîne CSV simple : bat,eau,vanne,panneau
    return f"{bat},{eau},{vanne},{panneau}"

# ========= PAGE WEB =========
# Page HTML affichée sur le hotspot (192.168.4.1)
# ========= PAGE WEB (nouveau design) =========
html_page = '''<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROJET PICO</title>
    <style>
        body {
            background: #f4f6f9;
            color: #2c3e50;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
        }
        h1 {
            text-align: center;
            margin: 20px 0;
            color: #2c3e50;
            font-weight: 600;
        }
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            padding: 15px 20px;
            margin: 10px 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: transform 0.1s ease, box-shadow 0.1s ease;
        }
        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.12);
        }
        .card-title {
            font-size: 16px;
            font-weight: 500;
            color: #7f8c8d;
            margin: 0 0 5px 0;
        }
        .card-value {
            font-size: 36px;
            margin: 0;
            font-weight: 700;
            color: #2c3e50;
        }
        .unit {
            font-size: 14px;
            color: #7f8c8d;
            margin-left: 6px;
        }
        .no-sensor {
            color: #e74c3c !important;
        }
        .ok {
            color: #27ae60 !important;
        }
    </style>
    <script>
        function updateValues(){
            fetch("/data")
            .then(r => r.text())
            .then(d => {
                const v = d.split(",");
                document.getElementById("bat").innerHTML = v[0];
                document.getElementById("conso").innerHTML = v[1];
                document.getElementById("courant").innerHTML = v[2];
                document.getElementById("panneau").innerHTML = v[3];

                colorStatus("bat", v[0]);
                colorStatus("conso", v[1]);
                colorStatus("courant", v[2]);
                colorStatus("panneau", v[3]);
            });
        }

        function colorStatus(id, val){
            const el = document.getElementById(id);
            el.className = (val == "----") ? "card-value no-sensor" : "card-value ok";
        }

        setInterval(updateValues, 2000);
        updateValues();
    </script>
</head>
<body>
    <h1>PROJET PICO</h1>

    <div class="card">
        <div>
            <div class="card-title">Batterie</div>
            <div class="card-value no-sensor" id="bat">----</div>
        </div>
        <div class="unit">V</div>
    </div>

    <div class="card">
        <div>
            <div class="card-title">Hauteur eau</div>
            <div class="card-value no-sensor" id="conso">----</div>
        </div>
        <div class="unit">cm</div>
    </div>

    <div class="card">
        <div>
            <div class="card-title">Hauteur vanne</div>
            <div class="card-value no-sensor" id="courant">----</div>
        </div>
        <div class="unit">cm</div>
    </div>

    <div class="card">
        <div>
            <div class="card-title">Panneau</div>
            <div class="card-value no-sensor" id="panneau">----</div>
        </div>
        <div class="unit">A</div>
    </div>
</body>
</html>'''


# ========= SERVEUR WEB =========
# On crée une socket TCP pour écouter sur le port 80
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# On peut réutiliser l'adresse (pour éviter les erreurs de port déjà utilisé)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# On écoute sur toutes les interfaces (hotspot + STA) sur le port 80
s.bind(('', 80))
s.listen(5)

print("🚀 DOUBLE WIFI + SIMULATION RÉALISTE")
print("Hotspot → 192.168.4.1")
print("BTS    →", ip_bts)

# ========= BOUCLE PRINCIPALE =========
while True:
    # Envoi ThingSpeak toutes les 10 secondes
    if time.time() - last_upload > 10:
        bat, eau, vanne, panneau = read_local_sensors()
        send_thingspeak(eau, vanne)   # On envoie seulement eau et vanne

    # Gestion du serveur web
    conn, addr = s.accept()  # On accepte une connexion entrante
    request = conn.recv(1024)
    req = str(request)

    # Si la requête contient '/data', on envoie juste les valeurs brutes
    if '/data' in req:
        response = json_data()
        # Une seule série de \r\n dans la chaîne b''
        conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\n' + response.encode())
    else:
        # Sinon on renvoie la page HTML complète
        response = html_page
        conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n' + response.encode())

    # On ferme la connexion
    conn.close()
