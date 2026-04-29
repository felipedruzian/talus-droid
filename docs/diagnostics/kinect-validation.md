# Kinect Validation Diagnostic Procedure

Date: 2026-04-27  
Target host: `raspi`  
Workspace: `/home/felip/talus-droid`  
Branch: `diag/2026-04-27-kinect-validation`

## Purpose

Validate Kinect v1 bring-up independently from IMU, visual odometry, and RTAB-Map. A Kinect open/start failure must be classified as a Kinect/USB/cleanup failure, not as SLAM failure.

This diagnostic flow is part of the Talus-Droid robot platform. Optional build/test support may run on the Talus host, but real Kinect hardware validation remains `raspi`-only.

Current gate as of 2026-04-29: run `preflight` before any larger battery or `odom_test`. If `preflight` fails with `RGB_TIMEOUT`, keep the work in Kinect/USB/driver diagnostics and do not continue to VO/SLAM.

## Environment

```bash
cd ~/talus-droid
source /opt/ros/jazzy/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=42
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export TALUS_KINECT_DRIVER_MODE=unified
export TALUS_KINECT_ENABLE_POINT_CLOUD=false
```

## Artifact root

```text
artifacts/testlogs/2026-04-27-kinect-validation/raspi/
```

## Build

Optional support step on `talus` or another non-hardware host for package/build sanity only. Real execution of the diagnostic phases below remains `raspi`-only.

```bash
colcon build --symlink-install --packages-select talus_base talus_bringup
source install/setup.bash
```

## Phase 1: Snapshot and isolated battery

Use this phase only after `preflight` passes or when explicitly running a Kinect-focused diagnostic battery.

```bash
ros2 run talus_base talus_kinect_validate isolated --rounds 10
```

Initial criterion:

- ideal: 10/10 `PASS`
- acceptable to keep investigating higher layers: at least 8/10 `PASS`
- below 8/10: continue focusing on USB/driver/cleanup, not SLAM

## Phase 2: Settle matrix

```bash
ros2 run talus_base talus_kinect_validate matrix --rounds 10 --settle-rounds 5
```

Groups:

| Group | Settle | Repetitions |
|---|---:|---:|
| `isolated-default` | 0s | 10 |
| `settle-10s` | 10s | 5 |
| `settle-30s` | 30s | 5 |
| `settle-60s` | 60s | 5 |

## Phase 3: Optional USB reset

Run only as an explicit opt-in diagnostic path if the Kinect remains listed by USB but fails to open after normal cleanup. This is only a safe command-level reset attempt, not a mandatory baseline step. Real execution remains `raspi`-only.

```bash
ros2 run talus_base talus_kinect_validate usb-reset
```

## Phase 4: Preflight before larger tests

```bash
ros2 run talus_base talus_kinect_validate preflight
```

Only if preflight passes:

```bash
./scripts/talus-up odom_test
./scripts/talus-up floor_test
ros2 launch talus_bringup slam_rtabmap.launch.py rtabmap_viz:=false rviz:=false
```

If preflight fails, abort the larger test and copy the classification into `docs/reports/2026-04-27-kinect-validation.md`.

## Classification codes

| Code | Meaning |
|---|---|
| `PASS` | RGB and depth published real messages and cleanup finished cleanly |
| `USB_MISSING` | Kinect camera ID `045e:02ae` not present in `lsusb` before or after the round |
| `USB_BUSY` | Device present but likely held by previous process/libusb state |
| `KINECT_OPEN_FAIL` | Driver/node failed to open Kinect |
| `RGB_TIMEOUT` | `/image_raw` did not publish a real message in time |
| `DEPTH_TIMEOUT` | `/depth/image_raw` did not publish a real message in time |
| `TOPIC_TIMEOUT` | Expected topics did not appear/publish in time |
| `CLEANUP_FAIL` | Processes remained alive after shutdown |
| `COLLECTOR_FAIL` | Diagnostic collector/sampler failed |
