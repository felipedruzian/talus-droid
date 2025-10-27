#!/usr/bin/env python3
from evdev import InputDevice, ecodes
import time, sys

EVENT_PATH = '/dev/input/event4'  # ajuste se precisar
DEADZONE = 16                     # o "Flat" do evtest estava 15; use 16

def norm_0_255_to_unit(v):
    # mapeia 0..255 -> -1..+1 com centro em 128
    n = (v - 128.0) / 127.0
    if n > 1: n = 1
    if n < -1: n = -1
    return n

def apply_deadzone(raw):
    # raw é 0..255; aplica deadzone em torno de 128
    if abs(raw - 128) <= DEADZONE:
        return 128
    return raw

def main():
    dev = InputDevice(EVENT_PATH)
    ax_x = 128  # ABS_X
    ax_y = 128  # ABS_Y
    last = 0.0

    for ev in dev.read_loop():
        if ev.type == ecodes.EV_ABS:
            if ev.code == ecodes.ABS_X:
                ax_x = apply_deadzone(ev.value)
            elif ev.code == ecodes.ABS_Y:
                ax_y = apply_deadzone(ev.value)
        now = time.time()
        if now - last >= 0.10:
            vx = norm_0_255_to_unit(ax_x)
            vy = -norm_0_255_to_unit(ax_y)  # Y invertido p/ frente positiva
            sys.stdout.write(f"LX={vx:+.2f} LY={vy:+.2f}\r")
            sys.stdout.flush()
            last = now

if __name__ == "__main__":
    main()
