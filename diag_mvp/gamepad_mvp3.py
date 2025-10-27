#!/usr/bin/env python3
import time
import sys
import serial
from serial.serialutil import SerialException
from evdev import InputDevice, ecodes

# --- Configurações ---
EVENT_PATH  = '/dev/input/event4'   # Verificado com 'evtest'
SERIAL_PATH = '/dev/ttyUSB0'        # Porta serial do Arduino
BAUD        = 115200                # Mesma velocidade configurada no Arduino
DEADZONE    = 16                    # 'flat' do seu controle é 15, então usamos 16
SEND_HZ     = 20                    # Frequência de envio de comandos (20x por segundo)

def norm_0_255_to_unit(v):
    """Mapeia um valor de 0-255 para -1.0 a +1.0, com o centro em 128."""
    n = (v - 128.0) / 127.0
    # Garante que o valor esteja estritamente entre -1 e 1
    return max(-1.0, min(1.0, n))

def apply_deadzone(raw_value):
    """Retorna 128 (centro) se o valor estiver dentro da deadzone."""
    return 128 if abs(raw_value - 128) <= DEADZONE else raw_value

def clamp255(x):
    """Limita um valor ao intervalo de -255 a 255 para envio aos motores."""
    return int(max(-255, min(255, x)))

def main():
    # 1. Inicializa o Gamepad
    try:
        gp = InputDevice(EVENT_PATH)
        print(f"[OK] Joystick encontrado em {EVENT_PATH}")
    except FileNotFoundError:
        print(f"[ERRO] Dispositivo de evento não encontrado em {EVENT_PATH}", file=sys.stderr)
        print("Verifique o caminho com 'evtest' ou 'ls -l /dev/input/by-id'.", file=sys.stderr)
        sys.exit(1)

    # 2. Inicializa a Comunicação Serial
    try:
        ser = serial.Serial(SERIAL_PATH, BAUD, timeout=0.01)
        print(f"[OK] Porta serial aberta em {SERIAL_PATH} @ {BAUD} bps")
    except SerialException as e:
        print(f"[ERRO] Falha ao abrir a porta serial {SERIAL_PATH}: {e}", file=sys.stderr)
        print("Verifique se o Arduino está conectado e se nenhum outro programa (como o monitor serial) está usando a porta.", file=sys.stderr)
        sys.exit(1)

    # Variáveis de estado
    ax_x = 128  # Eixo X (esquerda/direita), 128 é o centro
    ax_y = 128  # Eixo Y (frente/trás), 128 é o centro
    ser_buf = b""
    last_tx_time = 0.0
    send_period = 1.0 / SEND_HZ

    print(f"[INFO] Enviando comandos a cada {int(send_period * 1000)} ms. Imprimindo diagnóstico do Arduino.")
    print("-" * 30)

    try:
        while True:
            # --- TAREFA 1: Ler e imprimir dados do Arduino (Não bloqueante) ---
            try:
                if ser.in_waiting > 0:
                    ser_buf += ser.read(ser.in_waiting)
                    while b'\n' in ser_buf:
                        line, ser_buf = ser_buf.split(b'\n', 1)
                        # Imprime a linha decodificada recebida do Arduino
                        print(line.decode(errors='replace').strip())
            except SerialException:
                # Lida com uma possível desconexão do Arduino
                print("[AVISO] Erro de comunicação serial. Tentando continuar...", file=sys.stderr)
                time.sleep(1)

            # --- TAREFA 2: Ler eventos do Gamepad (Não bloqueante) ---
            # Drena todos os eventos na fila sem esperar por novos
            event = gp.read_one()
            while event:
                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_X:
                        ax_x = apply_deadzone(event.value)
                    elif event.code == ecodes.ABS_Y:
                        ax_y = apply_deadzone(event.value)
                event = gp.read_one()

            # --- TAREFA 3: Enviar comandos para o Arduino (Controlado por tempo) ---
            current_time = time.time()
            if current_time - last_tx_time >= send_period:
                # Normaliza os eixos para o cálculo de direção
                vx = norm_0_255_to_unit(ax_x)
                vy = -norm_0_255_to_unit(ax_y)  # Inverte Y para que "para frente" seja positivo

                # Mixagem diferencial para controle estilo "tanque"
                # L e R são as velocidades para os motores esquerdo e direito
                L = clamp255(255 * (vy - vx))
                R = clamp255(255 * (vy + vx))

                # Monta e envia o comando pela serial
                command = f"V {L} {R}\n"
                try:
                    ser.write(command.encode())
                except SerialException:
                    pass # Evita travar se o Arduino desconectar
                
                last_tx_time = current_time

            # Pequena pausa para evitar uso de 100% da CPU
            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\n[INFO] Encerrando o programa...")
    finally:
        # Garante que a porta serial seja fechada ao sair
        if 'ser' in locals() and ser.is_open:
            # Envia um último comando para parar os motores
            ser.write(b"V 0 0\n")
            ser.close()
            print("[OK] Motores parados e porta serial fechada.")

if __name__ == "__main__":
    main()
