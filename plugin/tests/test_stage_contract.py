from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
SHIP = (PLUGIN / "skills" / "ship" / "SKILL.md").read_text()
AGENTS = ["planner", "plan-reviewer", "implementer", "reviewer"]
STAGE_SKILLS = ["plan", "plan-review", "implement", "final-review"]
CONTRACT_HEADINGS = ["## Stage agent contract", "## Escalation triggers"]


# The contract is pinned through the literal text the agent files must carry, so that an
# edit on one side alone fails CI: plugin/skills/ship/SKILL.md and the four agent files are
# one unit. Editing the contract means editing all five.
def section(text: str, heading_prefix: str) -> str:
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(heading_prefix))
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start:end]).rstrip()


def agent_section(name: str, heading_prefix: str) -> str:
    return section(agent_text(name), heading_prefix)


def agent_text(name: str) -> str:
    return (PLUGIN / "agents" / f"{name}.md").read_text()


def skill_text(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


@pytest.mark.parametrize("agent", AGENTS)
@pytest.mark.parametrize("heading", CONTRACT_HEADINGS)
def test_every_agent_carries_the_contract(agent, heading):
    text = agent_text(agent)
    assert heading in text, f"{agent}.md is missing `{heading}`"
    assert agent_section(agent, heading) == section(SHIP, heading), (
        f"{agent}.md's `{heading}` is not character-identical to skills/ship/SKILL.md — "
        "the contract lives in five files and every change has to be repeated in all of "
        "them; neither an added nor a removed line is allowed in one copy alone"
    )


@pytest.mark.parametrize("agent", AGENTS)
def test_no_agent_sends_the_reader_to_the_ship_skill(agent):
    text = agent_text(agent)
    assert "skills/ship" not in text
    assert "skill `ship`" not in text
    assert "`ship` skill" not in text


def test_the_contract_states_the_metrics_format():
    block = section(SHIP, "## Stage agent contract")
    assert "metrics:" in block
    assert "%Y-%m-%dT%H:%M" in block
    assert "escalations" in block
    assert "README" not in block


# A stage agent that bumps `escalations` itself double-counts the orchestrator's escalation.
def test_the_contract_leaves_escalations_to_the_orchestrator():
    block = section(SHIP, "## Stage agent contract")
    assert "`escalations` is incremented only by the orchestrator" in block


# The harness may run agents in the background; what matters is waiting for the result.
def test_ship_waits_for_the_stage_result_without_naming_a_mode():
    assert "in the foreground" not in SHIP
    assert "You wait for the stage agent's result before you go on." in SHIP


@pytest.mark.parametrize("skill", STAGE_SKILLS)
def test_no_stage_skill_orders_a_read_of_the_ship_skill(skill):
    assert "this plugin's `ship` skill" not in skill_text(skill)


def test_ship_step_three_states_the_metrics_format():
    lines = SHIP.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("3. "))
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("#")), len(lines))
    step = "\n".join(lines[start:end])
    for token in ["started_at", "escalations", "metrics:", "%Y-%m-%dT%H:%M"]:
        assert token in step
    assert "README" not in step
