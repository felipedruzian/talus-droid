# Kinect Validation Diagnostic Procedure

Date: 2026-04-27  
Target host: `raspi`  
Workspace: `/home/felip/talus-droid`  
Branch: `diag/2026-04-27-kinect-validation`

## Purpose

Validate Kinect v1 bring-up independently from IMU, visual odometry, and RTAB-Map. A Kinect open/start failure must be classified as a Kinect/USB/cleanup failure, not as SLAM failure.

This diagnostic flow is part of the Talus-Droid robot platform. Optional build/test support may run on the Talus host, but real Kinect hardware validation remains `raspi`-only.

Current gate as of 2026-05-02: validate Kinect RGB-D stability before any `odom_test`, RTAB-Map, VO, or SLAM conclusion. If `preflight` fails with `RGB_TIMEOUT`, `KINECT_OPEN_FAIL`, `USB_BUSY`, or `USB_MISSING`, keep the work in Kinect/USB/libfreenect/driver diagnostics and do not continue to VO/SLAM.

## Preflight definition

In this project, **preflight** is the minimum readiness check for the Kinect before any higher-level test.

It means:

- the unified Kinect driver starts on `raspi`;
- expected topics are visible;
- `/image_raw` publishes at least one real RGB message;
- `/depth/image_raw` publishes at least one real depth message;
- the Kinect USB camera remains present before and after the round;
- cleanup leaves no relevant Kinect/launch/TF processes alive.

Preflight has two valid uses:

- as a **validation gate**: if it passes, a repeated battery may be run before testing higher layers;
- as an **investigation target**: if it fails, the failure is still a valid diagnostic result and should be captured as a run bundle.

The run bundle standard is documented in [raspi-experiment-flow.md](raspi-experiment-flow.md). New relevant Kinect tests should use:

```text
artifacts/testlogs/YYYY-MM-DD-kinect-validation/raspi-vNN-description/
  experiment.yaml
  notes.md
  preflight/round-001/
```

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

Use a dedicated run bundle for new tests. Example:

```text
artifacts/testlogs/2026-05-01-kinect-validation/raspi-v10-baseline-medium/
```

Older artifacts remain under their original paths unless explicitly reorganized with updated report links.

## Build

Optional support step on `talus` or another non-hardware host for package/build sanity only. Real execution of the diagnostic phases below remains `raspi`-only.

```bash
colcon build --symlink-install --packages-select talus_base talus_bringup
source install/setup.bash
```

## Phase 1: Snapshot and isolated battery

Use this phase after `preflight` passes, or when explicitly running a Kinect-focused diagnostic battery to characterize a failing condition. In the second case, the run is a Kinect investigation, not a validation of VO/SLAM readiness.

```bash
ros2 run talus_base talus_kinect_validate isolated --rounds 10
```

Initial criterion:

- ideal: 10/10 `PASS`
- acceptable to consider controlled investigation of higher layers: at least 8/10 `PASS`
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
ros2 run talus_base talus_kinect_validate preflight \
  --artifact-root artifacts/testlogs/YYYY-MM-DD-kinect-validation/raspi-vNN-description
```

Only if preflight passes:

```bash
./scripts/talus-up odom_test
./scripts/talus-up floor_test
ros2 launch talus_bringup slam_rtabmap.launch.py rtabmap_viz:=false rviz:=false
```

If preflight fails, abort the larger test and copy the classification into `docs/reports/2026-04-27-kinect-validation.md`.

If the purpose of the run is Kinect investigation, keep the run active and record the failure in `experiment.yaml` and `notes.md` instead of advancing to VO/SLAM.

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
