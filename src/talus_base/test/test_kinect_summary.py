import json
from pathlib import Path

from talus_base.kinect_validation.summary import aggregate_groups, render_markdown_table


def write_summary(root: Path, group: str, round_name: str, status: str) -> None:
    round_dir = root / group / round_name
    round_dir.mkdir(parents=True)
    (round_dir / "summary.json").write_text(json.dumps({"group": group, "round": 1, "status": status}) + "\n")


def test_aggregate_groups_counts_status_and_dominant_failure(tmp_path: Path):
    write_summary(tmp_path, "isolated-default", "round-001", "PASS")
    write_summary(tmp_path, "isolated-default", "round-002", "RGB_TIMEOUT")
    write_summary(tmp_path, "isolated-default", "round-003", "RGB_TIMEOUT")

    rows = aggregate_groups(tmp_path)
    assert rows[0].group == "isolated-default"
    assert rows[0].rounds == 3
    assert rows[0].passes == 1
    assert rows[0].dominant_failure == "RGB_TIMEOUT"


def test_render_markdown_table_contains_required_columns(tmp_path: Path):
    write_summary(tmp_path, "settle-60s", "round-001", "PASS")
    table = render_markdown_table(aggregate_groups(tmp_path))
    assert "| Grupo | Rodadas | PASS | Falha dominante | Observação |" in table
    assert "| `settle-60s` | 1 | 1 | none |" in table
