import json
from pathlib import Path

from talus_base.kinect_validation.artifacts import ROUND_FILES, RoundArtifactPaths, write_round_summary
from talus_base.kinect_validation.status import KinectStatus


def test_round_artifact_paths_create_expected_directory_and_files(tmp_path: Path):
    paths = RoundArtifactPaths(root=tmp_path, group="settle-10s", round_number=3)
    assert paths.round_dir == tmp_path / "settle-10s" / "round-003"
    paths.ensure()
    assert paths.round_dir.is_dir()
    assert set(ROUND_FILES) >= {"metadata.txt", "classification.txt", "kinect-launch.log"}


def test_write_round_summary_writes_text_and_json(tmp_path: Path):
    paths = RoundArtifactPaths(root=tmp_path, group="isolated-default", round_number=1)
    paths.ensure()
    write_round_summary(paths, KinectStatus.PASS, {"settle_secs": 0, "rgb_sample_ok": True})

    assert (paths.round_dir / "classification.txt").read_text() == "PASS\n"
    data = json.loads((paths.round_dir / "summary.json").read_text())
    assert data["status"] == "PASS"
    assert data["group"] == "isolated-default"
    assert data["round"] == 1
    assert data["signals"]["rgb_sample_ok"] is True
