import network
import socket
import urequests
import time
from machine import I2C, Pin, Timer

# ========= CONFIGURATION I2C (TFmini Plus) =========
i2c = I2C(0, sda=Pin(23), scl=Pin(25), freq=400000)

dist1, dist2, dist3, hauteur = 0, 0, 0, 0 		# Stockage des 3 dernières valeurs et de la moyenne
error, count = 0, 0 							# Valeurs des erreurs et du compteur
max_error, max_marge = 2, 10   					# Nombre d'erreurs tolérées et variation maximale autorisée (en cm) entre deux mesures
timer_period_ms, error_period_ms = 3000, 1000	# Fréquence de mesure normale / erreur détectée
att_moy = 100									# Attente en ms entre chaque distance mesurée
mesure_hauteur = 0
prep = 0
calibr = (timer_period_ms*(prep+1))/1000
timer_sensor = None  # Sera initialisé plus bas

def get_firmware_version(addr):
    """
        Cette fonction permet de récupérer la version du capteur détecté.
        On envoie d'abord la commande à l'adresse du capteur pour récupérer sa version puis on lit sa réponse.
        On formate ensuite les octets qui nous intéresse dans une variable.
        
        Args:
            addr (string): Adresse du capteur
            
        Returns:
            string: Version du capteur trouvée
    """
    try:
        # Commande version du firmware
        i2c.writeto(addr, b'\x5a\x04\x01\x5f')
        time.sleep_ms(20) # Temps d'attente ajusté pour éviter le gel du bus
        
        # Lecture 7 octets de réponse
        res = i2c.readfrom(addr, 7)
        
        # Vérification trame reçue (7 octets, octet 0 entête 0x5A, octet 2 confirmation ID commande 0x01)
        if len(res) >= 7 and res[0] == 0x5a and res[2] == 0x01:
            # Formatage version
            return "V{}.{}.{}".format(res[3], res[4], res[5])
    except:
        pass
    
    return "Inconnue"


print("Recherche de capteurs I2C...")
# Scan bus I2C adresses matérielles connectées
devices = i2c.scan()
sensor_info = {} 								# Dictionnaire stock adresse et version capteur(s)

if devices:
    for d in devices:
        version = get_firmware_version(d)
        sensor_info[d] = version
        print("Trouvé : Adresse {} | Version : {}".format(hex(d), version))
    
    # Première adresse trouvée = capteur principal
    TFMINI_ADDR = devices[0]
else:
    # Echec scan = adresse par défaut (0x10 pour le TFMini Plus en mode I2C)
    print("\nAucun capteur détecté. Utilisation adresse par défaut 0x10")
    TFMINI_ADDR = 0x10
    sensor_info[0x10] = "Inconnue"

# ========= THINGSPEAK =========
THINGSPEAK_WRITE_KEY = "Z5R36BOW4YA29JFK"
THINGSPEAK_URL       = "http://api.thingspeak.com/update"
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
time.sleep_ms(500)
while wlan.isconnected() == False :
    print("Tentative de connexion à la borne...")
    wlan.connect('BTS_SN_IoT', 'BOU_BTS_SN')
    time.sleep_ms(500)


# ========= FONCTIONS CAPTEUR =========
def get_distance():
    """
        Cette fonction permet de récupérer la distance mesurée par un capteur.
        La commande de lecture de distance est envoyée au capteur et sa réponse est stocker dans la variable data.
        On vérifie qu'elle soit au bon format puis on récupère les octets indiquant la distance.
        Un correctif est appliqué sur la distance mais n'est pas obligatoire sur tous les capteurs.
        
        Args:
            ...
            
        Returns:
            int: Distance mesurée en cm
    """
    try:
        # Commande demande de mesure de distance
        i2c.writeto(TFMINI_ADDR, b'\x5a\x05\x00\x01\x60')
        time.sleep_ms(15) # Laisse le temps au capteur de préparer la trame de données
        
        # Lecture 9 octets de données de mesure
        data = i2c.readfrom(TFMINI_ADDR, 9)
        
        # Vérification protocole standard TFMini
        if len(data) >= 9 and data[0] == 0x59 and data[1] == 0x59:
            # Distance codée sur 2 octets
            # Octet 2 (poids faible) + octet 3 (poids fort) décalé de 8 bits vers la gauche
            distance = data[2] + (data[3] << 8)
            distance = round(distance * 1.05)
            return distance
    except:
        print("\nErreur dans la récupération de la mesure.")
        return None
    
    return None


def use_data():
    """
        Cette fonction affiche et gère les mesures.
        On initialise toutes nos variables à la première mesure pour éviter une erreur en début de boucle.
        On vérifie si la distance est prise en compte par le capteur et on compare la moyenne avec la précédente.
        Une fois acceptée, on peut calculer une moyenne à partir de trois valeurs successives puis on affiche les informations.
        Si la différence entre les deux dernières moyennes est plus élevée que la marge configurée, une erreur est comptée.
        Trop d'erreur de suite indique qu'il s'agit d'une valeur correcte.
        
        Args:
            timer (timer): Timer par interruption
            
        Returns:
            ...
    """
    global dist1, dist2, dist3, hauteur, error, count, att_moy, prep
    mesure = get_distance()
        
    if mesure is not None:
        if dist1 == 0:
            hauteur = mesure
            dist1 = mesure
            dist2 = mesure
            dist3 = mesure
        # Vérification mesure physiquement possible
        if 10 < mesure < 1200:
            
            # Accepte la valeur si écart avec mesure précédente correct et erreurs maximales non atteintes
            if abs(mesure - hauteur) <= max_marge:
                
                # Prise de mesure décalée pour calculer une moyenne
                dist3 = mesure
                
                time.sleep_ms(att_moy)
                mesure = get_distance()
                # Sécurité au cas où une mesure intermédiaire renverrait None
                if mesure is None: mesure = dist3
                dist2 = mesure
                
                time.sleep_ms(att_moy)
                mesure = get_distance()
                if mesure is None: mesure = dist2
                dist1 = mesure
                
                hauteur = round((dist1 + dist2 + dist3)/3)
                
                # Conversion en 2 octets
                lsb = hauteur & 0xFF
                msb = (hauteur >> 8) & 0xFF
                octets_distance = bytes([lsb, msb])
                
                # Réinitialise le compteur d'erreurs car valeur valide
                error = 0
                
                # Incrémente le compteur global
                count += 1
                
                # Formatage pour l'affichage
                addr_h = hex(TFMINI_ADDR)
                ver = sensor_info.get(TFMINI_ADDR, "N/A")
                
                # Affiche les résultats
                if count > prep:
                    print("[Adresse: {} | Version: {}]\nDistance n°{}: {} cm\nFormat bytes: {}\n\n".format(addr_h, ver, count, hauteur, octets_distance))
                
                # Après réinitialisation erreurs: retour au cycle normal
                if error == 0:
                    timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)
                        
                return hauteur
            
            else:
                # Variance trop élevée = ignorée + erreur + temps de mesure raccourci
                timer_sensor.init(mode=Timer.PERIODIC, period=error_period_ms, callback=interrupt_hauteur)
                error += 1
                if count > prep:
                    print(f"{error} erreur(s)\n")
            
                if error > max_error:
                    # Erreurs maximales atteintes = réinitialisation des variables + reprise du cycle normal
                    if count > prep:
                        print("Erreurs multiples, recalibrage...\n\n")
                    error = 0
                    hauteur = mesure
                    dist1 = mesure
                    dist2 = mesure
                    dist3 = mesure
                    timer_sensor.init(mode=Timer.PERIODIC, period=timer_period_ms, callback=interrupt_hauteur)
                    
                return hauteur
            
        else:
            # Donnée lue mais en dehors des limites du capteur
            count += 1
            print("[Adresse: {}]\nHors limite ({} cm)\n\n".format(hex(TFMINI_ADDR), mesure))
            
            return hauteur


def interrupt_hauteur(timer):
    global mesure_hauteur
    mesure_hauteur = 1
    return mesure_hauteur


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
print("Démarrage du programme de mesure...")
print("Mesures de calibration en cours... ({} s)\n\n".format(calibr))
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
        print(hauteur)
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