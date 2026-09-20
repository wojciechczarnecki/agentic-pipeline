#!/usr/bin/env python3
# Summarises the `metrics:` blocks of <specs>/*/SPEC.md into a markdown table, so changes to
# the agentic workflow are judged by numbers. Without an argument the spec directory comes
# from .claude/workflow.json (`docs.specsDir`).
# Usage: python3 workflow_metrics.py [dir]
#        python3 workflow_metrics.py --check <spec-dir>
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow_config  # noqa: E402

COUNTERS = [
    "plan_steps",
    "plan_review_blockers",
    "plan_review_majors",
    "plan_changes",
    "implement_steps",
    "implement_iterations",
    "deviations",
    "escalations",
    "final_review_blockers",
    "final_review_worth_fixing",
    "final_review_nits",
    "findings_accepted",
    "findings_rejected",
]
TIME_FORMAT = "%Y-%m-%dT%H:%M"
TIMESTAMPS = ("started_at", "finished_at")
_PLAN_DRAFT = ["started_at", "escalations", "plan_steps"]
_PLAN_APPROVED = _PLAN_DRAFT + ["plan_review_blockers", "plan_review_majors", "plan_changes"]
_IMPLEMENTED = _PLAN_APPROVED + ["implement_steps", "implement_iterations", "deviations"]
REQUIRED: dict[str, list[str]] = {
    "spec-draft": [],
    "spec-ready": [],
    "plan-draft": _PLAN_DRAFT,
    "plan-approved": _PLAN_APPROVED,
    "implemented": _IMPLEMENTED,
    "done": ["started_at", "finished_at", *COUNTERS],
}
BALANCE = (
    ("findings_accepted", "findings_rejected"),
    ("final_review_blockers", "final_review_worth_fixing", "final_review_nits"),
)


def parse_metrics(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    metrics: dict[str, str] = {}
    inside = False
    for line in match.group(1).splitlines():
        if not line.startswith(" "):
            inside = line.strip() == "metrics:"
        elif inside and ":" in line:
            key, value = line.strip().split(":", 1)
            metrics[key.strip()] = value.strip().strip("\"'")
    return metrics


def parse_status(text: str) -> str | None:
    match = re.match(r"---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return None
    for line in match.group(1).splitlines():
        if line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() == "status":
            return value.strip().strip("\"'")
    return None


def check(spec_dir: Path) -> list[str]:
    spec = spec_dir / "SPEC.md"
    if not spec.is_file():
        return [f"no SPEC.md in {spec_dir}"]
    try:
        text = spec.read_text()
    except OSError as exc:
        return [f"{spec} cannot be read: {exc}"]
    if not re.match(r"---\n(.*?)\n---", text, re.DOTALL):
        return [f"{spec} has no frontmatter"]
    status = parse_status(text)
    if status is None:
        return [f"{spec} has no frontmatter"]
    if status not in REQUIRED:
        return [f'{spec}: unknown status "{status}"']

    metrics = parse_metrics(text)
    problems = []
    missing = [key for key in REQUIRED[status] if not metrics.get(key)]
    if missing:
        problems.append(
            f"status `{status}` requires metric keys that are missing: " + ", ".join(missing)
        )
    for key in TIMESTAMPS:
        value = metrics.get(key)
        if not value:
            continue
        try:
            datetime.strptime(value, TIME_FORMAT)
        except ValueError:
            problems.append(f'metrics.{key} "{value}" does not match {TIME_FORMAT}')
    for key in COUNTERS:
        if key not in metrics:
            continue
        value = metrics[key]
        if not re.fullmatch(r"\d+", value):
            problems.append(f'metrics.{key} "{value}" is not a non-negative integer')
    balance_keys = [key for group in BALANCE for key in group]
    if all(re.fullmatch(r"\d+", metrics.get(key, "")) for key in balance_keys):
        left = sum(int(metrics[key]) for key in BALANCE[0])
        right = sum(int(metrics[key]) for key in BALANCE[1])
        if left != right:
            problems.append(
                f"decided findings ({' + '.join(BALANCE[0])} = {left}) do not match the findings "
                f"reported ({' + '.join(BALANCE[1])} = {right})"
            )
    return [f"{spec_dir.name}: {problem}" for problem in problems]


def lead_time_hours(metrics: dict[str, str]) -> float | None:
    try:
        started = datetime.strptime(metrics["started_at"], TIME_FORMAT)
        finished = datetime.strptime(metrics["finished_at"], TIME_FORMAT)
    except (KeyError, ValueError):
        return None
    return round((finished - started).total_seconds() / 3600, 1)


def collect(specs_dir: Path) -> list[tuple[str, dict[str, str]]]:
    rows = []
    for spec in sorted(specs_dir.glob("*/SPEC.md")):
        metrics = parse_metrics(spec.read_text())
        if metrics:
            rows.append((spec.parent.name, metrics))
    return rows


def ratio(part: int, whole: int) -> str:
    return f"{part / whole:.0%} ({part}/{whole})"


def render(rows: list[tuple[str, dict[str, str]]]) -> str:
    if not rows:
        return "No spec carries a metrics block yet."
    header = ["spec", "lead_time_h", *COUNTERS]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    totals = dict.fromkeys(COUNTERS, 0)
    for name, metrics in rows:
        hours = lead_time_hours(metrics)
        cells = [name, "-" if hours is None else str(hours)]
        for key in COUNTERS:
            value = metrics.get(key, "")
            cells.append(value or "-")
            if value.isdigit():
                totals[key] += int(value)
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("| **total** | - | " + " | ".join(str(totals[key]) for key in COUNTERS) + " |")

    lines.append("")
    early = totals["plan_review_blockers"] + totals["plan_review_majors"]
    late = totals["final_review_blockers"] + totals["final_review_worth_fixing"]
    if early + late:
        lines.append(f"Significant findings caught before code: {ratio(early, early + late)}")
    accepted = totals["findings_accepted"]
    decided = accepted + totals["findings_rejected"]
    if decided:
        lines.append(f"Final-review findings accepted: {ratio(accepted, decided)}")
    lines.append(f"Escalations per spec: {totals['escalations'] / len(rows):.1f}")
    return "\n".join(lines)


def configured_specs_dir(start: Path) -> Path:
    config = workflow_config.load(start)
    root = config.root or workflow_config.project_root(start)
    return root / (config.get("docs.specsDir") or "specs")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Report or check workflow metrics.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("directory", nargs="?")
    args = parser.parse_args(argv[1:])

    if args.check:
        if not args.directory:
            print("usage: workflow_metrics.py --check <spec-dir>", file=sys.stderr)
            return 1
        problems = check(Path(args.directory))
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0

    if args.directory:
        specs_dir = Path(args.directory)
    else:
        try:
            specs_dir = configured_specs_dir(Path.cwd())
        except workflow_config.ConfigError as exc:
            print(f"workflow.json: {exc}", file=sys.stderr)
            return 1
    print(render(collect(specs_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
