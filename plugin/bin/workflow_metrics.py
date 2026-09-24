#!/usr/bin/env python3
# Summarises the `metrics:` blocks of <specs>/*/SPEC.md into a markdown table, so changes to
# the agentic workflow are judged by numbers. Without an argument the spec directory comes
# from .claude/workflow.json (`docs.specsDir`).
# With --record-cost it prices the spec's stage subagents from Claude Code's transcripts and
# writes the four `cost_*` keys into its SPEC.md.
# Usage: python3 workflow_metrics.py [dir]
#        python3 workflow_metrics.py --check <spec-dir>
#        python3 workflow_metrics.py --record-cost <spec-dir> [--transcripts <dir>]
# Exit codes: 0 — report rendered, --check found nothing wrong, or --record-cost finished
# (missing transcripts and unknown models only warn); 1 — --check found a problem (every one
# named on stderr), an unreadable spec directory or a broken workflow.json; 2 — argparse
# rejected the arguments.
import argparse
import json
import os
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


# A transcript still being written, or left by a crashed session, can end inside a multi-byte
# character: `errors="replace"` keeps that from stopping the whole run.
def read_lines(path: Path):
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    yield entry
    except OSError:
        return


# The prompt is the first `user` entry: an entry of another type written ahead of it must not
# hide the agent.
def prompt_and_cwd(path: Path) -> tuple[str, str]:
    for entry in read_lines(path):
        if entry.get("type") != "user":
            continue
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
            meta = json.loads(meta_path.read_text(encoding="utf-8", errors="replace"))
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
# `estimates`, when given, gets per stage the logged output tokens and an estimate from the
# content (see `content_tokens`).
def stage_usage(
    spec_dir: Path, source: Path, estimates: dict[str, list[int]] | None = None
) -> dict[str, dict[str, list[int]]]:
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
    blocks: dict[str, set[str]] = {}
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
                content = message.get("content")
                if isinstance(content, list):
                    blocks.setdefault(key, set()).update(
                        json.dumps(block, sort_keys=True) for block in content
                    )
    stages: dict[str, dict[str, list[int]]] = {}
    for key, (stage, model, tokens) in messages.items():
        totals = stages.setdefault(stage, {}).setdefault(model, [0] * len(TOKEN_TYPES))
        for index, count in enumerate(tokens):
            totals[index] += count
        if estimates is not None:
            estimate = estimates.setdefault(stage, [0, 0])
            estimate[0] += tokens[-1]
            estimate[1] += content_tokens(blocks.get(key, set()))
    return stages


# Claude Code often logs a message's `output_tokens` from the start of the stream, not its
# final count, so the logged output is a lower bound. Characters / 4 of the logged content is
# a rough size of what the model wrote, used only to warn, never to price.
def content_tokens(blocks: set[str]) -> int:
    return sum(len(block) for block in blocks) // 4


# Warn when the content is at least twice the logged output and more than 1000 tokens apart,
# so small or empty messages stay quiet.
def output_shortfall(stage: str, logged: int, estimated: int) -> str | None:
    if estimated < 2 * logged or estimated - logged <= 1000:
        return None
    return (
        f"stage `{stage}`: transcripts log {logged} output tokens, while the content comes to "
        f"about {estimated} (characters / 4); Claude Code often logs the output count from "
        f"the start of the stream, so `{COST_KEYS[stage]}` is a lower bound"
    )


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


# Claude Code keeps its transcripts under its configuration directory, which
# CLAUDE_CONFIG_DIR moves.
def default_transcripts() -> Path:
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(configured) if configured else Path.home() / ".claude"
    return base / "projects"


# An exact line edit inside the `metrics:` block: an existing key has its value replaced, a
# new one is appended after the block's last line, and every other byte stays as it was.
def write_costs(text: str, values: dict[str, int]) -> str | None:
    if not text.startswith("---\n"):
        return None
    close = text.find("\n---", 3)
    if close < 0:
        return None
    lines = text[4 : close + 1].splitlines(keepends=True)
    # The same test as `parse_metrics`, so `metrics: ` with a trailing space is still the block.
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if not line.startswith(" ") and line.strip() == "metrics:"
        ),
        None,
    )
    if start is None:
        lines.append("metrics:\n")
        start = len(lines) - 1
    end = start + 1
    while end < len(lines) and lines[end].startswith(" "):
        end += 1
    block = lines[start + 1 : end]
    indent = re.match(r" +", block[0]).group(0) if block else "  "
    for key, value in values.items():
        pattern = re.compile(rf"( +){re.escape(key)}:.*")
        for index, line in enumerate(block):
            match = pattern.fullmatch(line.rstrip("\n"))
            if match:
                block[index] = f"{match.group(1)}{key}: {value}\n"
                break
        else:
            block.append(f"{indent}{key}: {value}\n")
    lines[start + 1 : end] = block
    return "---\n" + "".join(lines) + text[close + 1 :]


def usage_table(stages: dict[str, dict[str, list[int]]], cents: dict[str, int | None]) -> str:
    header = ["stage", "models", *TOKEN_TYPES, "cents"]
    rows = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for stage in COST_KEYS:
        if stage not in stages:
            continue
        by_model = stages[stage]
        totals = [sum(tokens[index] for tokens in by_model.values()) for index in range(5)]
        cost = cents[stage]
        cells = [stage, ", ".join(sorted(by_model)), *map(str, totals)]
        cells.append("-" if cost is None else str(cost))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


# A missing cost must never stop the closing of a spec, so everything except an unreadable
# SPEC.md ends with a warning and exit code 0.
def record_cost(spec_dir: Path, source: Path) -> int:
    spec = spec_dir / "SPEC.md"
    try:
        text = spec.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"no readable SPEC.md in {spec_dir}: {exc}", file=sys.stderr)
        return 1
    estimates: dict[str, list[int]] = {}
    stages = stage_usage(spec_dir, source, estimates) if source.is_dir() else {}
    if not stages:
        print(
            f"no stage transcripts of {spec_dir.resolve().name} in {source}; "
            "SPEC.md left unchanged",
            file=sys.stderr,
        )
        return 0
    cents: dict[str, int | None] = {}
    values: dict[str, int] = {}
    for stage, key in COST_KEYS.items():
        if stage not in stages:
            print(f"stage `{stage}`: no transcripts found, `{key}` not written", file=sys.stderr)
            continue
        unknown = sorted(model for model in stages[stage] if rate_for(model) is None)
        cents[stage] = stage_cents(stages[stage])
        if unknown:
            print(
                f"stage `{stage}`: no rate for model {', '.join(unknown)} in the rate table "
                f"of {RATES_DATE}, `{key}` not written",
                file=sys.stderr,
            )
        elif cents[stage] is not None:
            values[key] = cents[stage]
        shortfall = output_shortfall(stage, *estimates.get(stage, [0, 0]))
        if shortfall:
            print(shortfall, file=sys.stderr)
    print(usage_table(stages, cents))
    if not values:
        return 0
    updated = write_costs(text, values)
    if updated is None:
        print(f"{spec} has no frontmatter; cost not written", file=sys.stderr)
    elif updated != text:
        spec.write_text(updated, encoding="utf-8")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Report or check workflow metrics.")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--record-cost", action="store_true")
    parser.add_argument("--transcripts")
    parser.add_argument("directory", nargs="?")
    args = parser.parse_args(argv[1:])
    if args.check and args.record_cost:
        parser.error("--check and --record-cost are separate runs; pass one of them")
    if args.transcripts and not args.record_cost:
        parser.error("--transcripts only works with --record-cost")

    if args.record_cost:
        if not args.directory:
            print(
                "usage: workflow_metrics.py --record-cost <spec-dir> [--transcripts <dir>]",
                file=sys.stderr,
            )
            return 1
        source = Path(args.transcripts) if args.transcripts else default_transcripts()
        return record_cost(Path(args.directory), source)

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
