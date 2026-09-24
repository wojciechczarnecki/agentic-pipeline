import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


# SPEC 010, AC4: `implement` closes with a converge pass — a fresh subagent compares the code
# with every AC before the Definition of Done. Text is compared whitespace-collapsed, because
# the skills are hard-wrapped.
def skill_text(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


def section(name: str, heading: str) -> str:
    text = skill_text(name)
    assert f"\n## {heading}\n" in text, f"{name}: no section `{heading}`"
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0].strip()


def collapse(text: str) -> str:
    return " ".join(text.split())


def converge() -> str:
    return collapse(section("implement", "Converge pass"))


def sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.;])\s+", text)


def test_converge_section_sits_between_the_steps_and_the_finish():
    assert converge()
    lines = section("implement", "Procedure").splitlines()
    converge_line = [i for i, line in enumerate(lines) if line.startswith("5. **Converge pass")]
    finish_line = [i for i, line in enumerate(lines) if line.startswith("6. **Finish")]
    assert len(converge_line) == 1 and len(finish_line) == 1
    assert converge_line[0] < finish_line[0]


def test_converge_starts_a_fresh_subagent():
    text = converge()
    for phrase in [
        "fresh subagent",
        "`Agent`",
        "the path of SPEC.md",
        "`git diff origin/main...HEAD`",
        "not your reasoning",
    ]:
        assert phrase in text, phrase


def test_converge_names_the_four_classes():
    text = converge()
    for token in ["`missing`", "`partial`", "`contradicts`", "`unrequested`"]:
        assert token in text, token


def test_converge_checks_every_gap():
    text = converge()
    for phrase in ["check each gap in the code", "reject a false one with a one-sentence reason"]:
        assert phrase in text, phrase


def test_converge_adds_steps_with_evidence():
    text = converge()
    for phrase in ["adds a step", "self-correction loop", "test-first evidence"]:
        assert phrase in text, phrase


def test_converge_removes_unrequested_code():
    assert any(
        all(token in sentence for token in ["`unrequested`", "`## Deviations`", "removal step"])
        for sentence in sentences(converge())
    )


def test_converge_runs_at_most_two_passes():
    text = converge()
    assert "at most two passes" in text
    assert any(
        "after the second pass" in sentence and "escalation" in sentence
        for sentence in sentences(text)
    )


def test_converge_is_recorded_in_the_plan():
    text = converge()
    assert "Converge pass" in text
    assert "PLAN.md" in text


def test_converge_keeps_the_escalation_triggers():
    text = converge()
    for phrase in ["dependency", "migration", "architecture", "within the SPEC's scope"]:
        assert phrase in text, phrase


def test_implement_handoff_reports_the_converge_passes():
    assert "converge" in collapse(section("implement", "Handoff"))
