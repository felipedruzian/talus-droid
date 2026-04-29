from __future__ import annotations

from dataclasses import dataclass
import re

KINECT_USB_IDS = {"045e:02ae", "045e:02ad", "045e:02b0"}
KINECT_CAMERA_ID = "045e:02ae"
LSUSB_RE = re.compile(r"^Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+):\s+ID\s+(?P<usb_id>[0-9a-fA-F:]+)\s*(?P<label>.*)$")


@dataclass(frozen=True)
class KinectUsbDevice:
    bus: str
    device: str
    usb_id: str
    label: str


def find_kinect_devices(lsusb_text: str) -> list[KinectUsbDevice]:
    devices: list[KinectUsbDevice] = []
    for line in lsusb_text.splitlines():
        match = LSUSB_RE.match(line.strip())
        if not match:
            continue
        usb_id = match.group("usb_id").lower()
        if usb_id in KINECT_USB_IDS or "xbox nui" in match.group("label").lower():
            devices.append(
                KinectUsbDevice(
                    bus=match.group("bus"),
                    device=match.group("device"),
                    usb_id=usb_id,
                    label=match.group("label").strip(),
                )
            )
    return devices


def has_kinect(lsusb_text: str) -> bool:
    return any(device.usb_id == KINECT_CAMERA_ID for device in find_kinect_devices(lsusb_text))
