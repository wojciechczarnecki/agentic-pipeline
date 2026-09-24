import re
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
STAGE_SKILLS = ["idea", "plan", "plan-review", "implement", "final-review", "ship"]


# Structural cover over the identifiers the stage skills must name — the metrics format, the
# checker, the configuration block, the visual sentence — never over their prose, which a
# rewording (or a translation) would break while a lost rule slipped past.
def skill_text(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


def section(name: str, heading: str) -> str:
    text = skill_text(name)
    assert f"## {heading}" in text, f"{name}: no section `{heading}`"
    return text.split(f"## {heading}", 1)[1].split("\n## ", 1)[0].strip()


def test_the_configuration_block_is_two_bullets_everywhere():
    blocks = {name: section(name, "Project configuration") for name in STAGE_SKILLS}
    for name, block in blocks.items():
        bullets = [line for line in block.splitlines() if line.startswith("- ")]
        assert len(bullets) == 2, f"{name}: the configuration block must be two bullets"
        assert not any(
            line.strip().startswith("|") for line in block.splitlines()
        ), f"{name}: the key table belongs in plugin/README.md only"
    assert (
        len(set(blocks.values())) == 1
    ), "the six configuration blocks have drifted apart: " + ", ".join(sorted(blocks))


@pytest.mark.parametrize("name", STAGE_SKILLS)
def test_the_configuration_block_keeps_the_fallback(name):
    block = section(name, "Project configuration")
    for token in [".claude/workflow.json", "README", "/pipeline:init"]:
        assert token in block, f"{name}: the configuration block must name {token}"


VISUAL_FILES = {
    "plan": PLUGIN / "skills" / "plan" / "SKILL.md",
    "plan-review": PLUGIN / "skills" / "plan-review" / "SKILL.md",
    "implement": PLUGIN / "skills" / "implement" / "SKILL.md",
    "final-review": PLUGIN / "skills" / "final-review" / "SKILL.md",
    "implementer": PLUGIN / "agents" / "implementer.md",
}
MASK = "\x00"


def sentences(text: str) -> list[str]:
    masked = re.sub(r"`[^`]*`", lambda m: m.group(0).replace(".", MASK), text)
    return [part.replace(MASK, ".") for part in re.split(r"(?<=[.!?])\s+", masked)]


@pytest.mark.parametrize("name", sorted(VISUAL_FILES))
def test_the_visual_sentence_is_one_imperative_sentence(name):
    text = VISUAL_FILES[name].read_text()
    assert "verify.scopes" in text and "<docs.conventions>" in text
    carrying = [
        sentence
        for sentence in sentences(text)
        if "verify.scopes" in sentence and "<docs.conventions>" in sentence
    ]
    assert len(carrying) == 1, (
        f"{name}: exactly one sentence must name both `verify.scopes` and "
        f"`<docs.conventions>`, found {len(carrying)}"
    )
    sentence = carrying[0]
    assert "consider" not in sentence.lower()
    assert "worth" not in sentence.lower()


@pytest.mark.parametrize("name", STAGE_SKILLS)
def test_no_stage_skill_enumerates_views(name):
    for forbidden in ["wide view", "narrow view", "wide and narrow"]:
        assert forbidden not in skill_text(name)


@pytest.mark.parametrize("name", ["planner", "plan-reviewer", "implementer", "reviewer"])
def test_no_agent_enumerates_views(name):
    text = (PLUGIN / "agents" / f"{name}.md").read_text()
    for forbidden in ["wide view", "narrow view", "wide and narrow"]:
        assert forbidden not in text


CLOSING_STEPS = {
    "plan": ("8. ", ["started_at", "escalations", "plan_steps"]),
    "plan-review": (
        "6. ",
        ["plan_review_blockers", "plan_review_majors", "plan_changes"],
    ),
    "implement": (
        "6. **Finish",
        ["implement_steps", "implement_iterations", "deviations"],
    ),
    "final-review": (
        "4. **Write the report",
        ["final_review_blockers", "final_review_worth_fixing", "final_review_nits"],
    ),
}
METRIC_SKILLS = sorted(CLOSING_STEPS)


def closing_step(name: str) -> str:
    text = skill_text(name)
    prefix, _ = CLOSING_STEPS[name]
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(prefix))
    end = next(
        (
            i
            for i in range(start + 1, len(lines))
            if lines[i].startswith("#") or re.match(r"\d+\. ", lines[i])
        ),
        len(lines),
    )
    return "\n".join(lines[start:end])


def apply_closing_step() -> str:
    text = skill_text("final-review").split("## Apply mode", 1)[1]
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("5. "))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("6. ")), len(lines))
    return "\n".join(lines[start:end])


@pytest.mark.parametrize("name", METRIC_SKILLS)
def test_closing_step_states_the_metrics_format(name):
    step = closing_step(name)
    assert "metrics:" in step
    assert "%Y-%m-%dT%H:%M" in step
    for key in CLOSING_STEPS[name][1]:
        assert key in step, f"{name}: the closing step must name `{key}`"


@pytest.mark.parametrize("name", METRIC_SKILLS)
def test_closing_step_runs_the_checker(name):
    step = closing_step(name)
    # The checker is called through PATH (Claude Code appends the plugin's `bin/` to it).
    # Skill text gets ${CLAUDE_PLUGIN_ROOT} substituted, but permission rules do not, so an
    # absolute-path call never matches the allow rule and a stage subagent, which cannot
    # answer the prompt, stalls. Measured 2026-09-21 on 0.3.0.
    assert "`workflow_metrics.py --check <spec-dir>`" in step, name
    assert "CLAUDE_PLUGIN_ROOT" not in step, name


@pytest.mark.parametrize("name", METRIC_SKILLS)
def test_closing_step_names_the_escalation_path(name):
    assert "RESULT: ESCALATE" in closing_step(name)


def test_apply_mode_gates_done_on_the_checker():
    step = apply_closing_step()
    assert "--check" in step
    assert "done" in step
    assert "RESULT: ESCALATE" in step


@pytest.mark.parametrize("name", STAGE_SKILLS)
def test_no_stage_skill_sends_metrics_rules_to_the_readme(name):
    for line in skill_text(name).splitlines():
        lowered = line.lower()
        sends_to_readme = "readme" in lowered and "metric" in lowered
        assert not sends_to_readme, f"{name}: {line}"
    if name == "ship":
        assert "Workflow metrics" not in skill_text(name)


# A workflow name belongs to the project that runs it; the PR checks carry the run links.
def test_final_review_takes_the_run_link_from_the_pr_checks():
    text = (PLUGIN / "skills" / "final-review" / "SKILL.md").read_text()
    assert "--workflow" not in text
    assert "gh pr checks <nr> --json name,workflow,link" in text
