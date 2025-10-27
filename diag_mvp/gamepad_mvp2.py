#!/usr/bin/env python3
import sys, time, threading, argparse
import serial
from evdev import InputDevice, ecodes

# ===== ajustes rápidos =====
DEFAULT_SER  = "/dev/ttyUSB0"
DEFAULT_JS   = "/dev/input/by-id/usb-Zikway_HID_gamepad-event-joystick"  # seu symlink
BAUD         = 115200
SEND_HZ      = 20.0      # taxa de envio de comandos ao Arduino
DEADZONE     = 0.08      # zona morta nos eixos
MAX_PWM      = 255

# Eixos do seu controle (ver evtest):
AXIS_X = ecodes.ABS_X   # 0 .. 255  (stick esquerdo X)
AXIS_Y = ecodes.ABS_Y   # 0 .. 255  (stick esquerdo Y)
# Botão deadman opcional (R1/TL)
DEADMAN_KEY = ecodes.BTN_TL   # ou None para desativar

def scale_0_255_to_unit(v):
    # 0..255 -> -1..+1 com 128 ~ centro
    return max(-1.0, min(1.0, (v - 128) / 127.0))

def apply_deadzone(x):
    return 0.0 if abs(x) < DEADZONE else x

class Teleop:
    def __init__(self, ser_path, js_path):
        self.ser_path = ser_path
        self.js_path = js_path
        self.ser = None
        self.js = None
        self.ax = 0.0
        self.ay = 0.0
        self.deadman = (DEADMAN_KEY is None)  # se não configurar, fica sempre "ativo"
        self.running = True

    def open_serial(self):
        self.ser = serial.Serial(self.ser_path, BAUD, timeout=0.1)

    def open_joystick(self):
        self.js = InputDevice(self.js_path)

    def reader_serial(self):
        """Lê linhas da serial e imprime exatamente uma linha por linha (como o monitor)."""
        while self.running:
            try:
                line = self.ser.readline()
                if line:
                    # imprime já em uma linha, sem adicionar coisas
                    sys.stdout.write(line.decode(errors='ignore').rstrip() + "\n")
                    sys.stdout.flush()
            except Exception as e:
                sys.stderr.write(f"[serial] erro: {e}\n")
                time.sleep(0.2)

    def writer_joystick(self):
        """Lê eventos do controle e envia 'V L R\\n' periodicamente."""
        last_send = 0.0
        for ev in self.js.read_loop():
            if not self.running:
                break

            if ev.type == ecodes.EV_ABS:
                if ev.code == AXIS_X:
                    self.ax = apply_deadzone(scale_0_255_to_unit(ev.value))
                elif ev.code == AXIS_Y:
                    # Y invertido (pra frente positivo)
                    self.ay = apply_deadzone(-scale_0_255_to_unit(ev.value))

            elif ev.type == ecodes.EV_KEY and DEADMAN_KEY is not None:
                if ev.code == DEADMAN_KEY:
                    self.deadman = (ev.value == 1)

            # rate-limit envio
            now = time.time()
            if (now - last_send) >= (1.0 / SEND_HZ):
                v = self.ay
                w = self.ax
                L = int(max(-MAX_PWM, min(MAX_PWM, MAX_PWM * (v - w))))
                R = int(max(-MAX_PWM, min(MAX_PWM, MAX_PWM * (v + w))))
                if not self.deadman:
                    L = 0
                    R = 0
                try:
                    self.ser.write(f"V {L} {R}\n".encode())
                except Exception as e:
                    sys.stderr.write(f"[serial write] erro: {e}\n")
                last_send = now

    def run(self):
        self.open_serial()
        self.open_joystick()
        t = threading.Thread(target=self.reader_serial, daemon=True)
        t.start()
        try:
            self.writer_joystick()
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            time.sleep(0.1)
            try: self.ser.close()
            except: pass

def main():
    ap = argparse.ArgumentParser(description="Teleop + monitor serial (uma linha por mensagem do Arduino)")
    ap.add_argument("--serial", "-s", default=DEFAULT_SER, help="porta serial (default: /dev/ttyUSB0)")
    ap.add_argument("--js", "-j", default=DEFAULT_JS, help="device de evento do joystick")
    args = ap.parse_args()

    teleop = Teleop(args.serial, args.js)
    teleop.run()

if __name__ == "__main__":
    main()
