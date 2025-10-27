#!/usr/bin/env python3
import time, sys
import serial
from serial.serialutil import SerialException
from evdev import InputDevice, ecodes

EVENT_PATH  = '/dev/input/event4'   # do seu evtest
SERIAL_PATH = '/dev/ttyUSB0'
BAUD        = 115200
DEADZONE    = 16        # seu ABS tem flat 15 → use 16
SEND_HZ     = 20        # envia 20x/seg (~50 ms)

def norm_0_255_to_unit(v):
    # mapeia 0..255 -> -1..+1 com centro em 128
    n = (v - 128.0) / 127.0
    if n >  1: n =  1
    if n < -1: n = -1
    return n

def apply_deadzone(raw):
    if abs(raw - 128) <= DEADZONE:
        return 128
    return raw

def clamp255(x):
    if x > 255: return 255
    if x < -255: return -255
    return int(x)

def main():
    # abre gamepad explicitamente no event4
    gp = InputDevice(EVENT_PATH)

    # abre serial do Arduino (sem monitor externo aberto)
    try:
        ser = serial.Serial(SERIAL_PATH, BAUD, timeout=0.01)
    except SerialException as e:
        print(f"[ERRO] Não consegui abrir {SERIAL_PATH}: {e}", file=sys.stderr)
        print("Feche o processo que está usando a porta (ex.: 'pkill -f \"arduino-cli monitor\"').", file=sys.stderr)
        sys.exit(1)

    ax_x = 128
    ax_y = 128
    last_tx = 0.0
    ser_buf = b""

    # loop principal: lê eventos do gamepad; a cada ~50ms,
    # 1) drena e imprime linhas da SERIAL,
    # 2) envia V L R e imprime a linha enviada.
    for ev in gp.read_loop():
        if ev.type == ecodes.EV_ABS:
            if ev.code == ecodes.ABS_X:
                ax_x = apply_deadzone(ev.value)
            elif ev.code == ecodes.ABS_Y:
                ax_y = apply_deadzone(ev.value)

        now = time.time()
        if now - last_tx >= (1.0 / SEND_HZ):
            # 1) ler TUDO que tiver chegado da serial e imprimir linha-a-linha
            try:
                available = ser.in_waiting
                if available:
                    ser_buf += ser.read(available)
                    while b'\n' in ser_buf:
                        line, ser_buf = ser_buf.split(b'\n', 1)
                        print(line.decode(errors='replace'))
            except SerialException:
                pass

            # 2) calcular L/R e enviar
            vx = norm_0_255_to_unit(ax_x)
            vy = -norm_0_255_to_unit(ax_y)  # frente positiva
            L  = clamp255(255 * (vy - vx))
            R  = clamp255(255 * (vy + vx))
            out = f"V {L} {R}\n"
            ser.write(out.encode())
            print(out.strip())  # imprime após as linhas da serial
            last_tx = now

if __name__ == "__main__":
    main()
