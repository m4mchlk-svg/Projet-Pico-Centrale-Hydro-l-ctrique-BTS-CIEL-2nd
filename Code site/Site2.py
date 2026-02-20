import network, time

print("BOOT - Mesure REPOS 10s...")
time.sleep(10)

print("HOTSPOT ESP32 FULL POWER...")
wlan = network.WLAN(network.AP_IF)

# ✅ ORDRE CRITIQUE : config D'ABORD, active APRÈS
wlan.config(essid='ESP32_PICO', password='12345678')
wlan.config(channel=1, max_clients=4)  # ✅ FORCE stabilité AP
wlan.active(True)

print("Attente WiFi FULL...")
time.sleep(5)  # ✅ 5s CRITIQUE pour FULL POWER

print("IP:", wlan.ifconfig())
print("WiFi FULL 100mA+ - Mesure OK !")

while True:
    time.sleep_ms(100)  # CPU actif
