from talus_base.kinect_validation.usb import KinectUsbDevice, find_kinect_devices, has_kinect


LSUSB = """\
Bus 001 Device 002: ID 2109:3431 VIA Labs, Inc. Hub
Bus 001 Device 005: ID 045e:02ae Microsoft Corp. Xbox NUI Camera
Bus 001 Device 006: ID 045e:02ad Microsoft Corp. Xbox NUI Audio
Bus 001 Device 007: ID 045e:02b0 Microsoft Corp. Xbox NUI Motor
"""


def test_find_kinect_devices_matches_camera_audio_and_motor_ids():
    assert find_kinect_devices(LSUSB) == [
        KinectUsbDevice(bus="001", device="005", usb_id="045e:02ae", label="Microsoft Corp. Xbox NUI Camera"),
        KinectUsbDevice(bus="001", device="006", usb_id="045e:02ad", label="Microsoft Corp. Xbox NUI Audio"),
        KinectUsbDevice(bus="001", device="007", usb_id="045e:02b0", label="Microsoft Corp. Xbox NUI Motor"),
    ]


def test_has_kinect_requires_camera_id_045e_02ae():
    assert has_kinect(LSUSB) is True
    assert has_kinect("Bus 001 Device 007: ID 045e:02b0 Microsoft Corp. Xbox NUI Motor") is False
