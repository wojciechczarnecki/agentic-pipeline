import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "workflow_metrics.py"
_spec = importlib.util.spec_from_file_location("workflow_metrics", SCRIPT)
workflow_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(workflow_metrics)


# SPEC 011, AC8: a cent is a fixed unit only while the table is never repriced, so the rows
# are pinned literally. Cents per million tokens: input, cache write 5 min, cache write 1 h,
# cache read, output.
def test_the_rate_table_is_dated_and_frozen():
    assert workflow_metrics.RATES_DATE == "2026-09-24"
    assert workflow_metrics.RATES == {
        "claude-opus-5-5": (400, 500, 800, 20, 2000),
        "claude-opus-5": (500, 625, 1000, 50, 2500),
        "claude-sonnet-5": (200, 250, 400, 20, 1000),
        "claude-haiku-4-5": (100, 125, 200, 10, 500),
        "claude-fable-5-1": (1000, 1250, 2000, 25, 5000),
    }
    source = SCRIPT.read_text()
    assert "never changed" in source
    assert "launch rates" in source


# SPEC 011, AC1: only the stage total is rounded.
def test_stage_cost_is_tokens_times_rates_rounded_once():
    # 200 output tokens on Opus 5.5 = 200 × 2000 = 400 000 → 0.4 cent; 400 output tokens on
    # Sonnet 5 = 400 × 1000 = 400 000 → 0.4 cent. Together 0.8 → 1, where rounding each
    # would give 0.
    assert (
        workflow_metrics.stage_cents(
            {"claude-opus-5-5": [0, 0, 0, 0, 200], "claude-sonnet-5": [0, 0, 0, 0, 400]}
        )
        == 1
    )
    # Sonnet 5, every type: 1000 × 200 + 2000 × 250 + 3000 × 400 + 100 000 × 20 + 5000 × 1000
    # = 200 000 + 500 000 + 1 200 000 + 2 000 000 + 5 000 000 = 8 900 000 → 8.9 → 9.
    assert workflow_metrics.stage_cents({"claude-sonnet-5": [1000, 2000, 3000, 100_000, 5000]}) == 9
    # Half up: 5000 × 100 = 500 000 → 0.5 → 1.
    assert workflow_metrics.stage_cents({"claude-haiku-4-5": [5000, 0, 0, 0, 0]}) == 1


def test_a_dated_model_id_finds_its_rate():
    assert workflow_metrics.rate_for("claude-haiku-4-5-20251001") == (100, 125, 200, 10, 500)
    assert workflow_metrics.rate_for("claude-opus-5-5") == (400, 500, 800, 20, 2000)
    assert workflow_metrics.rate_for("claude-nope-1") is None
    assert workflow_metrics.stage_cents({"claude-nope-1": [1, 0, 0, 0, 0]}) is None


def test_usage_without_the_ttl_split_counts_as_5m():
    older = {
        "input_tokens": 1,
        "cache_creation_input_tokens": 7,
        "cache_read_input_tokens": 3,
        "output_tokens": 4,
    }
    assert workflow_metrics.usage_tokens(older) == (1, 7, 0, 3, 4)
    split = dict(
        older, cache_creation={"ephemeral_5m_input_tokens": 2, "ephemeral_1h_input_tokens": 5}
    )
    assert workflow_metrics.usage_tokens(split) == (1, 2, 5, 3, 4)


# The transcript layout of Claude Code 2.1.281: <source>/<project slug>/<session>/subagents/
# agent-<id>.meta.json beside agent-<id>.jsonl, whose first line is the prompt with `cwd`.
def write_agent(
    source: Path,
    slug: str,
    session: str,
    agent_id: str,
    agent_type: str,
    prompt: str,
    cwd: Path,
    messages: list[tuple[str, str, dict]],
    parent: str | None = None,
) -> None:
    directory = source / slug / session / "subagents"
    directory.mkdir(parents=True, exist_ok=True)
    meta = {"agentType": agent_type, "description": "x"}
    if parent:
        meta["parentAgentId"] = parent
    (directory / f"agent-{agent_id}.meta.json").write_text(json.dumps(meta))
    lines = [
        {
            "type": "user",
            "agentId": agent_id,
            "cwd": str(cwd),
            "message": {"role": "user", "content": [{"type": "text", "text": prompt}]},
        }
    ]
    for message_id, model, usage in messages:
        lines.append(
            {
                "type": "assistant",
                "agentId": agent_id,
                "cwd": str(cwd),
                "message": {"id": message_id, "model": model, "usage": usage},
            }
        )
    (directory / f"agent-{agent_id}.jsonl").write_text(
        "".join(json.dumps(line) + "\n" for line in lines)
    )


SPEC_NAME = "011-cost-x"
OPUS = "claude-opus-5-5"


def usage(input_tokens=0, write_5m=0, write_1h=0, read=0, output=0) -> dict:
    return {
        "input_tokens": input_tokens,
        "cache_creation_input_tokens": write_5m + write_1h,
        "cache_read_input_tokens": read,
        "cache_creation": {
            "ephemeral_5m_input_tokens": write_5m,
            "ephemeral_1h_input_tokens": write_1h,
        },
        "output_tokens": output,
    }


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


@pytest.fixture
def repo(tmp_path) -> Path:
    root = git_repo(tmp_path / "repo")
    (root / ".claude").mkdir()
    (root / ".claude" / "workflow.json").write_text('{"worktree": {"dir": "../wt"}}')
    spec = root / "specs" / SPEC_NAME
    spec.mkdir(parents=True)
    (spec / "SPEC.md").write_text(
        '---\nstatus: done\nstage_history:\n  - "done — 2026-09-24"\nmetrics:\n'
        "  started_at: 2026-09-24T10:00\n  escalations: 0\n---\n\n# SPEC 011 — x\n\nBody.\n"
    )
    return root


def prompt(name: str = SPEC_NAME) -> str:
    return f"Spec 011: specs/{name}/SPEC.md and PLAN.md (status plan-approved)."


def test_perspectives_and_both_reviewer_runs_count_toward_the_final_review(repo, tmp_path):
    source = tmp_path / "projects"
    for agent_id, output in [("r1", 10), ("r2", 20)]:
        write_agent(
            source,
            "slug",
            "s1",
            agent_id,
            "pipeline:reviewer",
            prompt(),
            repo,
            [(f"m-{agent_id}", OPUS, usage(output=output))],
        )
    for index in range(3):
        write_agent(
            source,
            "slug",
            "s1",
            f"p{index}",
            "general-purpose",
            "Review this diff.",
            repo,
            [(f"m-p{index}", OPUS, usage(input_tokens=100))],
            parent="r1",
        )
    stages = workflow_metrics.stage_usage(repo / "specs" / SPEC_NAME, source)
    assert stages == {"final-review": {OPUS: [300, 0, 0, 0, 30]}}


def test_a_rerun_after_an_escalation_counts_toward_its_stage(repo, tmp_path):
    source = tmp_path / "projects"
    write_agent(
        source,
        "slug",
        "s1",
        "a",
        "pipeline:planner",
        prompt(),
        repo,
        [("m1", OPUS, usage(output=5))],
    )
    write_agent(
        source, "slug", "s2", "b", "planner", prompt(), repo, [("m2", OPUS, usage(output=7))]
    )
    stages = workflow_metrics.stage_usage(repo / "specs" / SPEC_NAME, source)
    assert stages == {"plan": {OPUS: [0, 0, 0, 0, 12]}}


def test_other_specs_and_other_repositories_are_not_counted(repo, tmp_path):
    source = tmp_path / "projects"
    write_agent(
        source,
        "slug",
        "s1",
        "a",
        "pipeline:implementer",
        prompt(),
        repo,
        [("m1", OPUS, usage(output=5))],
    )
    spec = repo / "specs" / SPEC_NAME
    before = workflow_metrics.stage_usage(spec, source)
    other_repo = git_repo(tmp_path / "other")
    write_agent(
        source,
        "slug",
        "s1",
        "b",
        "pipeline:implementer",
        prompt("012-other"),
        repo,
        [("m2", OPUS, usage(output=50))],
    )
    write_agent(
        source,
        "other-slug",
        "s3",
        "c",
        "pipeline:implementer",
        prompt(),
        other_repo,
        [("m3", OPUS, usage(output=500))],
    )
    write_agent(
        source,
        "slug",
        "s1",
        "d",
        "pipeline:implementer",
        prompt(SPEC_NAME + "-v2"),
        repo,
        [("m4", OPUS, usage(output=5000))],
    )
    assert workflow_metrics.stage_usage(spec, source) == before
    assert before == {"implement": {OPUS: [0, 0, 0, 0, 5]}}


def test_repeated_lines_and_archive_copies_count_once(repo, tmp_path):
    source = tmp_path / "archive"
    for day in ["2026-09-23", "2026-09-24"]:
        write_agent(
            source / day,
            "slug",
            "s1",
            "a",
            "pipeline:plan-reviewer",
            prompt(),
            repo,
            [
                ("m1", OPUS, usage(input_tokens=3, output=1)),
                ("m1", OPUS, usage(input_tokens=3, output=4)),
                ("m1", OPUS, usage(input_tokens=3, output=9)),
            ],
        )
    stages = workflow_metrics.stage_usage(repo / "specs" / SPEC_NAME, source)
    assert stages == {"plan-review": {OPUS: [3, 0, 0, 0, 9]}}


def test_synthetic_lines_are_skipped(repo, tmp_path):
    source = tmp_path / "projects"
    write_agent(
        source,
        "slug",
        "s1",
        "a",
        "pipeline:planner",
        prompt(),
        repo,
        [("m1", "<synthetic>", usage(output=100)), ("m2", OPUS, usage(output=2))],
    )
    directory = source / "slug" / "s1" / "subagents"
    with (directory / "agent-a.jsonl").open("a") as handle:
        handle.write("not json\n")
        handle.write(json.dumps({"type": "assistant", "message": {"id": "m3", "model": OPUS}}))
        handle.write("\n")
    stages = workflow_metrics.stage_usage(repo / "specs" / SPEC_NAME, source)
    assert stages == {"plan": {OPUS: [0, 0, 0, 0, 2]}}


def test_worktree_lane_cwd_is_accepted(repo, tmp_path):
    source = tmp_path / "projects"
    lane = tmp_path / "wt" / "011-x"
    lane.mkdir(parents=True)
    write_agent(
        source,
        "-wt-011-x",
        "s1",
        "a",
        "pipeline:implementer",
        prompt(),
        lane,
        [("m1", OPUS, usage(write_1h=10))],
    )
    stages = workflow_metrics.stage_usage(repo / "specs" / SPEC_NAME, source)
    assert stages == {"implement": {OPUS: [0, 0, 10, 0, 0]}}
