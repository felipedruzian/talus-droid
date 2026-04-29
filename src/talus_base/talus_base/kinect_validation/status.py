from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class KinectStatus(StrEnum):
    PASS = "PASS"
    USB_MISSING = "USB_MISSING"
    USB_BUSY = "USB_BUSY"
    KINECT_OPEN_FAIL = "KINECT_OPEN_FAIL"
    RGB_TIMEOUT = "RGB_TIMEOUT"
    DEPTH_TIMEOUT = "DEPTH_TIMEOUT"
    TOPIC_TIMEOUT = "TOPIC_TIMEOUT"
    CLEANUP_FAIL = "CLEANUP_FAIL"
    COLLECTOR_FAIL = "COLLECTOR_FAIL"


EXPECTED_TOPICS = frozenset({"/image_raw", "/depth/image_raw"})


@dataclass(frozen=True)
class RoundSignals:
    usb_present_before: bool = True
    usb_present_after: bool = True
    launch_exit_code: int | None = None
    launch_log: str = ""
    topics_seen: set[str] = field(default_factory=set)
    rgb_sample_ok: bool = False
    depth_sample_ok: bool = False
    cleanup_ok: bool = True
    collector_error: str | None = None


def classify_round(signals: RoundSignals) -> KinectStatus:
    if not signals.usb_present_before:
        return KinectStatus.USB_MISSING
    if not signals.usb_present_after:
        return KinectStatus.USB_MISSING
    if signals.collector_error:
        return KinectStatus.COLLECTOR_FAIL

    log_lower = signals.launch_log.lower()
    if "libusb_error_busy" in log_lower or "resource busy" in log_lower:
        return KinectStatus.USB_BUSY
    if (
        signals.launch_exit_code not in (None, 0, -15)
        and ("open" in log_lower or "freenect" in log_lower or "libusb" in log_lower)
    ):
        return KinectStatus.KINECT_OPEN_FAIL

    if not EXPECTED_TOPICS.issubset(signals.topics_seen):
        return KinectStatus.TOPIC_TIMEOUT
    if not signals.rgb_sample_ok:
        return KinectStatus.RGB_TIMEOUT
    if not signals.depth_sample_ok:
        return KinectStatus.DEPTH_TIMEOUT
    if not signals.cleanup_ok:
        return KinectStatus.CLEANUP_FAIL
    return KinectStatus.PASS
