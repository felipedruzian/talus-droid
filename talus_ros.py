#!/usr/bin/env python3
import rclpy, serial, threading, time
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy, Imu
from std_msgs.msg import Int32, Bool

class TalusBaseBridge(Node):
    def __init__(self):
        super().__init__('talus_base_bridge')
        # ---------- Parâmetros ----------
        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('baud', 115200)
        self.declare_parameter('baseline', 0.19)     # distância entre rodas (m)
        self.declare_parameter('v_max', 0.50)        # m/s que mapeia para PWM 255
        self.declare_parameter('pwm_max', 255)

        # mapeamento de joystick (Xbox-like)
        self.declare_parameter('axis_linear', 1)     # LX vertical
        self.declare_parameter('axis_angular', 3)    # RX horizontal
        self.declare_parameter('scale_linear', 0.5)  # m/s
        self.declare_parameter('scale_angular', 1.0) # rad/s
        self.declare_parameter('enable_button', 4)   # LB
        self.declare_parameter('turbo_button', 5)    # RB
        self.declare_parameter('horn_button', 0)     # A

        # carrega parâmetros
        p = lambda n: self.get_parameter(n).get_parameter_value()
        self.port      = p('port').string_value
        self.baud      = p('baud').integer_value
        self.baseline  = float(self.get_parameter('baseline').value)
        self.v_max     = float(self.get_parameter('v_max').value)
        self.pwm_max   = int(self.get_parameter('pwm_max').value)

        self.axis_lin  = int(self.get_parameter('axis_linear').value)
        self.axis_ang  = int(self.get_parameter('axis_angular').value)
        self.k_lin     = float(self.get_parameter('scale_linear').value)
        self.k_ang     = float(self.get_parameter('scale_angular').value)
        self.btn_en    = int(self.get_parameter('enable_button').value)
        self.btn_turbo = int(self.get_parameter('turbo_button').value)
        self.btn_horn  = int(self.get_parameter('horn_button').value)

        # ---------- Serial ----------
        self.ser = None
        self._open_serial()

        # ---------- ROS pubs/subs ----------
        self.pub_cmd = self.create_publisher(Twist, 'cmd_vel', 10)
        self.pub_imu = self.create_publisher(Imu, 'imu/raw', 10)
        self.pub_l   = self.create_publisher(Int32, 'wheel/left_ticks', 10)
        self.pub_r   = self.create_publisher(Int32, 'wheel/right_ticks', 10)
        self.pub_horn= self.create_publisher(Bool, 'horn', 10)  # opcional p/ debug

        self.sub_cmd = self.create_subscription(Twist, 'cmd_vel', self.on_cmd, 10)
        self.sub_joy = self.create_subscription(Joy,   'joy',     self.on_joy, 10)

        # thread de RX serial
        self.rx_thread = threading.Thread(target=self.rx_loop, daemon=True)
        self.rx_thread.start()

        self.get_logger().info('TalusBaseBridge pronto ✔')

    # ---------- Serial helpers ----------
    def _open_serial(self):
        while rclpy.ok():
            try:
                self.ser = serial.Serial(self.port, baudrate=self.baud, timeout=0.1)
                self.get_logger().info(f'Conectado a {self.port} @ {self.baud}')
                # flush inicial
                time.sleep(0.2)
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                return
            except serial.SerialException as e:
                self.get_logger().warn(f'Falha ao abrir serial: {e}; tentando em 1s')
                time.sleep(1)

    def _send(self, s: str):
        try:
            if self.ser and self.ser.writable():
                self.ser.write(s.encode('utf-8'))
        except serial.SerialException as e:
            self.get_logger().error(f'Erro serial TX: {e}')

    def rx_loop(self):
        while rclpy.ok():
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                if line.startswith('IMU '):
                    # IMU ax ay az gx gy gz
                    try:
                        _, ax, ay, az, gx, gy, gz = line.split()
                        msg = Imu()
                        msg.header.stamp = self.get_clock().now().to_msg()
                        msg.linear_acceleration.x = float(ax)
                        msg.linear_acceleration.y = float(ay)
                        msg.linear_acceleration.z = float(az)
                        msg.angular_velocity.x = float(gx)
                        msg.angular_velocity.y = float(gy)
                        msg.angular_velocity.z = float(gz)
                        self.pub_imu.publish(msg)
                    except Exception as e:
                        self.get_logger().warn(f'Parse IMU falhou: {e} | "{line}"')

                elif line.startswith('ENC '):
                    # ENC l r
                    try:
                        _, l, r = line.split()
                        ml = Int32(); ml.data = int(l); self.pub_l.publish(ml)
                        mr = Int32(); mr.data = int(r); self.pub_r.publish(mr)
                    except Exception as e:
                        self.get_logger().warn(f'Parse ENC falhou: {e} | "{line}"')
                else:
                    # logs do boot, etc.
                    pass

            except serial.SerialException as e:
                self.get_logger().error(f'Erro serial RX: {e}. Reabrindo...')
                time.sleep(1)
                self._open_serial()

    # ---------- Joystick -> cmd_vel + horn ----------
    def on_joy(self, joy: Joy):
        try:
            enable = (joy.buttons[self.btn_en] == 1) if self.btn_en < len(joy.buttons) else False
            turbo  = (joy.buttons[self.btn_turbo] == 1) if self.btn_turbo < len(joy.buttons) else False
            horn   = (joy.buttons[self.btn_horn] == 1) if self.btn_horn < len(joy.buttons) else False

            scale_turbo = 1.5 if turbo else 1.0
            vx = 0.0
            wz = 0.0
            if enable:
                vx =  self.k_lin * scale_turbo * (joy.axes[self.axis_lin]  if self.axis_lin < len(joy.axes)  else 0.0)
                wz =  self.k_ang * scale_turbo * (joy.axes[self.axis_ang]  if self.axis_ang < len(joy.axes)  else 0.0)

            tw = Twist()
            tw.linear.x  = vx
            tw.angular.z = wz
            self.pub_cmd.publish(tw)          # publica cmd_vel p/ debug e outros nós

            # horn direto
            self.pub_horn.publish(Bool(data=horn))
            self._send(f'H {1 if horn else 0}\n')

        except Exception as e:
            self.get_logger().warn(f'on_joy erro: {e}')

    # ---------- cmd_vel -> motores ----------
    def on_cmd(self, tw: Twist):
        v = float(tw.linear.x)
        w = float(tw.angular.z)
        # cinemática diferencial
        vL = v - w*self.baseline/2.0
        vR = v + w*self.baseline/2.0

        def to_pwm(x):
            return int(max(-self.pwm_max, min(self.pwm_max, (x/self.v_max)*self.pwm_max)))
        L = to_pwm(vL)
        R = to_pwm(vR)
        self._send(f'V {L} {R}\n')

def main():
    rclpy.init()
    node = TalusBaseBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
