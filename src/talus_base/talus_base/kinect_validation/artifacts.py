from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .status import KinectStatus

ROUND_FILES = (
    "metadata.txt",
    "env.txt",
    "git.txt",
    "lsusb-before.txt",
    "lsusb-after.txt",
    "processes-before.txt",
    "processes-after.txt",
    "kernel-usb-before.txt",
    "kernel-usb-after.txt",
    "kinect-launch.log",
    "topic-list.txt",
    "rgb-sample.txt",
    "depth-sample.txt",
    "topic-hz.txt",
    "classification.txt",
    "summary.json",
)


@dataclass(frozen=True)
class RoundArtifactPaths:
    root: Path
    group: str
    round_number: int

    @property
    def round_dir(self) -> Path:
        return self.root / self.group / f"round-{self.round_number:03d}"

    def ensure(self) -> None:
        self.round_dir.mkdir(parents=True, exist_ok=True)

    def file(self, name: str) -> Path:
        if name not in ROUND_FILES:
            raise ValueError(f"Unknown Kinect validation artifact: {name}")
        return self.round_dir / name


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n")


def write_round_summary(paths: RoundArtifactPaths, status: KinectStatus, signals: dict[str, Any]) -> None:
    write_text(paths.file("classification.txt"), status.value)
    payload = {
        "group": paths.group,
        "round": paths.round_number,
        "status": status.value,
        "signals": signals,
    }
    paths.file("summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
