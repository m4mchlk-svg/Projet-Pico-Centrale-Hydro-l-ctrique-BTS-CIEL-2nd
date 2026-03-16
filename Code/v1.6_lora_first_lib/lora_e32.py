from machine import UART, Pin
import time

class LoRaE32:
    def __init__(self, uart_id=2, tx=17, rx=16, m0_pin=19, m1_pin=18, aux_pin=22, debug=True):
        self.uart = UART(uart_id, baudrate=9600, tx=tx, rx=rx, timeout=200)
        self.m0 = Pin(m0_pin, Pin.OUT)
        self.m1 = Pin(m1_pin, Pin.OUT)
        self.aux = Pin(aux_pin, Pin.IN)
        self.debug = debug

    def wait_aux(self):
        while self.aux.value() == 0:
            time.sleep_ms(1)
        time.sleep_ms(2)

    def set_mode(self, mode):
        self.wait_aux()
        if mode == 0:     # NORMAL
            self.m1.value(0); self.m0.value(0)
        elif mode == 1:   # WAKE-UP
            self.m1.value(0); self.m0.value(1)
        elif mode == 2:   # POWER-SAVING
            self.m1.value(1); self.m0.value(0)
        elif mode == 3:   # SLEEP (CONFIG)
            self.m1.value(1); self.m0.value(1)
        
        time.sleep_ms(20)
        self.wait_aux()
        if self.debug:
            print(f"Mode {mode} active")

    def setup_fixed_transmission(self, addr_h, addr_l, channel):
        self.set_mode(3)
        # C0 + ADDR_H + ADDR_L + 1A (9600bps) + CHAN + C4 (Fixe)
        config_cmd = bytes([0xC0, addr_h, addr_l, 0x1A, channel, 0xC4])
        if self.debug:
            print(f"Envoi configuration fixe : {config_cmd.hex().upper()}")
        self.uart.write(config_cmd)
        time.sleep_ms(200)
        if self.uart.any():
            response = self.uart.read()
            if self.debug:
                print(f"Confirmation module : {response.hex().upper()}")
        self.set_mode(0)

    def send_point_to_point_v(self, target_h, target_l, target_chan, message):
        self.wait_aux()
        header = bytes([target_h, target_l, target_chan])
        message_txt = str(message)
        self.uart.write(header + " " + message_txt)
        if self.debug:
            print(f"Envoyé à {target_h:02x}{target_l:02x} sur canal {target_chan}")

    def send_point_to_point_txt(self, target_h, target_l, target_chan, message):
        self.wait_aux()
        header = bytes([target_h, target_l, target_chan])
        self.uart.write(header + message.encode('utf-8'))
        if self.debug:
            print(f"Envoyé à {target_h:02x}{target_l:02x} sur canal {target_chan}")

    def send_broadcast(self, target_chan, message):
        self.wait_aux()
        header = bytes([0xFF, 0xFF, target_chan])
        self.uart.write(header + message.encode('utf-8'))
        if self.debug:
            print(f"Broadcast envoyé sur canal {target_chan}")

    def receive_txt(self):
        if self.uart.any():
            data = self.uart.read()
            try:
                if self.debug:
                    print(f"Message reçu : {data.decode('utf-8')}")
                return data.decode('utf-8')
            except:
                if self.debug:
                    print(f"Message reçu (HEX) : {data.hex()}")
                return data
        return None