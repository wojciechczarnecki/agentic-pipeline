#!/usr/bin/env python3
# Summarises the `metrics:` blocks of <specs>/*/SPEC.md into a markdown table, so changes to
# the agentic workflow are judged by numbers. Without an argument the spec directory comes
# from .claude/workflow.json (`docs.specsDir`).
# Usage: python3 workflow_metrics.py [dir]
#        python3 workflow_metrics.py --check <spec-dir>
# Exit codes: 0 — report rendered, or --check found nothing wrong; 1 — --check found a
# problem (every one named on stderr), an unreadable spec directory or a broken
# workflow.json; 2 — argparse rejected the arguments.
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow_config  # noqa: E402

REQUIRED_DONE_COUNTERS = [
    "plan_steps",
    "plan_review_blockers",
    "plan_review_majors",
    "plan_changes",
    "implement_steps",
    "implement_iterations",
    "escalations",
    "final_review_blockers",
    "final_review_worth_fixing",
    "final_review_nits",
    "findings_accepted",
    "findings_rejected",
]
COST_KEYS = {
    "plan": "cost_plan_cents",
    "plan-review": "cost_plan_review_cents",
    "implement": "cost_implement_cents",
    "final-review": "cost_final_review_cents",
}
COUNTERS = [
    "plan_steps",
    "plan_review_blockers",
    "plan_review_majors",
    "plan_changes",
    "implement_steps",
    "implement_iterations",
    "converge_gaps",
    "deviations",
    "deviations_minor",
    "deviations_major",
    "escalations",
    "final_review_blockers",
    "final_review_worth_fixing",
    "final_review_nits",
    "findings_accepted",
    "findings_rejected",
    *COST_KEYS.values(),
]
# `deviations` or both split keys: the split arrived in SPEC 011, and nobody guesses it for
# specs that recorded the old key.
DEVIATION_FORMS = ("deviations", ("deviations_minor", "deviations_major"))
DEVIATIONS_DUE = ("implemented", "done")
TOKEN_TYPES = ("input", "cache_write_5m", "cache_write_1h", "cache_read", "output")
# API list rates of RATES_DATE in cents per million tokens, in TOKEN_TYPES order. Existing
# rates are never changed, even when prices move: a cent here is a fixed unit, so costs from
# different years stay comparable. A new model is only added, at its launch rates.
RATES_DATE = "2026-09-24"
RATES: dict[str, tuple[int, int, int, int, int]] = {
    "claude-opus-5-5": (400, 500, 800, 20, 2000),
    "claude-opus-5": (500, 625, 1000, 50, 2500),
    "claude-sonnet-5": (200, 250, 400, 20, 1000),
    "claude-haiku-4-5": (100, 125, 200, 10, 500),
    "claude-fable-5-1": (1000, 1250, 2000, 25, 5000),
}
MODEL_DATE = re.compile(r"-\d{8}$")


def _count(value: object) -> int:
    return value if isinstance(value, int) and value > 0 else 0


def usage_tokens(usage: dict) -> tuple[int, ...]:
    split = usage.get("cache_creation")
    if isinstance(split, dict):
        write_5m = _count(split.get("ephemeral_5m_input_tokens"))
        write_1h = _count(split.get("ephemeral_1h_input_tokens"))
    else:
        write_5m, write_1h = _count(usage.get("cache_creation_input_tokens")), 0
    return (
        _count(usage.get("input_tokens")),
        write_5m,
        write_1h,
        _count(usage.get("cache_read_input_tokens")),
        _count(usage.get("output_tokens")),
    )


def rate_for(model: str) -> tuple[int, ...] | None:
    return RATES.get(MODEL_DATE.sub("", model))


# Integer arithmetic and one rounding (half up) of the stage total: rounding per message or
# per model would lose sub-cent amounts that add up.
def stage_cents(tokens_by_model: dict[str, list[int]]) -> int | None:
    numerator = 0
    for model, tokens in tokens_by_model.items():
        rates = rate_for(model)
        if rates is None:
            return None
        numerator += sum(count * rate for count, rate in zip(tokens, rates, strict=True))
    return (numerator + 500_000) // 1_000_000


STAGE_AGENTS = {
    "planner": "plan",
    "plan-reviewer": "plan-review",
    "implementer": "implement",
    "reviewer": "final-review",
}


def stage_of(agent_type: object) -> str | None:
    if not isinstance(agent_type, str):
        return None
    return STAGE_AGENTS.get(agent_type.removeprefix("pipeline:"))


def git_path(directory: Path, *args: str) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--path-format=absolute", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    output = result.stdout.strip()
    return Path(output) if result.returncode == 0 and output else None


# Where a stage agent of this repository may have run: the spec's own checkout, the main
# checkout, and the configured worktree directory, where lanes live under a project slug of
# their own.
def repository_roots(spec_dir: Path) -> list[Path]:
    spec_dir = spec_dir.resolve()
    checkout = git_path(spec_dir, "--show-toplevel") or workflow_config.project_root(spec_dir)
    common = git_path(spec_dir, "--git-common-dir")
    main_root = common.parent if common else checkout
    roots = [checkout, main_root]
    try:
        config, _ = workflow_config.load_sections(main_root)
        lanes = config.get("worktree.dir")
    except workflow_config.ConfigError:
        lanes = None
    if not isinstance(lanes, str) or Path(lanes).is_absolute():
        lanes = workflow_config.defaults()["worktree"]["dir"]
    roots.append((main_root / lanes).resolve())
    return [root.resolve() for root in roots]


def read_lines(path: Path):
    try:
        with path.open() as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    yield entry
    except OSError:
        return


def prompt_and_cwd(path: Path) -> tuple[str, str]:
    for entry in read_lines(path):
        message = entry.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            content = " ".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            )
        cwd = entry.get("cwd")
        return (content if isinstance(content, str) else ""), (cwd if isinstance(cwd, str) else "")
    return "", ""


def find_agents(source: Path) -> dict[str, tuple[dict, list[Path]]]:
    agents: dict[str, tuple[dict, list[Path]]] = {}
    for meta_path in sorted(source.rglob("agent-*.meta.json")):
        if meta_path.parent.name != "subagents":
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict):
            continue
        agent_id = meta_path.name.removeprefix("agent-").removesuffix(".meta.json")
        transcript = meta_path.with_name(f"agent-{agent_id}.jsonl")
        known = agents.setdefault(agent_id, (meta, []))
        if transcript.is_file():
            known[1].append(transcript)
    return agents


# A stage agent belongs to this spec when its type is a stage agent, its prompt names the spec
# directory as a whole path segment, and it ran inside this repository: a spec with the same
# number, or even the same name, in another repository is not counted. Its descendants (the
# final review's perspectives, the converge pass) count toward its stage.
def stage_usage(spec_dir: Path, source: Path) -> dict[str, dict[str, list[int]]]:
    agents = find_agents(source)
    name = re.compile(rf"(?<![\w.-]){re.escape(spec_dir.resolve().name)}(?![\w.-])")
    roots = repository_roots(spec_dir)
    stage_agents: dict[str, str] = {}
    for agent_id, (meta, transcripts) in agents.items():
        stage = stage_of(meta.get("agentType"))
        if stage is None or not transcripts:
            continue
        text, cwd = prompt_and_cwd(transcripts[0])
        if not cwd or not name.search(text):
            continue
        where = Path(cwd).resolve()
        if any(where.is_relative_to(root) for root in roots):
            stage_agents[agent_id] = stage

    def owning_stage(agent_id: str) -> str | None:
        seen = set()
        while agent_id and agent_id not in seen:
            if agent_id in stage_agents:
                return stage_agents[agent_id]
            seen.add(agent_id)
            parent = agents.get(agent_id, ({}, []))[0].get("parentAgentId")
            agent_id = parent if isinstance(parent, str) else ""
        return None

    messages: dict[str, tuple[str, str, tuple[int, ...]]] = {}
    for agent_id, (_, transcripts) in agents.items():
        stage = owning_stage(agent_id)
        if stage is None:
            continue
        for transcript in transcripts:
            for entry in read_lines(transcript):
                message = entry.get("message")
                if entry.get("type") != "assistant" or not isinstance(message, dict):
                    continue
                model, usage, key = message.get("model"), message.get("usage"), message.get("id")
                if not isinstance(model, str) or model == "<synthetic>":
                    continue
                if not isinstance(usage, dict) or not isinstance(key, str):
                    continue
                tokens = usage_tokens(usage)
                if key not in messages or tokens[-1] > messages[key][2][-1]:
                    messages[key] = (stage, model, tokens)
    stages: dict[str, dict[str, list[int]]] = {}
    for stage, model, tokens in messages.values():
        totals = stages.setdefault(stage, {}).setdefault(model, [0] * len(TOKEN_TYPES))
        for index, count in enumerate(tokens):
            totals[index] += count
    return stages


FRONTMATTER = re.compile(r"---\n(.*?)\n---", re.DOTALL)
TIME_FORMAT = "%Y-%m-%dT%H:%M"
TIMESTAMPS = ("started_at", "finished_at")
_PLAN_DRAFT = ["started_at", "escalations", "plan_steps"]
_PLAN_APPROVED = _PLAN_DRAFT + ["plan_review_blockers", "plan_review_majors", "plan_changes"]
_IMPLEMENTED = _PLAN_APPROVED + ["implement_steps", "implement_iterations"]
REQUIRED: dict[str, list[str]] = {
    "spec-draft": [],
    "spec-ready": [],
    "plan-draft": _PLAN_DRAFT,
    "plan-approved": _PLAN_APPROVED,
    "implemented": _IMPLEMENTED,
    "done": ["started_at", "finished_at", *REQUIRED_DONE_COUNTERS],
}
BALANCE = (
    ("findings_accepted", "findings_rejected"),
    ("final_review_blockers", "final_review_worth_fixing", "final_review_nits"),
)


def parse_metrics(text: str) -> dict[str, str]:
    match = FRONTMATTER.match(text)
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
    match = FRONTMATTER.match(text)
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
    if not FRONTMATTER.match(text):
        return [f"{spec} has no frontmatter"]
    status = parse_status(text)
    if status is None:
        return [f"{spec}: frontmatter has no `status` key"]
    if status not in REQUIRED:
        return [f'{spec}: unknown status "{status}"']

    metrics = parse_metrics(text)
    problems = []
    missing = [key for key in REQUIRED[status] if not metrics.get(key)]
    if missing:
        problems.append(
            f"status `{status}` requires metric keys that are missing: " + ", ".join(missing)
        )
    old, split = DEVIATION_FORMS
    if status in DEVIATIONS_DUE and not (
        metrics.get(old) or all(metrics.get(key) for key in split)
    ):
        problems.append(
            f"status `{status}` requires either `{old}` or both `{split[0]}` and `{split[1]}`"
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
    unknown = [key for key in metrics if key not in (*COUNTERS, *TIMESTAMPS)]
    if unknown:
        problems.append(
            "metrics holds keys that are not metrics (a typo drops the value silently): "
            + ", ".join(sorted(unknown))
        )
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
        try:
            text = spec.read_text()
        except OSError as exc:
            print(f"{spec} cannot be read, skipped: {exc}", file=sys.stderr)
            continue
        metrics = parse_metrics(text)
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
    lines.extend(cost_lines([metrics for _, metrics in rows]))
    return "\n".join(lines)


def integer(metrics: dict[str, str], key: str) -> int:
    value = metrics.get(key, "")
    return int(value) if value.isdigit() else 0


def per_unit(label: str, cents: int, units: int) -> list[str]:
    if units <= 0:
        return []
    return [f"{label}: {(2 * cents + units) // (2 * units)} cents ({cents}/{units})"]


# Each line only counts specs that carry its cost, so a spec costed on another machine, or
# before 0.8.0, adds nothing to the numerator or the denominator.
def cost_lines(specs: list[dict[str, str]]) -> list[str]:
    lines = []
    for label, cost, findings in (
        (
            "Plan review cost per significant finding",
            COST_KEYS["plan-review"],
            ("plan_review_blockers", "plan_review_majors"),
        ),
        (
            "Final review cost per significant finding",
            COST_KEYS["final-review"],
            ("final_review_blockers", "final_review_worth_fixing"),
        ),
    ):
        costed = [metrics for metrics in specs if metrics.get(cost, "").isdigit()]
        cents = sum(int(metrics[cost]) for metrics in costed)
        units = sum(integer(metrics, key) for metrics in costed for key in findings)
        lines.extend(per_unit(label, cents, units))
    complete = [
        metrics
        for metrics in specs
        if all(metrics.get(key, "").isdigit() for key in COST_KEYS.values())
    ]
    cents = sum(int(metrics[key]) for metrics in complete for key in COST_KEYS.values())
    steps = sum(integer(metrics, "plan_steps") for metrics in complete)
    lines.extend(per_unit("Cost per plan step", cents, steps))
    return lines


# Section-wise, like the hooks: a key that fails validation (a `language` outside the
# supported ones) only warns and falls back to its default instead of stopping the report.
def configured_specs_dir(start: Path) -> Path:
    config, problems = workflow_config.load_sections(start)
    for problem in problems:
        print(f"workflow.json: {problem}", file=sys.stderr)
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
    if not specs_dir.is_dir():
        print(f"{specs_dir} is not a directory", file=sys.stderr)
        return 1
    print(render(collect(specs_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
