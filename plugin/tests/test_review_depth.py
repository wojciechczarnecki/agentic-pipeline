import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


# SPEC 010, AC5/AC6: the plan and the reviews scale with the change, with no size tiers, and
# the final-review report keeps at most five nits. Text is compared whitespace-collapsed,
# because the skills are hard-wrapped.
def skill_text(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


def section(name: str, heading: str) -> str:
    text = skill_text(name)
    assert f"\n## {heading}\n" in text, f"{name}: no section `{heading}`"
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0].strip()


def collapse(text: str) -> str:
    return " ".join(text.split())


def numbered_step(block: str, number: int) -> str:
    assert f"\n{number}. " in f"\n{block}", number
    return f"\n{block}".split(f"\n{number}. ", 1)[1].split(f"\n{number + 1}. ", 1)[0]


def step(name: str, heading: str, number: int) -> str:
    return collapse(numbered_step(section(name, heading), number))


def report_step(number: int) -> str:
    return step("final-review", "Report mode", number)


def test_depth_plan_follows_the_change():
    text = step("plan", "Steps", 5)
    for phrase in ["length follows the change", "`n/a — <reason>`"]:
        assert phrase in text, phrase


def test_depth_plan_review_one_line_verdict():
    assert "does not apply gets a one-line verdict" in step("plan-review", "Steps", 3)


def test_depth_final_review_always_runs_three():
    assert "always runs all three perspectives" in report_step(2)


def test_depth_final_review_report_follows_the_findings():
    assert "follows the findings" in report_step(4)


SIZE_WORDS = [
    re.compile(r"\btiers?\b", re.IGNORECASE),
    re.compile("threshold"),
    re.compile("size:"),
]
SIZE_FILES = sorted(
    [
        *PLUGIN.glob("skills/*/SKILL.md"),
        *PLUGIN.glob("agents/*.md"),
        *[
            PLUGIN / "templates" / f"{d}.{lang}.md"
            for d in ("SPEC", "PLAN")
            for lang in ("en", "pl")
        ],
    ]
)


# Green before the change by design: it keeps size classes from coming back.
def test_no_size_tiers_anywhere():
    found = [
        (path.relative_to(PLUGIN).as_posix(), pattern.pattern)
        for path in SIZE_FILES
        for pattern in SIZE_WORDS
        if pattern.search(path.read_text())
    ]
    assert not found, found
