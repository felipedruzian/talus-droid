from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from talus_base.kinect_validation.status import KinectStatus, RoundSignals, classify_round


def test_pass_requires_usb_topics_samples_and_cleanup():
    signals = RoundSignals(
        usb_present_before=True,
        usb_present_after=True,
        launch_exit_code=0,
        launch_log="Kinect initialized\n",
        topics_seen={"/image_raw", "/depth/image_raw"},
        rgb_sample_ok=True,
        depth_sample_ok=True,
        cleanup_ok=True,
        collector_error=None,
    )
    assert classify_round(signals) == KinectStatus.PASS


def test_usb_missing_wins_before_other_failures():
    signals = RoundSignals(usb_present_before=False, collector_error="sampler crashed")
    assert classify_round(signals) == KinectStatus.USB_MISSING


def test_usb_missing_after_round_blocks_pass():
    signals = RoundSignals(
        usb_present_before=True,
        usb_present_after=False,
        topics_seen={"/image_raw", "/depth/image_raw"},
        rgb_sample_ok=True,
        depth_sample_ok=True,
        cleanup_ok=True,
    )
    assert classify_round(signals) == KinectStatus.USB_MISSING


def test_open_fail_when_usb_present_and_launch_log_mentions_libusb_open_error():
    signals = RoundSignals(
        usb_present_before=True,
        usb_present_after=True,
        launch_exit_code=1,
        launch_log="freenect_open_device() failed: LIBUSB_ERROR_ACCESS",
    )
    assert classify_round(signals) == KinectStatus.KINECT_OPEN_FAIL


def test_controlled_launch_shutdown_does_not_mask_rgb_timeout_as_open_fail():
    signals = RoundSignals(
        usb_present_before=True,
        usb_present_after=True,
        launch_exit_code=-15,
        launch_log="freenect initialized; shutting down after diagnostic sampling",
        topics_seen={"/image_raw", "/depth/image_raw"},
        rgb_sample_ok=False,
        depth_sample_ok=True,
        cleanup_ok=True,
    )
    assert classify_round(signals) == KinectStatus.RGB_TIMEOUT


def test_usb_busy_when_log_mentions_busy():
    signals = RoundSignals(
        usb_present_before=True,
        usb_present_after=True,
        launch_exit_code=1,
        launch_log="LIBUSB_ERROR_BUSY while opening Kinect",
    )
    assert classify_round(signals) == KinectStatus.USB_BUSY


def test_rgb_timeout_when_depth_sample_succeeds_but_rgb_does_not():
    signals = RoundSignals(
        usb_present_before=True,
        topics_seen={"/image_raw", "/depth/image_raw"},
        rgb_sample_ok=False,
        depth_sample_ok=True,
        cleanup_ok=True,
    )
    assert classify_round(signals) == KinectStatus.RGB_TIMEOUT


def test_depth_timeout_when_rgb_sample_succeeds_but_depth_does_not():
    signals = RoundSignals(
        usb_present_before=True,
        topics_seen={"/image_raw", "/depth/image_raw"},
        rgb_sample_ok=True,
        depth_sample_ok=False,
        cleanup_ok=True,
    )
    assert classify_round(signals) == KinectStatus.DEPTH_TIMEOUT


def test_topic_timeout_when_expected_topics_never_appear():
    signals = RoundSignals(
        usb_present_before=True,
        topics_seen={"/camera_info"},
        rgb_sample_ok=False,
        depth_sample_ok=False,
        cleanup_ok=True,
    )
    assert classify_round(signals) == KinectStatus.TOPIC_TIMEOUT


def test_cleanup_fail_after_successful_samples():
    signals = RoundSignals(
        usb_present_before=True,
        topics_seen={"/image_raw", "/depth/image_raw"},
        rgb_sample_ok=True,
        depth_sample_ok=True,
        cleanup_ok=False,
    )
    assert classify_round(signals) == KinectStatus.CLEANUP_FAIL


def test_collector_fail_when_sampler_or_command_collection_fails():
    signals = RoundSignals(usb_present_before=True, collector_error="ros2 topic list timed out")
    assert classify_round(signals) == KinectStatus.COLLECTOR_FAIL
