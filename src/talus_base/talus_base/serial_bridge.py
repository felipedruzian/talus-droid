#!/usr/bin/env python3
"""ROS 2 serial bridge for the Talus base.

Protocol:
- TX: PING
- TX: DRV <left_pwm> <right_pwm>
- TX: HORN <0|1>          (optional)
- TX: BEEP <pattern_id>   (optional)
- RX: PONG <fw_version> [details...]
- RX: IMU <ax> <ay> <az> <gx> <gy> <gz>
- RX: ENC <left_ticks> <right_ticks>  (optional)
- RX: ERR <code> <detail...>
- RX: OK <detail...>
"""

from __future__ import annotations

import threading
import time
from typing import Optional, Tuple

import rclpy
import serial
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Bool, Int32


class TalusBaseBridge(Node):
    """Serial bridge between ROS 2 cmd_vel and the Arduino base controller."""

    def __init__(self) -> None:
        super().__init__("talus_base_bridge")

        self.declare_parameter("port", "/dev/ttyUSB0")
        self.declare_parameter("baud", 115200)
        self.declare_parameter("baseline", 0.19)
        self.declare_parameter("v_max", 0.50)
        self.declare_parameter("pwm_max", 255)
        self.declare_parameter("serial_boot_wait", 0.4)
        self.declare_parameter("serial_timeout", 0.05)
        self.declare_parameter("drive_keepalive", 0.10)
        self.declare_parameter("handshake_timeout", 2.0)
        self.declare_parameter("reconnect_backoff", 1.0)
        self.declare_parameter("enable_status_beeps", True)
        self.declare_parameter("beep_on_first_connect", 1)
        self.declare_parameter("beep_on_reconnect", 3)
        self.declare_parameter("debug", False)

        self.port = self.get_parameter("port").value
        self.baud = self.get_parameter("baud").value
        self.baseline = self.get_parameter("baseline").value
        self.v_max = self.get_parameter("v_max").value
        self.pwm_max = self.get_parameter("pwm_max").value
        self.serial_boot_wait = self.get_parameter("serial_boot_wait").value
        self.serial_timeout = self.get_parameter("serial_timeout").value
        self.drive_keepalive = self.get_parameter("drive_keepalive").value
        self.handshake_timeout = self.get_parameter("handshake_timeout").value
        self.reconnect_backoff = self.get_parameter("reconnect_backoff").value
        self.enable_status_beeps = self.get_parameter("enable_status_beeps").value
        self.beep_on_first_connect = self.get_parameter("beep_on_first_connect").value
        self.beep_on_reconnect = self.get_parameter("beep_on_reconnect").value
        self.debug = self.get_parameter("debug").value

        self.ser: Optional[serial.Serial] = None
        self.serial_lock = threading.Lock()
        self.last_pwm_cmd: Optional[Tuple[int, int]] = None
        self.last_horn_state: Optional[bool] = None
        self.last_drive_send_time = 0.0
        self.ever_connected = False

        self.pub_imu = self.create_publisher(Imu, "imu/raw", 10)
        self.pub_left_ticks = self.create_publisher(Int32, "wheel/left_ticks", 10)
        self.pub_right_ticks = self.create_publisher(Int32, "wheel/right_ticks", 10)

        self.sub_cmd = self.create_subscription(Twist, "cmd_vel", self.on_cmd, 10)
        self.sub_horn = self.create_subscription(Bool, "horn", self.on_horn, 10)

        self._open_serial()
        self.rx_thread = threading.Thread(target=self.rx_loop, daemon=True)
        self.rx_thread.start()

        self.get_logger().info("TalusBaseBridge ready")

    def _open_serial(self) -> None:
        while rclpy.ok():
            serial_port: Optional[serial.Serial] = None
            try:
                serial_port = serial.Serial(
                    self.port,
                    baudrate=self.baud,
                    timeout=self.serial_timeout,
                    write_timeout=1.0,
                )
                time.sleep(self.serial_boot_wait)
                serial_port.reset_input_buffer()
                serial_port.reset_output_buffer()

                fw_description = self._perform_handshake(serial_port)

                with self.serial_lock:
                    self.ser = serial_port

                self.last_pwm_cmd = None
                self.last_horn_state = None
                self.last_drive_send_time = 0.0

                beep_id = (
                    self.beep_on_reconnect
                    if self.ever_connected
                    else self.beep_on_first_connect
                )
                if self.enable_status_beeps and beep_id > 0:
                    self._send_beep(beep_id, force=True)

                self.ever_connected = True
                self.get_logger().info(
                    f"Serial connected: {self.port} @ {self.baud} | {fw_description}"
                )
                return
            except (serial.SerialException, RuntimeError) as exc:
                if serial_port and serial_port.is_open:
                    serial_port.close()
                self.get_logger().warn(
                    f"Serial setup failed: {exc} - retry in {self.reconnect_backoff:.1f}s"
                )
                time.sleep(self.reconnect_backoff)

    def _perform_handshake(self, serial_port: serial.Serial) -> str:
        serial_port.write(b"PING\n")
        serial_port.flush()

        deadline = time.monotonic() + self.handshake_timeout
        while rclpy.ok() and time.monotonic() < deadline:
            raw = serial_port.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            if line.startswith("PONG"):
                description = line[len("PONG") :].strip()
                return description or "fw=unknown"

            if line.startswith("ERR "):
                self.get_logger().warn(f"Arduino handshake warning: {line}")
            elif self.debug:
                self.get_logger().debug(f"Handshake RX: {line}")

        raise RuntimeError("handshake timed out waiting for PONG")

    def _close_serial(self) -> None:
        with self.serial_lock:
            serial_port = self.ser
            self.ser = None

        if serial_port and serial_port.is_open:
            try:
                serial_port.close()
            except serial.SerialException:
                pass

    def _recover_serial(self) -> None:
        self._close_serial()
        time.sleep(self.reconnect_backoff)
        self._open_serial()

    def _send(self, command: str) -> bool:
        payload = command.encode("utf-8")
        try:
            with self.serial_lock:
                if not self.ser or not self.ser.is_open:
                    return False
                self.ser.write(payload)
                self.ser.flush()
            if self.debug:
                self.get_logger().debug(f"TX: {command.strip()}")
            return True
        except serial.SerialException as exc:
            self.get_logger().error(f"Serial TX error: {exc}")
            self._recover_serial()
            return False

    def _send_drive(self, pwm_left: int, pwm_right: int, force: bool = False) -> None:
        now = time.monotonic()
        command = (int(pwm_left), int(pwm_right))
        same_as_last = command == self.last_pwm_cmd
        keepalive_due = (now - self.last_drive_send_time) >= self.drive_keepalive

        if not force and same_as_last and not keepalive_due:
            return

        if self._send(f"DRV {command[0]} {command[1]}\n"):
            self.last_pwm_cmd = command
            self.last_drive_send_time = now

    def _send_horn(self, enabled: bool, force: bool = False) -> None:
        if not force and enabled == self.last_horn_state:
            return
        if self._send(f"HORN {1 if enabled else 0}\n"):
            self.last_horn_state = enabled

    def _send_beep(self, pattern_id: int, force: bool = False) -> None:
        if not self.enable_status_beeps and not force:
            return
        self._send(f"BEEP {int(pattern_id)}\n")

    def rx_loop(self) -> None:
        while rclpy.ok():
            line = ""
            try:
                with self.serial_lock:
                    if self.ser and self.ser.is_open:
                        line = self.ser.readline().decode(
                            "utf-8", errors="ignore"
                        ).strip()

                if not line:
                    time.sleep(0.01)
                    continue

                self._handle_serial_line(line)
            except serial.SerialException as exc:
                self.get_logger().error(f"Serial RX error: {exc} - reconnecting")
                self._recover_serial()
            except Exception as exc:  # noqa: BLE001
                self.get_logger().warn(f'Parse error: {exc} | "{line}"')

    def _handle_serial_line(self, line: str) -> None:
        if line.startswith("PONG "):
            self.get_logger().info(f"Arduino: {line}")
            return

        if line.startswith("IMU "):
            parts = line.split()
            if len(parts) != 7:
                raise ValueError(f"invalid IMU frame: {line}")

            msg = Imu()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = "imu_link"
            msg.linear_acceleration.x = float(parts[1])
            msg.linear_acceleration.y = float(parts[2])
            msg.linear_acceleration.z = float(parts[3])
            msg.angular_velocity.x = float(parts[4])
            msg.angular_velocity.y = float(parts[5])
            msg.angular_velocity.z = float(parts[6])
            msg.orientation_covariance[0] = -1.0
            self.pub_imu.publish(msg)
            return

        if line.startswith("ENC "):
            parts = line.split()
            if len(parts) != 3:
                raise ValueError(f"invalid ENC frame: {line}")

            self.pub_left_ticks.publish(Int32(data=int(parts[1])))
            self.pub_right_ticks.publish(Int32(data=int(parts[2])))
            return

        if line.startswith("ERR "):
            self.get_logger().warn(f"Arduino error: {line}")
            return

        if line.startswith("OK "):
            if self.debug:
                self.get_logger().debug(f"Arduino: {line}")
            return

        if self.debug:
            self.get_logger().debug(f"RX: {line}")

    def on_cmd(self, msg: Twist) -> None:
        left_velocity = msg.linear.x - msg.angular.z * self.baseline / 2.0
        right_velocity = msg.linear.x + msg.angular.z * self.baseline / 2.0

        self._send_drive(
            self._vel_to_pwm(left_velocity),
            self._vel_to_pwm(right_velocity),
        )

    def on_horn(self, msg: Bool) -> None:
        self._send_horn(msg.data)

    def _vel_to_pwm(self, velocity: float) -> int:
        pwm_value = int((velocity / self.v_max) * self.pwm_max)
        return max(-self.pwm_max, min(self.pwm_max, pwm_value))


def main() -> None:
    rclpy.init()
    node = TalusBaseBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Shutdown requested")
    finally:
        node._send_drive(0, 0, force=True)
        node._send_horn(False, force=True)
        node._close_serial()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
