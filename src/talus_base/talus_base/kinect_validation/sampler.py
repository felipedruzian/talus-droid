from __future__ import annotations

import argparse
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


class OneImageSampler(Node):
    def __init__(self, topic: str):
        super().__init__("talus_kinect_one_image_sampler")
        self.received = None
        self.create_subscription(Image, topic, self._callback, qos_profile_sensor_data)

    def _callback(self, msg: Image) -> None:
        self.received = msg


def sample_image(topic: str, timeout_sec: float) -> tuple[bool, str]:
    rclpy.init(args=None)
    node = OneImageSampler(topic)
    deadline = time.monotonic() + timeout_sec
    try:
        while time.monotonic() < deadline and node.received is None:
            rclpy.spin_once(node, timeout_sec=0.1)
        if node.received is None:
            return False, f"TIMEOUT topic={topic} timeout_sec={timeout_sec}"
        msg = node.received
        return True, f"OK topic={topic} width={msg.width} height={msg.height} encoding={msg.encoding} stamp={msg.header.stamp.sec}.{msg.header.stamp.nanosec}"
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sample one sensor_msgs/Image message from a Kinect topic.")
    parser.add_argument("topic")
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)
    ok, message = sample_image(args.topic, args.timeout)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
