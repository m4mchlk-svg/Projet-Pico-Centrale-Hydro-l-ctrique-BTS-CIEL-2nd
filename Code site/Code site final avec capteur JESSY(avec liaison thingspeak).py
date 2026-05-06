import network
import socket
import urequests
import time
from machine import ADC, Pin, SoftI2C, Timer

# ========= CONFIGURATION CAPTEUR I2C (MB7040) =========
i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=50000)
MB7040_ADDR = 0x70
CMD_RANGE = 0x51

# Variables globales capteur
dist1, dist2, dist3, moyenne, error, count = 0, 0, 0, 0, 0, 0
max_error, max_marge = 2, 10

# ========= CAPTEURS ADC =========
adc_bat     = ADC(Pin(34))
adc_panneau = ADC(Pin(35))

# ========= THINGSPEAK =========
THINGSPEAK_WRITE_KEY = "Z5R36BOW4YA29JFK"
THINGSPEAK_URL       = "https://api.thingspeak.com/update"
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
    eau     = moyenne
    bat     = "----"
    panneau = "----"
    return bat, eau, panneau

# ========= PAGE HTML (thème rivière, optimisée ESP32) =========
html_page = b'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MB7040 | Station Riviere</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Exo+2:wght@300;400;600&display=swap');
:root{
  --deep:#062a3a;--mid:#0a4a6b;--light:#1a7fa8;--accent:#00d4ff;
  --surface:rgba(10,74,107,0.45);--glass:rgba(255,255,255,0.07);
  --text:#d0f0ff;--muted:#7ab8d4;
}
*{margin:0;padding:0;box-sizing:border-box}
body{
  min-height:100vh;background:var(--deep);
  font-family:'Exo 2',sans-serif;color:var(--text);
  overflow-x:hidden;position:relative;
}

/* ---- fond animé ---- */
.bg-waves{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none}
.wave{position:absolute;width:200%;height:200%;border-radius:40%;opacity:.08;animation:spin linear infinite}
.wave:nth-child(1){background:radial-gradient(ellipse,#00d4ff 0%,transparent 70%);top:-60%;left:-50%;animation-duration:18s}
.wave:nth-child(2){background:radial-gradient(ellipse,#0a9fd4 0%,transparent 70%);top:-40%;left:-30%;animation-duration:24s;animation-direction:reverse;opacity:.06}
.wave:nth-child(3){background:radial-gradient(ellipse,#062a3a 0%,#1a7fa8 60%,transparent 80%);top:20%;left:-60%;animation-duration:30s;opacity:.12}
@keyframes spin{to{transform:rotate(360deg)}}

/* ---- particules ---- */
.particles{position:fixed;inset:0;z-index:0;pointer-events:none}
.dot{position:absolute;border-radius:50%;background:var(--accent);animation:rise linear infinite;opacity:0}
@keyframes rise{0%{transform:translateY(0) scale(1);opacity:.6}100%{transform:translateY(-100vh) scale(0);opacity:0}}

/* ---- layout ---- */
.wrap{position:relative;z-index:1;max-width:480px;margin:0 auto;padding:24px 16px 40px}

/* ---- header ---- */
header{text-align:center;margin-bottom:32px}
.logo-ring{
  width:72px;height:72px;border-radius:50%;
  border:2px solid var(--accent);
  display:flex;align-items:center;justify-content:center;
  margin:0 auto 14px;
  box-shadow:0 0 24px rgba(0,212,255,.35);
  animation:pulse 3s ease-in-out infinite;
  font-size:28px;
}
@keyframes pulse{0%,100%{box-shadow:0 0 24px rgba(0,212,255,.35)}50%{box-shadow:0 0 42px rgba(0,212,255,.65)}}
h1{font-family:'Orbitron',sans-serif;font-size:1.35rem;letter-spacing:3px;color:var(--accent);text-shadow:0 0 18px rgba(0,212,255,.5)}
.subtitle{font-size:.78rem;color:var(--muted);letter-spacing:2px;margin-top:4px;text-transform:uppercase}

/* ---- status bar ---- */
.status-bar{
  display:flex;align-items:center;gap:8px;
  background:var(--glass);border:1px solid rgba(0,212,255,.15);
  border-radius:30px;padding:7px 16px;margin-bottom:24px;
  font-size:.75rem;color:var(--muted);letter-spacing:1px;
}
.dot-live{width:7px;height:7px;border-radius:50%;background:#00ff88;
  box-shadow:0 0 8px #00ff88;animation:blink 1.4s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

/* ---- hero card (distance eau) ---- */
.hero-card{
  background:linear-gradient(135deg,rgba(0,212,255,.12),rgba(10,74,107,.6));
  border:1px solid rgba(0,212,255,.3);border-radius:20px;
  padding:28px 24px;margin-bottom:16px;text-align:center;
  position:relative;overflow:hidden;
  box-shadow:0 8px 32px rgba(0,0,0,.4),inset 0 1px 0 rgba(255,255,255,.08);
}
.hero-card::before{
  content:'';position:absolute;inset:0;
  background:repeating-linear-gradient(90deg,transparent,transparent 19px,rgba(0,212,255,.04) 20px),
             repeating-linear-gradient(0deg,transparent,transparent 19px,rgba(0,212,255,.04) 20px);
}
.hero-label{font-size:.7rem;letter-spacing:3px;text-transform:uppercase;color:var(--muted);margin-bottom:8px}
.hero-value{
  font-family:'Orbitron',sans-serif;font-size:4rem;font-weight:700;
  color:#fff;line-height:1;text-shadow:0 0 30px rgba(0,212,255,.7);
  animation:countIn .4s ease;
}
@keyframes countIn{from{transform:scale(1.08);opacity:.5}to{transform:scale(1);opacity:1}}
.hero-unit{font-size:.95rem;color:var(--accent);letter-spacing:2px;margin-top:6px}
.water-bar-wrap{margin-top:18px;background:rgba(0,0,0,.3);border-radius:30px;height:10px;overflow:hidden}
.water-bar{height:100%;border-radius:30px;
  background:linear-gradient(90deg,#0a9fd4,#00d4ff);
  transition:width 1s ease;box-shadow:0 0 12px rgba(0,212,255,.6)}

/* ---- mini cartes ---- */
.cards-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
.card{
  background:var(--surface);
  border:1px solid rgba(255,255,255,.08);border-radius:16px;
  padding:18px 14px;position:relative;overflow:hidden;
  transition:transform .2s,border-color .2s;
  box-shadow:0 4px 20px rgba(0,0,0,.3);
}
.card:active{transform:scale(.97)}
.card::after{
  content:'';position:absolute;top:-30px;right:-30px;
  width:80px;height:80px;border-radius:50%;
  background:radial-gradient(circle,rgba(0,212,255,.1),transparent);
}
.card-icon{font-size:1.5rem;margin-bottom:8px}
.card-label{font-size:.65rem;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:6px}
.card-val{font-family:'Orbitron',sans-serif;font-size:1.6rem;font-weight:700;color:#fff}
.card-unit{font-size:.65rem;color:var(--accent);letter-spacing:1px;margin-top:2px}

/* ---- footer ---- */
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
    <div class="subtitle">Capteur MB7040 &mdash; Surveillance Hydrologique</div>
  </header>

  <div class="status-bar">
    <span class="dot-live"></span>
    <span>LIVE &mdash; Mise &agrave; jour toutes les 500ms</span>
  </div>

  <!-- Hero : Hauteur eau -->
  <div class="hero-card">
    <div class="hero-label">&#x1F4CF; Hauteur d&apos;eau mesur&eacute;e</div>
    <div class="hero-value" id="eau">---</div>
    <div class="hero-unit">CENTIMETRES</div>
    <div class="water-bar-wrap">
      <div class="water-bar" id="bar" style="width:0%"></div>
    </div>
  </div>

  <!-- Mini cartes -->
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

  <footer>PROJET PICO &mdash; ESP32 &mdash; 2026</footer>
</div>

<script>
// Particules flottantes
(function(){
  var c=document.getElementById('pts');
  for(var i=0;i<18;i++){
    var d=document.createElement('div');
    d.className='dot';
    var s=Math.random()*4+2;
    d.style.cssText='width:'+s+'px;height:'+s+'px;left:'+Math.random()*100+'%;bottom:'+Math.random()*20+'%;animation-duration:'+(Math.random()*12+8)+'s;animation-delay:'+(Math.random()*10)+'s;opacity:0';
    c.appendChild(d);
  }
})();

// Mise a jour des donnees
var MAX_H=765;
function upd(){
  fetch('/data').then(function(r){return r.text();}).then(function(d){
    var v=d.split(',');
    var bat=v[0]||'---',eau=parseInt(v[1])||0,pan=v[2]||'---';
    document.getElementById('bat').textContent=bat;
    document.getElementById('panneau').textContent=pan;
    document.getElementById('eau').textContent=isNaN(eau)?'---':eau;
    var pct=Math.min(100,Math.round(eau/MAX_H*100));
    document.getElementById('bar').style.width=pct+'%';
  }).catch(function(){});
}
upd();
setInterval(upd,500);
</script>
</body>
</html>'''

# ========= INITIALISATION =========
devices = i2c.scan()
if MB7040_ADDR not in devices:
    print("ALERTE: Capteur MB7040 non trouve !")

timer_sensor = Timer(1)
timer_sensor.init(mode=Timer.PERIODIC, period=500, callback=update_sensor_data)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)

# ========= BOUCLE PRINCIPALE =========
while True:
    try:
        # ThingSpeak toutes les 15s
        if time.time() - last_upload > 15:
            _, eau, _ = read_all_values()
            try:
                url = "{}?api_key={}&field1={}".format(THINGSPEAK_URL, THINGSPEAK_WRITE_KEY, eau)
                r = urequests.get(url)
                r.close()
                last_upload = time.time()
                print("ThingSpeak OK: {}cm".format(eau))
            except:
                print("Erreur ThingSpeak")

        # Serveur Web
        conn, addr = s.accept()
        request = conn.recv(1024)
        req = str(request)

        if '/data' in req:
            bat, eau, panneau = read_all_values()
            response = "{},{},{}".format(bat, eau, panneau)
            conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n' + response.encode())
        else:
            conn.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n' + html_page)

        conn.close()
    except Exception as e:
        print("Erreur boucle:", e)