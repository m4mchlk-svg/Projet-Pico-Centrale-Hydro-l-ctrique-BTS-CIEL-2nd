import network
import socket
import urequests
import time
from machine import I2C, Pin, Timer

# ========= CONFIGURATION I2C (TFmini Plus) =========
i2c = I2C(0, sda=Pin(21), scl=Pin(22), freq=400000)

dist1, dist2, dist3, hauteur = 0, 0, 0, 0
error, count = 0, 0
max_error, max_marge = 2, 10
timer_period_ms, error_period_ms = 1000, 250
att_moy = 100
mesure_hauteur = 0
prep = 0
timer_sensor = None  # Sera initialisé plus bas

print("Recherche de capteurs I2C...")
devices = i2c.scan()
if devices:
    TFMINI_ADDR = devices[0]
    print("Capteur trouvé à l'adresse:", hex(TFMINI_ADDR))
else:
    print("Aucun capteur détecté. Adresse par défaut 0x10")
    TFMINI_ADDR = 0x10

# ========= THINGSPEAK =========
THINGSPEAK_WRITE_KEY = "Z5R36BOW4YA29JFK"
THINGSPEAK_URL       = "https://api.thingspeak.com/update"
last_upload = 0

# ========= WIFI (STABILISÉ) =========
print("Nettoyage des interfaces WiFi...")
try:
    # On récupère les instances
    sta_net = network.WLAN(network.STA_IF)
    ap_net = network.WLAN(network.AP_IF)
    
    # On ne les coupe que si elles sont déjà actives
    if sta_net.active(): sta_net.active(False)
    if ap_net.active(): ap_net.active(False)
    time.sleep_ms(300)
except Exception as e:
    print("Note: Pas de nettoyage nécessaire (", e, ")")

print("Démarrage WiFi AP (PROJET_PICO)...")
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='PROJET_PICO', password='1234')
print("AP OK: PROJET_PICO / 192.168.4.1")

time.sleep_ms(500) 

print("Activation WiFi Station (Connexion BTS)...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

time.sleep_ms(500) 

print("Tentative de connexion à la borne...")
wlan.connect('BTS_SN_IoT', 'BOU_BTS_SN')

# ========= FONCTIONS CAPTEUR =========
def get_distance():
    try:
        i2c.writeto(TFMINI_ADDR, b'\x5a\x05\x00\x01\x60')
        data = i2c.readfrom(TFMINI_ADDR, 9)
        if len(data) >= 9 and data[0] == 0x59 and data[1] == 0x59:
            distance = data[2] + (data[3] << 8)
            distance = round(distance * 1.05)
            return distance
    except:
        return None
    return None


def use_data():
    global dist1, dist2, dist3, hauteur, error, count, att_moy, prep, timer_sensor
    mesure = get_distance()

    if mesure is not None:
        if dist1 == 0:
            hauteur = mesure
            dist1 = mesure
            dist2 = mesure
            dist3 = mesure

        if 10 < mesure < 1200:
            if abs(mesure - hauteur) <= max_marge:
                dist3 = mesure

                time.sleep_ms(att_moy)
                mesure = get_distance()
                if mesure is None: mesure = dist3
                dist2 = mesure

                time.sleep_ms(att_moy)
                mesure = get_distance()
                if mesure is None: mesure = dist2
                dist1 = mesure

                hauteur = round((dist1 + dist2 + dist3) / 3)
                error = 0
                count += 1

                if count > prep:
                    print("Distance n°{}: {} cm".format(count, hauteur))

                if timer_sensor is not None:
                    timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)

                return hauteur

            else:
                if timer_sensor is not None:
                    timer_sensor.init(mode=Timer.PERIODIC, period=error_period_ms, callback=interrupt_hauteur)
                error += 1
                if error > max_error:
                    error = 0
                    hauteur = mesure
                    dist1 = mesure
                    dist2 = mesure
                    dist3 = mesure
                    if timer_sensor is not None:
                        timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)
                return hauteur
        else:
            print("Hors limite: {} cm".format(mesure))
            return hauteur
    return hauteur


def interrupt_hauteur(timer):
    global mesure_hauteur
    mesure_hauteur = 1


def read_all_values():
    return "----", hauteur, "----"


# ========= PAGE HTML =========
html_page = b'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TFmini Plus | Station Riviere</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Exo+2:wght@300;400;600&display=swap');
:root{
  --deep:#062a3a;--mid:#0a4a6b;--light:#1a7fa8;--accent:#00d4ff;
  --surface:rgba(10,74,107,0.45);--glass:rgba(255,255,255,0.07);
  --text:#d0f0ff;--muted:#7ab8d4;
}
*{margin:0;padding:0;box-sizing:border-box}
body{min-height:100vh;background:var(--deep);font-family:'Exo 2',sans-serif;color:var(--text);overflow-x:hidden;position:relative;}
.bg-waves{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none}
.wave{position:absolute;width:200%;height:200%;border-radius:40%;opacity:.08;animation:spin linear infinite}
.wave:nth-child(1){background:radial-gradient(ellipse,#00d4ff 0%,transparent 70%);top:-60%;left:-50%;animation-duration:18s}
.wave:nth-child(2){background:radial-gradient(ellipse,#0a9fd4 0%,transparent 70%);top:-40%;left:-30%;animation-duration:24s;animation-direction:reverse;opacity:.06}
.wave:nth-child(3){background:radial-gradient(ellipse,#062a3a 0%,#1a7fa8 60%,transparent 80%);top:20%;left:-60%;animation-duration:30s;opacity:.12}
@keyframes spin{to{transform:rotate(360deg)}}
.particles{position:fixed;inset:0;z-index:0;pointer-events:none}
.dot{position:absolute;border-radius:50%;background:var(--accent);animation:rise linear infinite;opacity:0}
@keyframes rise{0%{transform:translateY(0) scale(1);opacity:.6}100%{transform:translateY(-100vh) scale(0);opacity:0}}
.wrap{position:relative;z-index:1;max-width:480px;margin:0 auto;padding:24px 16px 40px}
header{text-align:center;margin-bottom:32px}
.logo-ring{width:72px;height:72px;border-radius:50%;border:2px solid var(--accent);display:flex;align-items:center;justify-content:center;margin:0 auto 14px;box-shadow:0 0 24px rgba(0,212,255,.35);animation:pulse 3s ease-in-out infinite;font-size:28px;}
@keyframes pulse{0%,100%{box-shadow:0 0 24px rgba(0,212,255,.35)}50%{box-shadow:0 0 42px rgba(0,212,255,.65)}}
h1{font-family:'Orbitron',sans-serif;font-size:1.35rem;letter-spacing:3px;color:var(--accent);text-shadow:0 0 18px rgba(0,212,255,.5)}
.subtitle{font-size:.78rem;color:var(--muted);letter-spacing:2px;margin-top:4px;text-transform:uppercase}
.status-bar{display:flex;align-items:center;gap:8px;background:var(--glass);border:1px solid rgba(0,212,255,.15);border-radius:30px;padding:7px 16px;margin-bottom:24px;font-size:.75rem;color:var(--muted);letter-spacing:1px;}
.dot-live{width:77px;height:7px;border-radius:50%;background:#00ff88;box-shadow:0 0 8px #00ff88;animation:blink 1.4s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.hero-card{background:linear-gradient(135deg,rgba(0,212,255,.12),rgba(10,74,107,.6));border:1px solid rgba(0,212,255,.3);border-radius:20px;padding:28px 24px;margin-bottom:16px;text-align:center;position:relative;overflow:hidden;box-shadow:0 8px 32px rgba(0,0,0,.4),inset 0 1px 0 rgba(255,255,255,.08);}
.hero-card::before{content:'';position:absolute;inset:0;background:repeating-linear-gradient(90deg,transparent,transparent 19px,rgba(0,212,255,.04) 20px),repeating-linear-gradient(0deg,transparent,transparent 19px,rgba(0,212,255,.04) 20px);}
.hero-label{font-size:.7rem;letter-spacing:3px;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.hero-value{font-family:'Orbitron',sans-serif;font-size:4rem;font-weight:700;color:#fff;line-height:1;text-shadow:0 0 30px rgba(0,212,255,.7);}
.hero-unit{font-size:.95rem;color:var(--accent);letter-spacing:2px;margin-top:6px}
.water-bar-wrap{margin-top:18px;background:rgba(0,0,0,.3);border-radius:30px;height:10px;overflow:hidden}
.water-bar{height:100%;border-radius:30px;background:linear-gradient(90deg,#0a9fd4,#00d4ff);transition:width 1s ease;box-shadow:0 0 12px rgba(0,212,255,.6)}
.cards-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.card{background:var(--surface);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:18px 14px;position:relative;overflow:hidden;transition:transform .2s;box-shadow:0 4px 20px rgba(0,0,0,.3);}
.card:active{transform:scale(.97)}
.card::after{content:'';position:absolute;top:-30px;right:-30px;width:80px;height:80px;border-radius:50%;background:radial-gradient(circle,rgba(0,212,255,.1),transparent);}
.card-icon{font-size:1.5rem;margin-bottom:8px}
.card-label{font-size:.65rem;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:6px}
.card-val{font-family:'Orbitron',sans-serif;font-size:1.6rem;font-weight:700;color:#fff}
.card-unit{font-size:.65rem;color:var(--accent);letter-spacing:1px;margin-top:2px}
footer{text-align:center;margin-top:28px;font-size:.65rem;color:rgba(122,184,212,.4);letter-spacing:2px}
</style>
</head>
<body>
<div class="bg-waves"><div class="wave"></div><div class="wave"></div><div class="wave"></div></div>
<div class="particles" id="pts"></div>
<div class="wrap">
  <header>
    <div class="logo-ring">&#x1F30A;</div>
    <h1>STATION RIVIERE</h1>
    <div class="subtitle">TFmini Plus LiDAR &mdash; Surveillance Hydrologique</div>
  </header>
  <div class="status-bar"><span class="dot-live"></span><span>LIVE &mdash; Mise &agrave; jour toutes les 500ms</span></div>
  <div class="hero-card">
    <div class="hero-label">&#x1F4CF; Distance mesur&eacute;e</div>
    <div class="hero-value" id="eau">---</div>
    <div class="hero-unit">CENTIMETRES</div>
    <div class="water-bar-wrap"><div class="water-bar" id="bar" style="width:0%"></div></div>
  </div>
  <div class="cards-grid">
    <div class="card">
      <div class="card-icon">&#x1F50B;</div>
      <div class="card-label">Batterie</div>
      <div class="card-val" id="bat">---</div>
      <div class="card-unit">VOLTS</div>
    </div>
    <div class="card">
      <div class="card-icon">&#x2600;&#xFE0F;</div>
      <div class="card-label">Panneau solaire</div>
      <div class="card-val" id="panneau">---</div>
      <div class="card-unit">AMPERES</div>
    </div>
  </div>
  <footer>PROJET PICO &mdash; ESP32 &mdash; TFmini Plus I2C &mdash; 2026</footer>
</div>
<script>
(function(){
  var c=document.getElementById('pts');
  for(var i=0;i<18;i++){
    var d=document.createElement('div');d.className='dot';
    var s=Math.random()*4+2;
    d.style.cssText='width:'+s+'px;height:'+s+'px;left:'+Math.random()*100+'%;bottom:'+Math.random()*20+'%;animation-duration:'+(Math.random()*12+8)+'s;animation-delay:'+(Math.random()*10)+'s;opacity:0';
    c.appendChild(d);
  }
})();
var MAX_H=1200;
function upd(){
  fetch('/data').then(function(r){return r.text();}).then(function(d){
    var v=d.split(',');
    var bat=v[0]||'---',eau=parseInt(v[1])||0,pan=v[2]||'---';
    document.getElementById('bat').textContent=bat;
    document.getElementById('panneau').textContent=pan;
    document.getElementById('eau').textContent=isNaN(eau)?'---':eau;
    document.getElementById('bar').style.width=Math.min(100,Math.round(eau/MAX_H*100))+'%';
  }).catch(function(){});
}
upd();setInterval(upd,500);
</script>
</body>
</html>'''

# ========= INITIALISATION TIMER =========
print("Démarrage timer capteur...")
timer_sensor = Timer(0)
timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)

# ========= SERVEUR WEB =========
print("Démarrage serveur web...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)
s.setblocking(False)

print("Système prêt.")

# ========= BOUCLE PRINCIPALE =========
while True:

    if mesure_hauteur == 1:
        hauteur = use_data()
        mesure_hauteur = 0

    # Envoi ThingSpeak uniquement si la Station est bien connectée au réseau
    if wlan.isconnected() and (time.time() - last_upload > 15):
        try:
            url = "{}?api_key={}&field1={}".format(THINGSPEAK_URL, THINGSPEAK_WRITE_KEY, hauteur)
            r = urequests.get(url)
            r.close()
            last_upload = time.time()
            print("ThingSpeak OK: {}cm".format(hauteur))
        except Exception as e:
            print("Erreur d'envoi ThingSpeak:", e)

    try:
        conn, addr = s.accept()
        conn.setblocking(True)
        request = conn.recv(1024)
        req = str(request)

        if '/data' in req:
            bat, eau, panneau = read_all_values()
            response = "{},{},{}".format(bat, eau, panneau)
            conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n' + response.encode())
        else:
            conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n' + html_page)

        conn.close()
    except OSError:
        pass
    except Exception as e:
        print("Erreur serveur web:", e)