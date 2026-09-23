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


TEMPLATE_BLOCKS = {"idea": ("SPEC", "```"), "plan": ("PLAN", "````")}
BLOCK_HEADINGS = {"pl": "### Polski (`pl`)", "en": "### Angielski (`en`)"}


def inline_template(text: str, heading: str, fence: str) -> str:
    assert f"\n{heading}\n" in text, heading
    after = text.split(f"\n{heading}\n", 1)[1].lstrip("\n")
    opening = f"{fence}markdown\n"
    assert after.startswith(opening), heading
    return after[len(opening) :].split(f"\n{fence}\n", 1)[0] + "\n"


# A headless stage subagent cannot read a file outside the working directory without a
# permission prompt (PLAN 006, step 5 probe), so `idea` and `plan` carry both templates
# inline; the files under `templates/` stay the tested source and each block is pinned to
# its file byte for byte (owner decision, SPEC 006 AC5).
@pytest.mark.parametrize("skill", sorted(TEMPLATE_BLOCKS))
@pytest.mark.parametrize("language", sorted(BLOCK_HEADINGS))
def test_idea_and_plan_carry_their_templates_pinned_to_the_files(skill, language):
    document, fence = TEMPLATE_BLOCKS[skill]
    text = skill_text(skill)
    template = (PLUGIN / "templates" / f"{document}.{language}.md").read_text()
    assert inline_template(text, BLOCK_HEADINGS[language], fence) == template
    assert text.count(f"{fence}markdown\n") == 2
    choice = section(text, f"## Szablon {document}.md").split("\n### ", 1)[0]
    assert "`language`" in choice
    assert f"templates/{document}.pl.md" in choice and f"templates/{document}.en.md" in choice


def test_plan_writes_in_the_current_language():
    step = section(skill_text("plan"), "## Kroki").split("\n5. ", 1)[1].split("\n6. ", 1)[0]
    assert "`language`" in step
    assert "SPEC" in step
    assert "nie tłumaczysz" in step
