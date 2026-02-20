import network, machine, time, socket, urandom

print("BOOT - Mesure REPOS 10s...")
time.sleep(10)

print("HOTSPOT ESP32...")
wlan_ap=network.WLAN(network.AP_IF)
wlan_ap.config(essid='ESP32_PICO', password='12')
wlan_ap.active(True)
print("Hotspot actif")

boot_time = time.ticks_ms()
n = 0
last_visit_time = 0
server_start = time.ticks_ms()  # ✅ NOUVEAU : timeout serveur

messages = [
    "Boss du BTS !",
]

def web():
    global n, last_visit_time, server_start
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
    s.settimeout(1.0)  # ✅ TIMEOUT 1s sur accept()
    print("Serveur Actif")
    
    while True:
        # ✅ ARRET SERVEUR après 60s pour mesure WiFi MAX
        if time.ticks_diff(time.ticks_ms(), server_start) > 60000:
            print("Mesure WiFi terminée - Arrêt serveur")
            break
            
        try:
            conn, addr = s.accept()
            print("Connexion:", addr)
        except:
            continue  # Pas de client → on continue
            
        last_visit_time = time.ticks_ms()
        request = conn.recv(1024)
        
        # Compteur...
        if time.ticks_diff(last_visit_time, last_visit_time) > 1000:
            n = n + 1
            if n >= 10000000:
                n = 0
            print("✅ VISITE #", n)
        
        couleurs = ["#FF4444", "#44FF44", "#FFFF44", "#FF44FF", "#44FFFF"]
        couleur = couleurs[n % 5]
        uptime = (time.ticks_ms() - boot_time) // 1000
        msg_index = urandom.getrandbits(8) % len(messages)
        msg = messages[msg_index]
        
        html = """<!DOCTYPE html>
<html><body style='margin:0;background:linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #0f3460 100%);color:white;font-family:Arial;text-align:center;padding:50px;min-height:100vh;'>
<h1 style='font-size:80px;margin:20px 0;text-shadow:2px 2px 4px rgba(0,0,0,0.5);'>Bonjour et Bienvenue sur le site du BTS CIEL</h1>
<h2 style='font-size:60px;margin:10px 0;text-shadow:1px 1px 2px rgba(0,0,0,0.5);'>Projet Pico</h2>
<p style='font-size:45px;color:""" + couleur + """;margin:15px 0;text-shadow:1px 1px 2px rgba(0,0,0,0.5);'>Visites: """ + str(n) + """</p>
<p style='font-size:30px;margin:10px 0;text-shadow:1px 1px 2px rgba(0,0,0,0.3);'>Uptime: """ + str(uptime) + """s</p>
<p style='font-size:38px;color:#00AAFF;margin:15px 0;font-weight:bold;text-shadow:1px 1px 2px rgba(0,0,0,0.5);'>""" + msg + """</p>
<button onclick="location.reload();" style='font-size:30px;padding:22px 45px;background:rgba(255,255,255,0.1);color:white;border:2px solid rgba(255,255,255,0.3);border-radius:15px;cursor:pointer;margin:20px;box-shadow:0 4px 15px rgba(0,0,0,0.3);'>Refresh</button>
</body></html>"""
        
        conn.send('HTTP/1.1 200 OK\n')
        conn.send('Content-Type: text/html\n')
        conn.send('Connection: close\n\n')
        conn.sendall(html)
        conn.close()

print("Lancement...")
web()
print("WiFi actif - Mesure 100mA+ !")
while True:
    pass  # ✅ BOUCLE INFINIE WiFi MAX
