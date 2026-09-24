import importlib.util
import json
import os
import subprocess
import sys
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
        '---\nstatus: spec-ready\nstage_history:\n  - "done — 2026-09-24"\nmetrics:\n'
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


SONNET = "claude-sonnet-5"
HAIKU_DATED = "claude-haiku-4-5-20251001"


# Hand-computed, cents per million tokens from the rate table:
#   plan (Opus 5.5): 1000 × 400 + 2000 × 500 + 50 000 × 20 + 3000 × 2000
#     = 400 000 + 1 000 000 + 1 000 000 + 6 000 000 = 8 400 000 → 8.4 → 8
#   plan review (Sonnet 5): 2500 × 1000 = 2 500 000 → 2.5 → 3
#   implement: Opus 5.5 10 000 × 800 (1 h write) = 8 000 000, Haiku 4.5 20 000 × 100
#     = 2 000 000 → 10 000 000 → 10
#   final review: reviewer on Opus 5, 1000 × 2500 = 2 500 000; its perspective on Opus 5.5,
#     100 000 × 20 = 2 000 000 → 4 500 000 → 4.5 → 5
EXPECTED = {
    "cost_plan_cents": 8,
    "cost_plan_review_cents": 3,
    "cost_implement_cents": 10,
    "cost_final_review_cents": 5,
}


def write_all_stages(source: Path, cwd: Path, slug: str = "slug", scale: int = 1) -> None:
    write_agent(
        source,
        slug,
        "s1",
        "pl",
        "pipeline:planner",
        prompt(),
        cwd,
        [("a1", OPUS, usage(input_tokens=1000, write_5m=2000, read=50_000, output=3000 * scale))],
    )
    write_agent(
        source,
        slug,
        "s1",
        "pr",
        "pipeline:plan-reviewer",
        prompt(),
        cwd,
        [("a2", SONNET, usage(output=2500 * scale))],
    )
    write_agent(
        source,
        slug,
        "s1",
        "im",
        "pipeline:implementer",
        prompt(),
        cwd,
        [("a3", OPUS, usage(write_1h=10_000)), ("a4", HAIKU_DATED, usage(input_tokens=20_000))],
    )
    write_agent(
        source,
        slug,
        "s1",
        "rv",
        "pipeline:reviewer",
        prompt(),
        cwd,
        [("a5", "claude-opus-5", usage(output=1000))],
    )
    write_agent(
        source,
        slug,
        "s1",
        "pp",
        "general-purpose",
        "Review the diff.",
        cwd,
        [("a6", OPUS, usage(read=100_000))],
        parent="rv",
    )


def run_record(spec: Path, *args: str, home: Path, env: dict | None = None):
    environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_CONFIG_DIR"}
    environment["HOME"] = str(home)
    environment.update(env or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--record-cost", str(spec), *args],
        capture_output=True,
        text=True,
        env=environment,
    )


def recorded(spec: Path) -> dict[str, str]:
    return workflow_metrics.parse_metrics((spec / "SPEC.md").read_text())


def cost_values(spec: Path) -> dict[str, int]:
    return {key: int(value) for key, value in recorded(spec).items() if key.startswith("cost_")}


def test_record_cost_writes_the_four_keys(repo, tmp_path):
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    spec = repo / "specs" / SPEC_NAME
    result = run_record(spec, "--transcripts", str(source), home=tmp_path / "home")
    assert result.returncode == 0, result.stderr
    assert cost_values(spec) == EXPECTED


def test_transcripts_option_reads_that_directory(repo, tmp_path):
    archive = tmp_path / "archive" / "2026-09-24"
    write_all_stages(archive, repo)
    spec = repo / "specs" / SPEC_NAME
    without = run_record(spec, home=tmp_path / "home")
    assert without.returncode == 0
    assert cost_values(spec) == {}
    result = run_record(spec, "--transcripts", str(tmp_path / "archive"), home=tmp_path / "home")
    assert result.returncode == 0, result.stderr
    assert cost_values(spec) == EXPECTED


def test_default_source_finds_worktree_lanes(repo, tmp_path):
    home = tmp_path / "home"
    projects = home / ".claude" / "projects"
    lane = tmp_path / "wt" / "011-x"
    lane.mkdir(parents=True)
    write_agent(
        projects,
        "-repo",
        "s1",
        "pl",
        "pipeline:planner",
        prompt(),
        repo,
        [("a1", OPUS, usage(output=3000))],
    )
    write_agent(
        projects,
        "-wt-011-x",
        "s2",
        "im",
        "pipeline:implementer",
        prompt(),
        lane,
        [("a3", OPUS, usage(write_1h=10_000))],
    )
    spec = repo / "specs" / SPEC_NAME
    result = run_record(spec, home=home)
    assert result.returncode == 0, result.stderr
    # 3000 × 2000 = 6 000 000 → 6; 10 000 × 800 = 8 000 000 → 8
    assert cost_values(spec) == {"cost_plan_cents": 6, "cost_implement_cents": 8}


def test_the_claude_config_dir_moves_the_default_source(repo, tmp_path):
    config = tmp_path / "config"
    write_all_stages(config / "projects", repo)
    spec = repo / "specs" / SPEC_NAME
    result = run_record(spec, home=tmp_path / "home", env={"CLAUDE_CONFIG_DIR": str(config)})
    assert result.returncode == 0, result.stderr
    assert cost_values(spec) == EXPECTED


def test_a_second_run_replaces_the_keys_and_keeps_every_other_byte(repo, tmp_path):
    spec = repo / "specs" / SPEC_NAME
    original = (spec / "SPEC.md").read_text()
    first = tmp_path / "first"
    write_all_stages(first, repo)
    assert run_record(spec, "--transcripts", str(first), home=tmp_path / "h").returncode == 0
    second = tmp_path / "second"
    write_all_stages(second, repo, scale=2)
    assert run_record(spec, "--transcripts", str(second), home=tmp_path / "h").returncode == 0
    # scale 2: plan 8 400 000 + 6 000 000 = 14 400 000 → 14; plan review 5 000 000 → 5
    expected = original.replace(
        "  escalations: 0\n",
        "  escalations: 0\n"
        "  cost_plan_cents: 14\n"
        "  cost_plan_review_cents: 5\n"
        "  cost_implement_cents: 10\n"
        "  cost_final_review_cents: 5\n",
    )
    assert (spec / "SPEC.md").read_text() == expected


def test_an_existing_value_is_replaced_in_place(repo, tmp_path):
    spec = repo / "specs" / SPEC_NAME
    text = (
        (spec / "SPEC.md")
        .read_text()
        .replace("  started_at:", "  cost_plan_review_cents: 999\n  started_at:")
    )
    (spec / "SPEC.md").write_text(text)
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    assert run_record(spec, "--transcripts", str(source), home=tmp_path / "h").returncode == 0
    after = (spec / "SPEC.md").read_text()
    assert after.index("  cost_plan_review_cents: 3\n") < after.index("  started_at:")
    assert after.count("cost_plan_review_cents") == 1


def test_a_spec_without_a_metrics_block_gets_one(repo, tmp_path):
    spec = repo / "specs" / SPEC_NAME
    (spec / "SPEC.md").write_text("---\nstatus: spec-ready\n---\n\n# SPEC 011 — x\n")
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    assert run_record(spec, "--transcripts", str(source), home=tmp_path / "h").returncode == 0
    assert (
        (spec / "SPEC.md")
        .read_text()
        .startswith("---\nstatus: spec-ready\nmetrics:\n  cost_plan_cents: 8\n")
    )
    assert cost_values(spec) == EXPECTED


def test_an_unknown_model_skips_its_stage_and_is_named(repo, tmp_path):
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    write_agent(
        source,
        "slug",
        "s1",
        "im2",
        "pipeline:implementer",
        prompt(),
        repo,
        [("a9", "claude-nope-9", usage(output=10))],
    )
    spec = repo / "specs" / SPEC_NAME
    result = run_record(spec, "--transcripts", str(source), home=tmp_path / "h")
    assert result.returncode == 0
    assert "claude-nope-9" in result.stderr
    assert cost_values(spec) == {
        key: value for key, value in EXPECTED.items() if key != "cost_implement_cents"
    }


def test_a_stage_without_transcripts_warns(repo, tmp_path):
    source = tmp_path / "projects"
    write_agent(
        source,
        "slug",
        "s1",
        "pl",
        "pipeline:planner",
        prompt(),
        repo,
        [("a1", OPUS, usage(output=3000))],
    )
    spec = repo / "specs" / SPEC_NAME
    result = run_record(spec, "--transcripts", str(source), home=tmp_path / "h")
    assert result.returncode == 0
    assert cost_values(spec) == {"cost_plan_cents": 6}
    for stage in ["plan-review", "implement", "final-review"]:
        assert stage in result.stderr, stage


@pytest.mark.parametrize("kind", ["empty", "missing"])
def test_no_transcripts_leaves_the_file_unchanged(repo, tmp_path, kind):
    source = tmp_path / "projects"
    if kind == "empty":
        source.mkdir()
    spec = repo / "specs" / SPEC_NAME
    before = (spec / "SPEC.md").read_bytes()
    result = run_record(spec, "--transcripts", str(source), home=tmp_path / "h")
    assert result.returncode == 0
    assert result.stderr.strip()
    assert (spec / "SPEC.md").read_bytes() == before


def test_a_directory_without_a_spec_fails(tmp_path):
    result = run_record(tmp_path, "--transcripts", str(tmp_path), home=tmp_path)
    assert result.returncode == 1
    assert "SPEC.md" in result.stderr
    assert "Traceback" not in result.stderr


def test_stdout_shows_tokens_by_type_model_and_cost(repo, tmp_path):
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    write_agent(
        source,
        "slug",
        "s1",
        "im2",
        "pipeline:implementer",
        prompt(),
        repo,
        [("a9", "claude-nope-9", usage(output=10))],
    )
    spec = repo / "specs" / SPEC_NAME
    result = run_record(spec, "--transcripts", str(source), home=tmp_path / "h")
    lines = [line for line in result.stdout.splitlines() if line.startswith("|")]
    assert len(lines) >= 3, result.stdout
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    assert header == [
        "stage",
        "models",
        "input",
        "cache_write_5m",
        "cache_write_1h",
        "cache_read",
        "output",
        "cents",
    ]
    rows = {
        cells[0]: cells
        for cells in ([cell.strip() for cell in line.strip("|").split("|")] for line in lines[2:])
    }
    assert set(rows) == {"plan", "plan-review", "implement", "final-review"}
    assert rows["plan"] == ["plan", OPUS, "1000", "2000", "0", "50000", "3000", "8"]
    assert rows["plan-review"][1] == SONNET
    assert HAIKU_DATED in rows["implement"][1] and "claude-nope-9" in rows["implement"][1]
    assert rows["implement"][-1] == "-"
    assert rows["final-review"][-1] == "5"


def test_record_cost_output_passes_the_check(repo, tmp_path):
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    spec = repo / "specs" / SPEC_NAME
    assert run_record(spec, "--transcripts", str(source), home=tmp_path / "h").returncode == 0
    assert workflow_metrics.check(spec) == []


# A transcript cut off inside a multi-byte character (a lane still writing, a crashed
# session) must not stop the run: every other stage keeps its cost.
def test_a_transcript_cut_inside_a_character_is_still_read(repo, tmp_path):
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    transcript = source / "slug" / "s1" / "subagents" / "agent-im.jsonl"
    with transcript.open("ab") as handle:
        handle.write(b'{"type": "assistant", "message": {"id": "cut", "text": "\xe2\x80')
    spec = repo / "specs" / SPEC_NAME
    result = run_record(spec, "--transcripts", str(source), home=tmp_path / "h")
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert cost_values(spec) == EXPECTED


def test_a_spec_with_non_ascii_text_keeps_it(repo, tmp_path):
    spec = repo / "specs" / SPEC_NAME
    text = (spec / "SPEC.md").read_text(encoding="utf-8") + "Naïve café — déjà vu.\n"
    (spec / "SPEC.md").write_bytes(text.encode("utf-8"))
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    result = run_record(
        spec, "--transcripts", str(source), home=tmp_path / "h", env={"LC_ALL": "C"}
    )
    assert result.returncode == 0, result.stderr
    assert (spec / "SPEC.md").read_bytes().decode("utf-8").endswith("Naïve café — déjà vu.\n")
    assert cost_values(spec) == EXPECTED


# `metrics: ` with a trailing space is the same block for `parse_metrics`, so it must not get
# a second `metrics:` key.
def test_a_metrics_line_with_a_trailing_space_is_the_block(repo, tmp_path):
    spec = repo / "specs" / SPEC_NAME
    text = (spec / "SPEC.md").read_text().replace("metrics:\n", "metrics: \n")
    (spec / "SPEC.md").write_text(text)
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    assert run_record(spec, "--transcripts", str(source), home=tmp_path / "h").returncode == 0
    after = (spec / "SPEC.md").read_text()
    assert after.count("metrics:") == 1
    assert cost_values(spec) == EXPECTED


def test_a_block_followed_by_another_key_keeps_it_outside(repo, tmp_path):
    spec = repo / "specs" / SPEC_NAME
    text = (spec / "SPEC.md").read_text().replace("\n---\n", "\nowner: someone\n---\n", 1)
    (spec / "SPEC.md").write_text(text)
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    assert run_record(spec, "--transcripts", str(source), home=tmp_path / "h").returncode == 0
    after = (spec / "SPEC.md").read_text()
    assert "  cost_final_review_cents: 5\nowner: someone\n---\n" in after
    assert cost_values(spec) == EXPECTED


# Claude Code may log a message's `output_tokens` from the start of the stream; the output
# count is then a lower bound, and the run says so without changing the cost.
def append_content(source: Path, agent_id: str, message_id: str, text: str) -> None:
    transcript = source / "slug" / "s1" / "subagents" / f"agent-{agent_id}.jsonl"
    line = {
        "type": "assistant",
        "message": {
            "id": message_id,
            "model": OPUS,
            "usage": usage(output=8),
            "content": [{"type": "text", "text": text}],
        },
    }
    with transcript.open("a") as handle:
        handle.write(json.dumps(line) + "\n")


def test_an_output_count_far_below_the_content_warns(repo, tmp_path):
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    append_content(source, "rv", "big", "x" * 20_000)
    spec = repo / "specs" / SPEC_NAME
    result = run_record(spec, "--transcripts", str(source), home=tmp_path / "h")
    assert result.returncode == 0, result.stderr
    warned = [line for line in result.stderr.splitlines() if "lower bound" in line]
    assert len(warned) == 1, result.stderr
    assert "final-review" in warned[0] and "cost_final_review_cents" in warned[0]
    # The 8 logged tokens are priced; the estimate never is: 2 500 000 + 2 000 000 + 8 × 2000
    # = 4 516 000 → 4.5 → 5.
    assert cost_values(spec) == EXPECTED


def test_small_content_does_not_warn(repo, tmp_path):
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    append_content(source, "rv", "small", "x" * 400)
    result = run_record(
        repo / "specs" / SPEC_NAME, "--transcripts", str(source), home=tmp_path / "h"
    )
    assert "lower bound" not in result.stderr


def test_content_estimates_are_per_stage(repo, tmp_path):
    source = tmp_path / "projects"
    write_all_stages(source, repo)
    append_content(source, "rv", "big", "x" * 20_000)
    append_content(source, "rv", "big", "x" * 20_000)
    estimates: dict[str, list[int]] = {}
    workflow_metrics.stage_usage(repo / "specs" / SPEC_NAME, source, estimates)
    logged, estimated = estimates["final-review"]
    assert logged == 1000 + 0 + 8
    # One block, logged twice, counts once.
    assert 5000 <= estimated < 5100
    assert estimates["plan"] == [3000, 0]


# The prompt is the first `user` entry, whatever Claude Code writes ahead of it.
def test_an_entry_ahead_of_the_prompt_does_not_hide_the_agent(repo, tmp_path):
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
    transcript = source / "slug" / "s1" / "subagents" / "agent-a.jsonl"
    header = json.dumps({"type": "summary", "cwd": str(repo), "message": {"content": "x"}})
    transcript.write_text(header + "\n" + transcript.read_text())
    stages = workflow_metrics.stage_usage(repo / "specs" / SPEC_NAME, source)
    assert stages == {"plan": {OPUS: [0, 0, 0, 0, 5]}}


def test_a_grandchild_counts_and_a_parent_cycle_ends(repo, tmp_path):
    source = tmp_path / "projects"
    write_agent(
        source, "slug", "s1", "rv", "pipeline:reviewer", prompt(), repo, [("m1", OPUS, usage())]
    )
    write_agent(
        source,
        "slug",
        "s1",
        "p",
        "general-purpose",
        "x",
        repo,
        [("m2", OPUS, usage(output=3))],
        parent="rv",
    )
    write_agent(
        source,
        "slug",
        "s1",
        "g",
        "Explore",
        "x",
        repo,
        [("m3", OPUS, usage(output=4))],
        parent="p",
    )
    write_agent(
        source,
        "slug",
        "s1",
        "c1",
        "general-purpose",
        "x",
        repo,
        [("m4", OPUS, usage(output=100))],
        parent="c2",
    )
    write_agent(
        source,
        "slug",
        "s1",
        "c2",
        "general-purpose",
        "x",
        repo,
        [("m5", OPUS, usage(output=100))],
        parent="c1",
    )
    stages = workflow_metrics.stage_usage(repo / "specs" / SPEC_NAME, source)
    assert stages == {"final-review": {OPUS: [0, 0, 0, 0, 7]}}


@pytest.mark.parametrize(
    "args",
    [
        ["--check", "--record-cost", "SPEC_DIR"],
        ["--transcripts", "SOURCE", "SPEC_DIR"],
        ["--check", "--transcripts", "SOURCE", "SPEC_DIR"],
    ],
    ids=["check-and-record", "transcripts-with-report", "transcripts-with-check"],
)
def test_options_that_do_not_go_together_are_refused(repo, tmp_path, args):
    spec = repo / "specs" / SPEC_NAME
    before = (spec / "SPEC.md").read_bytes()
    argv = [{"SPEC_DIR": str(spec), "SOURCE": str(tmp_path)}.get(arg, arg) for arg in args]
    result = subprocess.run([sys.executable, str(SCRIPT), *argv], capture_output=True, text=True)
    assert result.returncode == 2
    assert "usage" in result.stderr
    assert (spec / "SPEC.md").read_bytes() == before


# A real lane: `ship` runs `--record-cost` on the lane's spec, while agents ran in the main
# checkout and in the lane. Only `--git-common-dir` leads from the lane back to the main
# checkout and to `worktree.dir` resolved from there.
def test_a_spec_costed_from_inside_a_real_lane(repo, tmp_path):
    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
            check=True,
            capture_output=True,
        )

    git("add", "-A")
    git("commit", "-q", "-m", "init")
    lane = tmp_path / "wt" / "011-x"
    git("worktree", "add", "-q", "-b", "lane", str(lane))
    source = tmp_path / "projects"
    write_agent(
        source,
        "-repo",
        "s1",
        "pl",
        "pipeline:planner",
        prompt(),
        repo,
        [("m1", OPUS, usage(output=3))],
    )
    write_agent(
        source,
        "-wt-011-x",
        "s2",
        "im",
        "pipeline:implementer",
        prompt(),
        lane,
        [("m2", OPUS, usage(output=4))],
    )
    stages = workflow_metrics.stage_usage(lane / "specs" / SPEC_NAME, source)
    assert stages == {"plan": {OPUS: [0, 0, 0, 0, 3]}, "implement": {OPUS: [0, 0, 0, 0, 4]}}
