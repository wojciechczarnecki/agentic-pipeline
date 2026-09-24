import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


# SPEC 012: the chunked implementer. The rules live in skill text, compared
# whitespace-collapsed, because the skills are hard-wrapped.
def skill_text(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


def section(name: str, heading: str) -> str:
    text = skill_text(name)
    assert f"\n## {heading}\n" in text, f"{name}: no section `{heading}`"
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0].strip()


def collapse(text: str) -> str:
    return " ".join(text.split())


def numbered(text: str, number: int) -> str:
    start = text.index(f"\n{number}. ") if not text.startswith(f"{number}. ") else 0
    end = text.find(f"\n{number + 1}. ", start + 1)
    return collapse(text[start : end if end != -1 else len(text)])


# AC2: the planner always divides the steps into groups.
def test_plan_marks_groups_always():
    groups = collapse(section("plan", "Step groups"))
    for token in [
        "`### Group N — <name>`",
        "whatever `implement.chunked` says",
        "green, committable state",
        "step numbers run through the whole plan",
        "sections.md",
    ]:
        assert token in groups, token
    assert "Step groups" in numbered(section("plan", "Steps"), 5)


def test_plan_small_plan_is_one_group():
    groups = collapse(section("plan", "Step groups"))
    for token in ["one group", "cache writes", "rule of thumb"]:
        assert token in groups, token
    assert "threshold" not in groups
    assert re.search(r"\d", groups) is None


# AC3: the plan review checks the grouping and fixes it in place.
def test_plan_review_checks_the_groups():
    checklist = numbered(section("plan-review", "Steps"), 3)
    for token in [
        "**groups:**",
        "exactly one group",
        "later group to finish",
        "one group",
        "a plan without groups gets them",
        "in place",
    ]:
        assert token in checklist, token
