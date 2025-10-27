#!/usr/bin/env python3
# gamepad_tx_fixedrate_buzina.py
# Envia "V L R" em taxa fixa e "H 0/1" conforme botão do controle. Imprime o que foi enviado.

import time, sys
import serial
from serial.serialutil import SerialException
from evdev import InputDevice, ecodes

EVENT_PATH  = '/dev/input/event4'   # ajuste se necessário
SERIAL_PATH = '/dev/ttyUSB0'
BAUD        = 115200
DEADZONE    = 16
SEND_HZ     = 20

BTN_HORN = ecodes.BTN_TL  # mapeie aqui o botão da buzina (p.ex. BTN_SOUTH, BTN_TR, etc.)

def norm_0_255_to_unit(v):
    n = (v - 128.0) / 127.0
    if n >  1: n =  1
    if n < -1: n = -1
    return n

def apply_deadzone(raw):
    return 128 if abs(raw - 128) <= DEADZONE else raw

def clamp255(x):
    if x > 255: return 255
    if x < -255: return -255
    return int(x)

def main():
    try:
        dev = InputDevice(EVENT_PATH)
    except Exception as e:
        print(f"[ERRO] Abrindo {EVENT_PATH}: {e}", file=sys.stderr); sys.exit(1)

    try:
        ser = serial.Serial(SERIAL_PATH, BAUD, timeout=0.01)
    except SerialException as e:
        print(f"[ERRO] Porta {SERIAL_PATH}: {e}", file=sys.stderr); sys.exit(1)

    period = 1.0 / SEND_HZ
    next_t = time.time()

    while True:
        # lê estado atual dos eixos
        ax_x = dev.absinfo(ecodes.ABS_X).value
        ax_y = dev.absinfo(ecodes.ABS_Y).value

        ax_x = apply_deadzone(ax_x)
        ax_y = apply_deadzone(ax_y)

        vx = norm_0_255_to_unit(ax_x)
        vy = -norm_0_255_to_unit(ax_y)  # frente positiva

        L  = clamp255(255 * (vy - vx))
        R  = clamp255(255 * (vy + vx))

        # estado do botão (buzina)
        try:
            keys = dev.active_keys()
            horn = 1 if BTN_HORN in keys else 0
        except Exception:
            horn = 0

        line_v = f"V {L} {R}\n"
        line_h = f"H {horn}\n"
        ser.write(line_v.encode())
        ser.write(line_h.encode())
        print(line_v.strip(), "|", line_h.strip())

        # temporização fixa
        now = time.time()
        next_t += period
        sleep_t = next_t - now
        if sleep_t < 0:
            next_t = now
        else:
            time.sleep(sleep_t)

if __name__ == "__main__":
    main()
