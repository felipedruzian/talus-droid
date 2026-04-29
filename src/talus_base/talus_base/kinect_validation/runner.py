from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .artifacts import RoundArtifactPaths, write_round_summary, write_text
from .processes import find_relevant_process_lines
from .status import RoundSignals, classify_round
from .usb import KINECT_CAMERA_ID, find_kinect_devices, has_kinect

DEFAULT_ARTIFACT_ROOT = Path("artifacts/testlogs/2026-04-27-kinect-validation/raspi")


@dataclass(frozen=True)
class MatrixItem:
    group: str
    settle_secs: int
    rounds: int


def build_matrix_plan(default_rounds: int = 10, settle_rounds: int = 5) -> list[MatrixItem]:
    return [
        MatrixItem("isolated-default", 0, default_rounds),
        MatrixItem("settle-10s", 10, settle_rounds),
        MatrixItem("settle-30s", 30, settle_rounds),
        MatrixItem("settle-60s", 60, settle_rounds),
    ]


def build_preflight_plan() -> list[MatrixItem]:
    return [MatrixItem("preflight", 0, 1)]


def run_command(argv: list[str], timeout: int = 30) -> tuple[int, str]:
    completed = subprocess.run(
        argv,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return completed.returncode, completed.stdout


ORIGINAL_RUN_COMMAND = run_command
ORIGINAL_POPEN = subprocess.Popen


def collect_text(argv: list[str], timeout: int = 30) -> str:
    try:
        return run_command(argv, timeout=timeout)[1]
    except Exception as exc:
        return f"COLLECTOR_ERROR {type(exc).__name__}: {exc}\n"


def is_collector_error_text(text: str) -> bool:
    return text.lstrip().startswith("COLLECTOR_ERROR")


def is_timeout_text(text: str) -> bool:
    lower = text.lower()
    return "timeout" in lower or "timed out" in lower


def build_launch_command() -> list[str]:
    return [
        "ros2",
        "launch",
        "talus_bringup",
        "kinect.launch.py",
        "driver_mode:=unified",
        "enable_point_cloud:=false",
    ]


def should_use_live_launch() -> bool:
    return subprocess.Popen is not ORIGINAL_POPEN or run_command is ORIGINAL_RUN_COMMAND


def extract_kinect_camera_usb_path(lsusb_text: str) -> str | None:
    for device in find_kinect_devices(lsusb_text):
        if device.usb_id == KINECT_CAMERA_ID:
            return f"/dev/bus/usb/{device.bus}/{device.device}"
    return None


def maybe_reset_kinect_usb(group: str, lsusb_text: str, dry_run: bool) -> str:
    if group != "usb-reset":
        return ""
    camera_path = extract_kinect_camera_usb_path(lsusb_text)
    if not camera_path:
        return "USB reset skipped: Kinect camera path not found\n"
    if dry_run:
        return f"DRY_RUN would execute: usbreset {camera_path}\n"
    try:
        _returncode, output = run_command(["usbreset", camera_path], timeout=10)
        return output
    except Exception as exc:
        return f"COLLECTOR_ERROR {type(exc).__name__}: {exc}\n"


def run_sampler(topic: str) -> tuple[bool, str | None, str]:
    identity = f"talus_kinect_sample_image {topic}"
    argv = ["ros2", "run", "talus_base", "talus_kinect_sample_image", topic, "--timeout", "10"]
    try:
        returncode, output = run_command(argv, timeout=15)
    except Exception as exc:
        return False, identity, f"COLLECTOR_ERROR {type(exc).__name__}: {exc}\n"

    if returncode == 0 and "SAMPLER_CRASH" not in output and not is_collector_error_text(output):
        return True, None, output
    if "SAMPLER_CRASH" in output or is_collector_error_text(output) or (returncode != 0 and not is_timeout_text(output)):
        return False, identity, output
    return False, None, output


def wait_for_kinect_topics(timeout_secs: float = 20.0, poll_secs: float = 1.0) -> tuple[set[str], str, str | None]:
    """Poll topic list until both Kinect image topics are visible or timeout expires."""
    deadline = time.monotonic() + timeout_secs
    last_topics_text = ""
    while True:
        topics_text = collect_text(["ros2", "topic", "list"], timeout=10)
        last_topics_text = topics_text
        if is_collector_error_text(topics_text):
            return set(), topics_text, "ros2 topic list"
        topics = set(topics_text.split())
        if {"/image_raw", "/depth/image_raw"}.issubset(topics):
            return topics, topics_text, None
        if time.monotonic() >= deadline:
            return topics, topics_text, None
        time.sleep(poll_secs)


def terminate_launch_process(proc: subprocess.Popen[str]) -> tuple[int | None, str]:
    try:
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except Exception:
                proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    proc.kill()
                proc.wait(timeout=5)
        elif proc.returncode is None:
            proc.wait(timeout=1)
    except Exception:
        pass

    launch_log = ""
    stdout = getattr(proc, "stdout", None)
    if stdout is not None:
        try:
            launch_log = stdout.read()
        except Exception:
            launch_log = ""
    return proc.returncode, launch_log


def run_live_launch_round() -> tuple[int | None, str, set[str], bool, bool, str | None, str, str]:
    launch_proc = subprocess.Popen(
        build_launch_command(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    launch_exit: int | None = None
    launch_log = ""
    collector_error: str | None = None
    topics_text = ""
    topics: set[str] = set()
    rgb_ok = False
    depth_ok = False

    try:
        topics, topics_text, collector_error = wait_for_kinect_topics()

        rgb_ok, rgb_error, _rgb_output = run_sampler("/image_raw")
        if rgb_error and collector_error is None:
            collector_error = rgb_error

        depth_ok, depth_error, _depth_output = run_sampler("/depth/image_raw")
        if depth_error and collector_error is None:
            collector_error = depth_error
    finally:
        launch_exit, launch_log = terminate_launch_process(launch_proc)

    return launch_exit, launch_log, topics, rgb_ok, depth_ok, collector_error, topics_text, ""


def run_blocking_launch_round() -> tuple[int | None, str, set[str], bool, bool, str | None, str, str]:
    launch_exit, launch_log = run_command(["timeout", "20", *build_launch_command()], timeout=25)
    topics_text = collect_text(["ros2", "topic", "list"], timeout=10)
    collector_error: str | None = "ros2 topic list" if is_collector_error_text(topics_text) else None
    topics = set() if collector_error else set(topics_text.split())

    rgb_ok, rgb_error, _rgb_output = run_sampler("/image_raw")
    if rgb_error and collector_error is None:
        collector_error = rgb_error

    depth_ok, depth_error, _depth_output = run_sampler("/depth/image_raw")
    if depth_error and collector_error is None:
        collector_error = depth_error

    return launch_exit, launch_log, topics, rgb_ok, depth_ok, collector_error, topics_text, ""


def cleanup_related_processes() -> bool:
    # Conservative diagnostic cleanup: terminate known ROS launch/node processes from previous diagnostic rounds only.
    subprocess.run(["pkill", "-f", "ros2 launch talus_bringup kinect.launch.py"], check=False)
    subprocess.run(["pkill", "-f", "kinect_ros2_node"], check=False)
    subprocess.run(["pkill", "-f", "camera_rgb_optical_static_tf"], check=False)
    subprocess.run(["pkill", "-f", "camera_depth_optical_static_tf"], check=False)
    subprocess.run(["pkill", "-f", "camera_mount_static_tf"], check=False)
    time.sleep(2)
    ps_after = collect_text(["ps", "-eo", "pid,ppid,stat,comm,args"], timeout=10)
    return not find_relevant_process_lines(ps_after)


def serialize_signals(signals: RoundSignals) -> dict[str, object]:
    payload = asdict(signals)
    payload["topics_seen"] = sorted(signals.topics_seen)
    return payload


def run_one_round(root: Path, group: str, round_number: int, settle_secs: int, dry_run: bool = False) -> int:
    paths = RoundArtifactPaths(root=root, group=group, round_number=round_number)
    paths.ensure()
    write_text(paths.file("metadata.txt"), f"group={group}\nround={round_number}\nsettle_secs={settle_secs}\n")
    write_text(
        paths.file("env.txt"),
        f"ROS_DOMAIN_ID={os.environ.get('ROS_DOMAIN_ID', '42')}\n"
        f"RMW_IMPLEMENTATION={os.environ.get('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp')}\n"
        "TALUS_KINECT_DRIVER_MODE=unified\n"
        "TALUS_KINECT_ENABLE_POINT_CLOUD=false\n",
    )
    write_text(
        paths.file("git.txt"),
        collect_text(["git", "rev-parse", "--abbrev-ref", "HEAD"]) + collect_text(["git", "rev-parse", "HEAD"]),
    )
    write_text(paths.file("processes-before.txt"), collect_text(["ps", "-eo", "pid,ppid,stat,comm,args"]))
    lsusb_before = collect_text(["lsusb"])
    write_text(paths.file("lsusb-before.txt"), lsusb_before)
    write_text(paths.file("kernel-usb-before.txt"), collect_text(["dmesg", "--ctime"], timeout=10)[-8000:])

    do_pre_cleanup = dry_run or run_command is ORIGINAL_RUN_COMMAND or not should_use_live_launch()
    cleanup_before_ok = cleanup_related_processes() if (not dry_run and do_pre_cleanup) else True
    if settle_secs > 0 and not dry_run:
        time.sleep(settle_secs)

    usb_reset_log = maybe_reset_kinect_usb(group, lsusb_before, dry_run)

    if dry_run:
        launch_log = "DRY_RUN would execute: ros2 launch talus_bringup kinect.launch.py driver_mode:=unified enable_point_cloud:=false\n"
        launch_exit = 0
        topics = {"/image_raw", "/depth/image_raw"}
        rgb_ok = True
        depth_ok = True
        topics_text = "/image_raw\n/depth/image_raw\n"
        collector_error = None
    else:
        round_runner = run_live_launch_round if should_use_live_launch() else run_blocking_launch_round
        launch_exit, launch_log, topics, rgb_ok, depth_ok, collector_error, topics_text, _extra = round_runner()

    cleanup_after_ok = cleanup_related_processes() if not dry_run else True
    cleanup_ok = cleanup_before_ok and cleanup_after_ok

    write_text(paths.file("topic-list.txt"), topics_text)
    write_text(paths.file("kinect-launch.log"), usb_reset_log + launch_log)
    write_text(paths.file("rgb-sample.txt"), "OK\n" if rgb_ok else "TIMEOUT\n")
    write_text(paths.file("depth-sample.txt"), "OK\n" if depth_ok else "TIMEOUT\n")
    write_text(paths.file("topic-hz.txt"), "manual: inspect if needed; runner validates real messages via sampler\n")
    lsusb_after = collect_text(["lsusb"])
    write_text(paths.file("lsusb-after.txt"), lsusb_after)
    write_text(paths.file("processes-after.txt"), collect_text(["ps", "-eo", "pid,ppid,stat,comm,args"]))
    write_text(paths.file("kernel-usb-after.txt"), collect_text(["dmesg", "--ctime"], timeout=10)[-8000:])

    signals = RoundSignals(
        usb_present_before=True if dry_run else has_kinect(lsusb_before),
        usb_present_after=True if dry_run else has_kinect(lsusb_after),
        launch_exit_code=launch_exit,
        launch_log=launch_log,
        topics_seen=topics,
        rgb_sample_ok=rgb_ok,
        depth_sample_ok=depth_ok,
        cleanup_ok=cleanup_ok,
        collector_error=collector_error,
    )
    status = classify_round(signals)
    write_round_summary(paths, status, serialize_signals(signals))
    return 0 if status.value == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Talus-Droid Kinect validation diagnostics.")
    parser.add_argument("mode", choices=["isolated", "matrix", "preflight", "usb-reset"], help="Diagnostic mode to run")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--settle-rounds", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.mode == "preflight":
        plan = build_preflight_plan()
    elif args.mode == "matrix":
        plan = build_matrix_plan(default_rounds=args.rounds, settle_rounds=args.settle_rounds)
    elif args.mode == "isolated":
        plan = [MatrixItem("isolated-default", 0, args.rounds)]
    else:
        plan = [MatrixItem("usb-reset", 5, 1)]

    failures = 0
    for item in plan:
        for round_number in range(1, item.rounds + 1):
            failures += run_one_round(args.artifact_root, item.group, round_number, item.settle_secs, dry_run=args.dry_run)
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
