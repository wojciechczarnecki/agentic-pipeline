from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
STAGE_SKILLS = ["idea", "plan", "plan-review", "implement", "final-review", "ship"]
AGENTS = ["planner", "plan-reviewer", "implementer", "reviewer"]


def skill_text(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


def agent_text(name: str) -> str:
    return (PLUGIN / "agents" / f"{name}.md").read_text()


def section(text: str, heading: str) -> str:
    assert f"\n{heading}\n" in text, heading
    return text.split(f"\n{heading}\n", 1)[1].split("\n## ", 1)[0].strip()


def bullets(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        if line.startswith("- "):
            items.append(line)
        elif items and line.startswith("  "):
            items[-1] += " " + line.strip()
    return items


# The language contract (plugin/README.md, SPEC 006 AC1–AC2) reaches every stage as one
# block, so a stage cannot drift from the others: files in `language`, commits and PR titles
# in English, the conversation in the session language.
def test_the_language_block_is_identical_everywhere():
    blocks = {name: section(skill_text(name), "## Język") for name in STAGE_SKILLS}
    assert len(set(blocks.values())) == 1, sorted(blocks)
    items = bullets(next(iter(blocks.values())))
    assert len(items) == 3
    assert "`language`" in items[0]
    for token in ["commit", "PR", "angielsku"]:
        assert token in items[1], token
    assert "sesji" in items[2]


@pytest.mark.parametrize("agent", AGENTS)
def test_every_agent_states_its_language_part(agent):
    contract = section(agent_text(agent), "## Kontrakt agenta etapu")
    assert "`language`" in contract
    assert "angielsku" in contract
