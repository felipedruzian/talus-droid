import json
from pathlib import Path

import pytest

from talus_base.kinect_validation import runner


LSUSB_WITH_KINECT = """\
Bus 001 Device 005: ID 045e:02ae Microsoft Corp. Xbox NUI Camera
Bus 001 Device 006: ID 045e:02ad Microsoft Corp. Xbox NUI Audio
Bus 001 Device 007: ID 045e:02b0 Microsoft Corp. Xbox NUI Motor
"""


def read_summary(round_dir: Path) -> dict[str, object]:
    return json.loads((round_dir / "summary.json").read_text())


def test_run_one_round_keeps_launch_alive_until_sampling_finishes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    events: list[str] = []
    launch_state: dict[str, object | None] = {"proc": None}

    class FakeLaunchProcess:
        def __init__(self, argv, **_kwargs):
            events.append("launch:start")
            self.argv = argv
            self.returncode = None
            self._alive = True
            launch_state["proc"] = self

        def poll(self):
            return None if self._alive else self.returncode

        def terminate(self):
            events.append("launch:terminate")
            self._alive = False
            self.returncode = 0

        def wait(self, timeout=None):
            events.append(f"launch:wait:{timeout}")
            self._alive = False
            self.returncode = 0
            return 0

    def fake_cleanup() -> bool:
        events.append("cleanup")
        return True

    def fake_collect_text(argv: list[str], timeout: int = 30) -> str:
        if argv == ["lsusb"]:
            return LSUSB_WITH_KINECT
        if argv[:1] == ["git"]:
            return "main\n" if "--abbrev-ref" in argv else "deadbeef\n"
        if argv[:1] == ["ps"] or argv[:1] == ["dmesg"]:
            return ""
        if argv[:3] == ["ros2", "topic", "list"]:
            proc = launch_state["proc"]
            alive = proc is not None and proc.poll() is None
            events.append("topics:while-launch-alive" if alive else "topics:while-launch-dead")
            return "/image_raw\n/depth/image_raw\n"
        raise AssertionError(f"unexpected collect_text argv={argv} timeout={timeout}")

    def fake_run_command(argv: list[str], timeout: int = 30) -> tuple[int, str]:
        if argv[:4] == ["ros2", "run", "talus_base", "talus_kinect_sample_image"]:
            proc = launch_state["proc"]
            alive = proc is not None and proc.poll() is None
            sample_name = "rgb" if argv[4] == "/image_raw" else "depth"
            events.append(f"{sample_name}:while-launch-alive" if alive else f"{sample_name}:while-launch-dead")
            return 0, "OK\n"
        if argv[:3] == ["timeout", "20", "ros2"]:
            events.append("launch:blocking-run")
            return 0, "launch completed\n"
        raise AssertionError(f"unexpected run_command argv={argv} timeout={timeout}")

    monkeypatch.setattr(runner.subprocess, "Popen", FakeLaunchProcess)
    monkeypatch.setattr(runner, "cleanup_related_processes", fake_cleanup)
    monkeypatch.setattr(runner, "collect_text", fake_collect_text)
    monkeypatch.setattr(runner, "run_command", fake_run_command)
    monkeypatch.setattr(runner, "has_kinect", lambda _text: True)
    monkeypatch.setattr(runner.time, "sleep", lambda *_args, **_kwargs: None)

    runner.run_one_round(tmp_path, "isolated-default", 1, settle_secs=0, dry_run=False)

    assert "launch:start" in events
    assert "topics:while-launch-alive" in events
    assert "rgb:while-launch-alive" in events
    assert "depth:while-launch-alive" in events
    assert "launch:terminate" in events
    assert "cleanup" in events
    assert events.index("topics:while-launch-alive") < events.index("launch:terminate") < events.index("cleanup")
    assert "topics:while-launch-dead" not in events
    assert "rgb:while-launch-dead" not in events
    assert "depth:while-launch-dead" not in events


def test_run_one_round_maps_topic_list_collection_failures_to_collector_fail_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def fake_collect_text(argv: list[str], timeout: int = 30) -> str:
        if argv == ["lsusb"]:
            return LSUSB_WITH_KINECT
        if argv[:1] == ["git"]:
            return "main\n" if "--abbrev-ref" in argv else "deadbeef\n"
        if argv[:1] == ["ps"] or argv[:1] == ["dmesg"]:
            return ""
        if argv[:3] == ["ros2", "topic", "list"]:
            return "COLLECTOR_ERROR TimeoutExpired: ros2 topic list\n"
        raise AssertionError(f"unexpected collect_text argv={argv} timeout={timeout}")

    def fake_run_command(argv: list[str], timeout: int = 30) -> tuple[int, str]:
        if argv[:3] == ["timeout", "20", "ros2"]:
            return 0, "launch ok\n"
        if argv[:4] == ["ros2", "run", "talus_base", "talus_kinect_sample_image"]:
            return 0, "OK\n"
        raise AssertionError(f"unexpected run_command argv={argv} timeout={timeout}")

    monkeypatch.setattr(runner, "cleanup_related_processes", lambda: True)
    monkeypatch.setattr(runner, "collect_text", fake_collect_text)
    monkeypatch.setattr(runner, "run_command", fake_run_command)
    monkeypatch.setattr(runner, "has_kinect", lambda _text: True)
    monkeypatch.setattr(runner.time, "sleep", lambda *_args, **_kwargs: None)

    rc = runner.run_one_round(tmp_path, "isolated-default", 1, settle_secs=0, dry_run=False)

    round_dir = tmp_path / "isolated-default" / "round-001"
    summary = read_summary(round_dir)
    assert rc == 1
    assert (round_dir / "classification.txt").read_text() == "COLLECTOR_FAIL\n"
    assert summary["status"] == "COLLECTOR_FAIL"
    assert summary["signals"]["collector_error"] == "ros2 topic list"


def test_run_one_round_maps_sampler_crash_to_collector_fail_and_records_failure_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    def fake_collect_text(argv: list[str], timeout: int = 30) -> str:
        if argv == ["lsusb"]:
            return LSUSB_WITH_KINECT
        if argv[:1] == ["git"]:
            return "main\n" if "--abbrev-ref" in argv else "deadbeef\n"
        if argv[:1] == ["ps"] or argv[:1] == ["dmesg"]:
            return ""
        if argv[:3] == ["ros2", "topic", "list"]:
            return "/image_raw\n/depth/image_raw\n"
        raise AssertionError(f"unexpected collect_text argv={argv} timeout={timeout}")

    def fake_run_command(argv: list[str], timeout: int = 30) -> tuple[int, str]:
        if argv[:3] == ["timeout", "20", "ros2"]:
            return 0, "launch ok\n"
        if argv[:4] == ["ros2", "run", "talus_base", "talus_kinect_sample_image"] and argv[4] == "/image_raw":
            return 2, "SAMPLER_CRASH RuntimeError: subscriber aborted\n"
        if argv[:4] == ["ros2", "run", "talus_base", "talus_kinect_sample_image"] and argv[4] == "/depth/image_raw":
            return 0, "OK\n"
        raise AssertionError(f"unexpected run_command argv={argv} timeout={timeout}")

    monkeypatch.setattr(runner, "cleanup_related_processes", lambda: True)
    monkeypatch.setattr(runner, "collect_text", fake_collect_text)
    monkeypatch.setattr(runner, "run_command", fake_run_command)
    monkeypatch.setattr(runner, "has_kinect", lambda _text: True)
    monkeypatch.setattr(runner.time, "sleep", lambda *_args, **_kwargs: None)

    rc = runner.run_one_round(tmp_path, "isolated-default", 1, settle_secs=0, dry_run=False)

    round_dir = tmp_path / "isolated-default" / "round-001"
    summary = read_summary(round_dir)
    assert rc == 1
    assert (round_dir / "classification.txt").read_text() == "COLLECTOR_FAIL\n"
    assert summary["status"] == "COLLECTOR_FAIL"
    assert summary["signals"]["collector_error"] == "talus_kinect_sample_image /image_raw"


def test_run_one_round_persists_artifacts_and_maps_post_launch_cleanup_failure_to_cleanup_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    cleanup_calls: list[str] = []
    cleanup_results = iter([True, False])

    def fake_cleanup() -> bool:
        cleanup_calls.append("cleanup")
        return next(cleanup_results)

    def fake_collect_text(argv: list[str], timeout: int = 30) -> str:
        if argv == ["lsusb"]:
            return LSUSB_WITH_KINECT
        if argv[:1] == ["git"]:
            return "main\n" if "--abbrev-ref" in argv else "deadbeef\n"
        if argv[:1] == ["ps"] or argv[:1] == ["dmesg"]:
            return ""
        if argv[:3] == ["ros2", "topic", "list"]:
            return "/image_raw\n/depth/image_raw\n"
        raise AssertionError(f"unexpected collect_text argv={argv} timeout={timeout}")

    def fake_run_command(argv: list[str], timeout: int = 30) -> tuple[int, str]:
        if argv[:3] == ["timeout", "20", "ros2"]:
            return 0, "launch ok\n"
        if argv[:4] == ["ros2", "run", "talus_base", "talus_kinect_sample_image"]:
            return 0, "OK\n"
        raise AssertionError(f"unexpected run_command argv={argv} timeout={timeout}")

    monkeypatch.setattr(runner, "cleanup_related_processes", fake_cleanup)
    monkeypatch.setattr(runner, "collect_text", fake_collect_text)
    monkeypatch.setattr(runner, "run_command", fake_run_command)
    monkeypatch.setattr(runner, "has_kinect", lambda _text: True)
    monkeypatch.setattr(runner.time, "sleep", lambda *_args, **_kwargs: None)

    rc = runner.run_one_round(tmp_path, "isolated-default", 1, settle_secs=0, dry_run=False)

    round_dir = tmp_path / "isolated-default" / "round-001"
    summary = read_summary(round_dir)
    assert cleanup_calls == ["cleanup", "cleanup"]
    assert rc == 1
    assert (round_dir / "classification.txt").read_text() == "CLEANUP_FAIL\n"
    assert summary["status"] == "CLEANUP_FAIL"
    assert summary["signals"]["cleanup_ok"] is False
    assert (round_dir / "kinect-launch.log").read_text() == "launch ok\n"
    assert (round_dir / "topic-list.txt").read_text() == "/image_raw\n/depth/image_raw\n"
    assert (round_dir / "rgb-sample.txt").read_text() == "OK\n"
    assert (round_dir / "depth-sample.txt").read_text() == "OK\n"


def test_run_one_round_records_usb_missing_after_round_in_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    lsusb_calls = 0

    def fake_collect_text(argv: list[str], timeout: int = 30) -> str:
        nonlocal lsusb_calls
        if argv == ["lsusb"]:
            lsusb_calls += 1
            if lsusb_calls == 1:
                return LSUSB_WITH_KINECT
            return "Bus 001 Device 002: ID 1d6b:0002 Linux Foundation 2.0 root hub\n"
        if argv[:1] == ["git"]:
            return "main\n" if "--abbrev-ref" in argv else "deadbeef\n"
        if argv[:1] == ["ps"] or argv[:1] == ["dmesg"]:
            return ""
        if argv[:3] == ["ros2", "topic", "list"]:
            return "/image_raw\n/depth/image_raw\n"
        raise AssertionError(f"unexpected collect_text argv={argv} timeout={timeout}")

    def fake_run_command(argv: list[str], timeout: int = 30) -> tuple[int, str]:
        if argv[:3] == ["timeout", "20", "ros2"]:
            return 0, "launch ok\n"
        if argv[:4] == ["ros2", "run", "talus_base", "talus_kinect_sample_image"]:
            return 0, "OK\n"
        raise AssertionError(f"unexpected run_command argv={argv} timeout={timeout}")

    monkeypatch.setattr(runner, "cleanup_related_processes", lambda: True)
    monkeypatch.setattr(runner, "collect_text", fake_collect_text)
    monkeypatch.setattr(runner, "run_command", fake_run_command)
    monkeypatch.setattr(runner.time, "sleep", lambda *_args, **_kwargs: None)

    rc = runner.run_one_round(tmp_path, "isolated-default", 1, settle_secs=0, dry_run=False)

    round_dir = tmp_path / "isolated-default" / "round-001"
    summary = read_summary(round_dir)
    assert rc == 1
    assert summary["status"] == "USB_MISSING"
    assert summary["signals"]["usb_present_before"] is True
    assert summary["signals"]["usb_present_after"] is False


def test_usb_reset_group_issues_opt_in_reset_command_before_launch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    commands: list[tuple[str, ...]] = []

    def fake_collect_text(argv: list[str], timeout: int = 30) -> str:
        if argv == ["lsusb"]:
            return LSUSB_WITH_KINECT
        if argv[:1] == ["git"]:
            return "main\n" if "--abbrev-ref" in argv else "deadbeef\n"
        if argv[:1] == ["ps"] or argv[:1] == ["dmesg"]:
            return ""
        if argv[:3] == ["ros2", "topic", "list"]:
            return "/image_raw\n/depth/image_raw\n"
        raise AssertionError(f"unexpected collect_text argv={argv} timeout={timeout}")

    def fake_run_command(argv: list[str], timeout: int = 30) -> tuple[int, str]:
        commands.append(tuple(argv))
        if argv[:3] == ["timeout", "20", "ros2"]:
            return 0, "launch ok\n"
        if argv[:4] == ["ros2", "run", "talus_base", "talus_kinect_sample_image"]:
            return 0, "OK\n"
        if argv[:1] == ["usbreset"]:
            return 0, "reset ok\n"
        raise AssertionError(f"unexpected run_command argv={argv} timeout={timeout}")

    monkeypatch.setattr(runner, "cleanup_related_processes", lambda: True)
    monkeypatch.setattr(runner, "collect_text", fake_collect_text)
    monkeypatch.setattr(runner, "run_command", fake_run_command)
    monkeypatch.setattr(runner, "has_kinect", lambda _text: True)
    monkeypatch.setattr(runner.time, "sleep", lambda *_args, **_kwargs: None)

    runner.run_one_round(tmp_path, "usb-reset", 1, settle_secs=5, dry_run=False)

    expected_reset = ("usbreset", "/dev/bus/usb/001/005")
    expected_launch = (
        "timeout",
        "20",
        "ros2",
        "launch",
        "talus_bringup",
        "kinect.launch.py",
        "driver_mode:=unified",
        "enable_point_cloud:=false",
    )
    launch_index = next(i for i, argv in enumerate(commands) if argv[:3] == ("timeout", "20", "ros2"))
    reset_index = commands.index(expected_reset)
    assert commands[reset_index] == expected_reset
    assert commands[launch_index] == expected_launch
    assert reset_index < launch_index
