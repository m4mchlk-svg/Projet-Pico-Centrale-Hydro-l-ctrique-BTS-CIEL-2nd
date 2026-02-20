import network, time

print("BOOT - Mesure REPOS 10s...")
time.sleep(10)

print("HOTSPOT ESP32 100mA+...")
wlan = network.WLAN(network.AP_IF)
wlan.active(True)
wlan.config(essid='ESP32_PICO', password='12345678')

# ✅ FORCE WiFi FULL POWER
wlan.config(pm=0x8000)  # Power Management OFF !
print("WiFi FULL POWER:", wlan.ifconfig())

while True:
    pass  # CPU 100% → MAX conso
