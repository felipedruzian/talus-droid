from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class GroupSummary:
    group: str
    rounds: int
    passes: int
    dominant_failure: str


def aggregate_groups(root: Path) -> list[GroupSummary]:
    statuses_by_group: dict[str, list[str]] = defaultdict(list)
    for summary_file in sorted(root.glob("*/round-*/summary.json")):
        payload = json.loads(summary_file.read_text())
        statuses_by_group[payload["group"]].append(payload["status"])

    rows: list[GroupSummary] = []
    for group, statuses in sorted(statuses_by_group.items()):
        failures = [status for status in statuses if status != "PASS"]
        dominant = "none" if not failures else Counter(failures).most_common(1)[0][0]
        rows.append(GroupSummary(group=group, rounds=len(statuses), passes=statuses.count("PASS"), dominant_failure=dominant))
    return rows


def render_markdown_table(rows: list[GroupSummary]) -> str:
    lines = [
        "| Grupo | Rodadas | PASS | Falha dominante | Observação |",
        "|---|---:|---:|---|---|",
    ]
    for row in rows:
        observation = "aguardando análise dos logs"
        lines.append(f"| `{row.group}` | {row.rounds} | {row.passes} | {row.dominant_failure} | {observation} |")
    return "\n".join(lines) + "\n"
