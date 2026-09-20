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
    blocks = {name: section(name, "Konfiguracja projektu") for name in STAGE_SKILLS}
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
    block = section(name, "Konfiguracja projektu")
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
    assert "rozważ" not in sentence.lower()
    assert "warto" not in sentence.lower()


@pytest.mark.parametrize("name", STAGE_SKILLS)
def test_no_stage_skill_enumerates_views(name):
    for forbidden in ["widok szeroki", "widok wąski", "szeroki i wąski"]:
        assert forbidden not in skill_text(name)


@pytest.mark.parametrize("name", ["planner", "plan-reviewer", "implementer", "reviewer"])
def test_no_agent_enumerates_views(name):
    text = (PLUGIN / "agents" / f"{name}.md").read_text()
    for forbidden in ["widok szeroki", "widok wąski", "szeroki i wąski"]:
        assert forbidden not in text
