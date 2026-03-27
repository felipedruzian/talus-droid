#!/usr/bin/env python3
"""
talus_base_bridge.py — ROS2 Jazzy Bridge para Talus Base
Corrigido: mapeamento de joystick, logs de debug, robustez
"""

import rclpy
import serial
import threading
import time
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy, Imu
from std_msgs.msg import Int32, Bool

class TalusBaseBridge(Node):
    def __init__(self):
        super().__init__('talus_base_bridge')
        
        # ========== PARÂMETROS ==========
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('baseline', 0.19)      # m
        self.declare_parameter('v_max', 0.50)         # m/s → PWM 255
        self.declare_parameter('pwm_max', 255)

        # Mapeamento joystick CORRIGIDO para seu controle
        self.declare_parameter('axis_linear', 1)      # Analog ESQ vertical
        self.declare_parameter('axis_angular', 2)     # Analog DIR horizontal (ERA 3!)
        self.declare_parameter('invert_linear', True) # Inverte eixo linear
        self.declare_parameter('invert_angular', False)
        
        self.declare_parameter('scale_linear', 0.4)   # m/s (reduzido p/ testes)
        self.declare_parameter('scale_angular', 1.2)  # rad/s
        
        self.declare_parameter('enable_button', 6)    # L1 (ERA 4!)
        self.declare_parameter('turbo_button', 7)     # R1 (ERA 5!)
        self.declare_parameter('horn_button', 0)      # X
        
        self.declare_parameter('deadzone', 0.1)       # Zona morta do joystick
        self.declare_parameter('debug', True)         # Logs de debug

        # Carrega parâmetros
        self.port = self.get_parameter('port').value
        self.baud = self.get_parameter('baud').value
        self.baseline = self.get_parameter('baseline').value
        self.v_max = self.get_parameter('v_max').value
        self.pwm_max = self.get_parameter('pwm_max').value

        self.axis_lin = self.get_parameter('axis_linear').value
        self.axis_ang = self.get_parameter('axis_angular').value
        self.inv_lin = self.get_parameter('invert_linear').value
        self.inv_ang = self.get_parameter('invert_angular').value
        
        self.k_lin = self.get_parameter('scale_linear').value
        self.k_ang = self.get_parameter('scale_angular').value
        
        self.btn_en = self.get_parameter('enable_button').value
        self.btn_turbo = self.get_parameter('turbo_button').value
        self.btn_horn = self.get_parameter('horn_button').value
        
        self.deadzone = self.get_parameter('deadzone').value
        self.debug = self.get_parameter('debug').value

        # ========== SERIAL ==========
        self.ser = None
        self._open_serial()

        # ========== ROS INTERFACES ==========
        self.pub_cmd = self.create_publisher(Twist, 'cmd_vel', 10)
        self.pub_imu = self.create_publisher(Imu, 'imu/raw', 10)
        self.pub_l = self.create_publisher(Int32, 'wheel/left_ticks', 10)
        self.pub_r = self.create_publisher(Int32, 'wheel/right_ticks', 10)
        self.pub_horn = self.create_publisher(Bool, 'horn', 10)

        self.sub_cmd = self.create_subscription(Twist, 'cmd_vel', self.on_cmd, 10)
        self.sub_joy = self.create_subscription(Joy, 'joy', self.on_joy, 10)

        # Thread RX
        self.rx_thread = threading.Thread(target=self.rx_loop, daemon=True)
        self.rx_thread.start()

        # Estado
        self.last_joy_time = time.time()
        self.joy_received_count = 0

        self.get_logger().info('🤖 TalusBaseBridge PRONTO!')
        self.get_logger().info(f'   Mapeamento: linear=axis{self.axis_lin}, angular=axis{self.axis_ang}')
        self.get_logger().info(f'   Botões: enable=btn{self.btn_en}, turbo=btn{self.btn_turbo}, horn=btn{self.btn_horn}')

    # ========== SERIAL ==========
    def _open_serial(self):
        """Abre conexão serial com retry"""
        while rclpy.ok():
            try:
                self.ser = serial.Serial(
                    self.port, 
                    baudrate=self.baud, 
                    timeout=0.1,
                    write_timeout=1.0
                )
                self.get_logger().info(f'✓ Serial: {self.port} @ {self.baud}')
                time.sleep(0.3)  # Aguarda boot do Arduino
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                return
            except serial.SerialException as e:
                self.get_logger().warn(f'⚠ Falha serial: {e} — retry em 2s')
                time.sleep(2)

    def _send(self, cmd: str):
        """Envia comando ao Arduino"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.write(cmd.encode('utf-8'))
                if self.debug:
                    self.get_logger().debug(f'TX: {cmd.strip()}')
        except Exception as e:
            self.get_logger().error(f'❌ Erro TX: {e}')

    def rx_loop(self):
        """Thread de recepção serial"""
        while rclpy.ok():
            try:
                if not self.ser or not self.ser.is_open:
                    time.sleep(0.5)
                    continue

                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                if line.startswith('IMU '):
                    parts = line.split()
                    if len(parts) == 7:
                        msg = Imu()
                        msg.header.stamp = self.get_clock().now().to_msg()
                        msg.header.frame_id = 'imu_link'
                        msg.linear_acceleration.x = float(parts[1])
                        msg.linear_acceleration.y = float(parts[2])
                        msg.linear_acceleration.z = float(parts[3])
                        msg.angular_velocity.x = float(parts[4])
                        msg.angular_velocity.y = float(parts[5])
                        msg.angular_velocity.z = float(parts[6])
                        # Covariâncias desconhecidas = -1 (padrão ROS)
                        msg.orientation_covariance[0] = -1.0
                        self.pub_imu.publish(msg)

                elif line.startswith('ENC '):
                    parts = line.split()
                    if len(parts) == 3:
                        ml = Int32(data=int(parts[1]))
                        mr = Int32(data=int(parts[2]))
                        self.pub_l.publish(ml)
                        self.pub_r.publish(mr)

                elif line.startswith('VER ') or line.startswith('OK '):
                    self.get_logger().info(f'Arduino: {line}')

            except serial.SerialException as e:
                self.get_logger().error(f'❌ RX error: {e} — reconnecting')
                time.sleep(1)
                self._open_serial()
            except Exception as e:
                self.get_logger().warn(f'⚠ Parse error: {e} | "{line}"')

    # ========== JOYSTICK → CMD_VEL ==========
    def on_joy(self, joy: Joy):
        """Processa mensagens do joystick"""
        try:
            self.joy_received_count += 1
            self.last_joy_time = time.time()

            # Lê botões com bounds check
            enable = self._get_button(joy, self.btn_en)
            turbo = self._get_button(joy, self.btn_turbo)
            horn = self._get_button(joy, self.btn_horn)

            # Log primeira mensagem
            if self.joy_received_count == 1:
                self.get_logger().info(f'🎮 Joystick conectado! axes={len(joy.axes)}, btns={len(joy.buttons)}')

            # Lê eixos com deadzone
            vx_raw = self._get_axis(joy, self.axis_lin, invert=self.inv_lin)
            wz_raw = self._get_axis(joy, self.axis_ang, invert=self.inv_ang)

            # Aplica escala se habilitado
            vx = 0.0
            wz = 0.0
            if enable:
                scale = 1.5 if turbo else 1.0
                vx = self.k_lin * scale * vx_raw
                wz = self.k_ang * scale * wz_raw

            # Debug periódico
            if self.debug and self.joy_received_count % 10 == 0:
                self.get_logger().info(
                    f'Joy: EN={enable} TU={turbo} | '
                    f'raw=({vx_raw:.2f},{wz_raw:.2f}) → cmd=({vx:.2f},{wz:.2f})'
                )

            # Publica cmd_vel
            tw = Twist()
            tw.linear.x = vx
            tw.angular.z = wz
            self.pub_cmd.publish(tw)

            # Buzina
            self.pub_horn.publish(Bool(data=horn))
            self._send(f'H {1 if horn else 0}\n')

        except Exception as e:
            self.get_logger().error(f'❌ on_joy: {e}', throttle_duration_sec=1.0)

    def _get_button(self, joy: Joy, idx: int) -> bool:
        """Lê botão com bounds check"""
        if 0 <= idx < len(joy.buttons):
            return joy.buttons[idx] == 1
        return False

    def _get_axis(self, joy: Joy, idx: int, invert: bool = False) -> float:
        """Lê eixo com deadzone e inversão"""
        if 0 <= idx < len(joy.axes):
            val = joy.axes[idx]
            if abs(val) < self.deadzone:
                return 0.0
            return -val if invert else val
        return 0.0

    # ========== CMD_VEL → MOTORES ==========
    def on_cmd(self, tw: Twist):
        """Converte cmd_vel em comandos PWM"""
        try:
            v = tw.linear.x
            w = tw.angular.z

            # Cinemática diferencial
            vL = v - w * self.baseline / 2.0
            vR = v + w * self.baseline / 2.0

            # Converte para PWM
            pwm_l = self._vel_to_pwm(vL)
            pwm_r = self._vel_to_pwm(vR)

            # Envia ao Arduino
            self._send(f'V {pwm_l} {pwm_r}\n')

        except Exception as e:
            self.get_logger().error(f'❌ on_cmd: {e}')

    def _vel_to_pwm(self, vel: float) -> int:
        """Converte velocidade (m/s) para PWM (-255..255)"""
        pwm = int((vel / self.v_max) * self.pwm_max)
        return max(-self.pwm_max, min(self.pwm_max, pwm))


def main():
    rclpy.init()
    node = TalusBaseBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('🛑 Shutdown')
    finally:
        # Para motores
        if node.ser and node.ser.is_open:
            node._send('V 0 0\n')
            node._send('H 0\n')
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
