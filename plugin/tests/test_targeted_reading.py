from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
READING_SKILLS = ["plan", "plan-review", "implement", "final-review"]


# Text is compared whitespace-collapsed, because the skills are hard-wrapped.
def skill_text(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


def collapse(text: str) -> str:
    return " ".join(text.split())


def section(name: str, heading: str) -> str:
    text = skill_text(name)
    assert f"\n## {heading}\n" in text, f"{name}: no section `{heading}`"
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0].strip()


def numbered_step(block: str, number: int) -> str:
    block = collapse(block)
    start = block.index(f"{number}. **")
    end = block.find(f" {number + 1}. **", start)
    return block[start : end if end != -1 else len(block)]


# SPEC 011, AC18: one rule, one text — like the configuration block, a copy that drifts in
# one skill fails here.
def test_the_reading_section_is_identical_in_four_skills():
    blocks = {name: section(name, "Reading") for name in READING_SKILLS}
    assert len(set(blocks.values())) == 1, sorted(blocks)


@pytest.mark.parametrize(
    "token",
    [
        "SPEC",
        "PLAN",
        "`<docs.conventions>`",
        "in full",
        "`<docs.decisions>`",
        "`<docs.roadmap>`",
        "domain documents",
        "search",
        "the names of the files it changes",
        "whole only when the search leaves the question open",
    ],
)
def test_the_reading_section_names_full_and_searched_documents(token):
    assert token in collapse(section("plan", "Reading")), token


# SPEC 011, AC19: `idea` states how each document of the SPEC's read context was read.
def test_idea_states_how_each_document_was_read():
    gather = numbered_step(section("idea", "Steps"), 1)
    guardrails = collapse(section("idea", "Guardrails"))
    for text in [gather, guardrails]:
        assert "read in full" in text
        assert "searched for" in text
        assert "terms" in text


def test_plan_lists_what_it_read_in_the_approach():
    gather = numbered_step(section("plan", "Steps"), 3)
    for token in ["the Reading section", "`## Approach`", "read in full", "searched for"]:
        assert token in gather, token


def test_plan_review_checks_decisions_by_its_own_search():
    checklist = numbered_step(section("plan-review", "Steps"), 3)
    compliance = checklist.split("**compliance:**", 1)[1].split("; - **", 1)[0]
    for token in ["`<docs.decisions>`", "own search", "the Reading section"]:
        assert token in compliance, token


def test_implement_and_the_perspectives_follow_the_reading_section():
    assert "the Reading section" in numbered_step(section("implement", "Procedure"), 1)
    perspectives = numbered_step(section("final-review", "Report mode"), 2)
    assert "the Reading section" in perspectives
