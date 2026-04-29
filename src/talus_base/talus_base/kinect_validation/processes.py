from __future__ import annotations

RELEVANT_PROCESS_TOKENS = (
    "kinect",
    "freenect",
    "rtabmap",
    "rgbd_odometry",
    "talus_bringup",
    "ros2 launch talus_bringup",
)

IGNORED_DIAGNOSTIC_TOKENS = (
    "talus_kinect_validate",
    "talus_kinect_sample_image",
    "talus_base.kinect_validation.runner",
    "talus_base.kinect_validation.sampler",
)


def find_relevant_process_lines(ps_text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in ps_text.splitlines():
        line = raw_line.strip()
        if not line or line.upper().startswith("PID "):
            continue
        lower = line.lower()
        if any(token in lower for token in IGNORED_DIAGNOSTIC_TOKENS):
            continue
        if any(token in lower for token in RELEVANT_PROCESS_TOKENS):
            lines.append(line)
    return lines
