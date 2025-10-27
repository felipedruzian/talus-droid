#!/usr/bin/env python3
import time
from evdev import InputDevice, ecodes

JS_DEV = '/dev/input/js0'
AXIS_X, AXIS_Y = 0, 1
def scale_axis(v): return (v/32767.0) if v>=0 else (v/32768.0)
def clamp255(x): return max(-255, min(255, int(x)))

def main():
    js = InputDevice(JS_DEV)
    ax=ay=0.0
    last=0
    for ev in js.read_loop():
        if ev.type == ecodes.EV_ABS:
            if ev.code == AXIS_X: ax = scale_axis(ev.value)
            elif ev.code == AXIS_Y: ay = -scale_axis(ev.value)
        now=time.time()
        if now-last>=0.1:
            L = clamp255(255*(ay - ax))
            R = clamp255(255*(ay + ax))
            print(f"SEND: V {L} {R}")
            last=now

if __name__ == "__main__":
    main()
