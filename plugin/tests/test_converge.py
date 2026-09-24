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
        "`git diff origin/main...HEAD -- . ':(exclude)<docs.specsDir>/NNN-<slug>'`",
        "not your reasoning, your hypotheses or PLAN.md",
    ]:
        assert phrase in text, phrase


# The committed spec directory holds PLAN.md, so a plain diff would hand the plan back to the
# reader that must not see it (final review F2).
def test_converge_diff_leaves_out_the_spec_directory():
    assert any(
        "spec directory" in sentence and "PLAN.md" in sentence for sentence in sentences(converge())
    )


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


# Code a plan step asked for is not an AC, so the fresh reader reports it `unrequested`; only
# code that neither a plan step nor a deviation covers is removed (final review F1).
def test_converge_removes_unrequested_code():
    assert any(
        all(
            token in sentence
            for token in ["`unrequested`", "no plan step", "`## Deviations`", "removal step"]
        )
        for sentence in sentences(converge())
    )


# A step added for an AC the plan left out needs a matrix row for its red record (F5).
def test_converge_added_step_gets_a_matrix_row():
    assert any(
        "added step" in sentence and "row in the AC → steps matrix" in sentence
        for sentence in sentences(converge())
    )


# An AC missing from the plan is the converge pass's job, not a reason to stop early (F8).
def test_converge_owns_an_ac_the_plan_left_out():
    assert any(
        "leaves out" in sentence and "not" in sentence and "escalat" in sentence
        for sentence in sentences(converge())
    )


# A run resumed after an owner decision on a gap must know whether another pass is due (F6).
def test_converge_resumption_after_the_second_pass():
    text = converge()
    assert any(
        "two passes" in sentence
        and "owner decided" in sentence
        and "Definition of Done" in sentence
        and "without a third pass" in sentence
        for sentence in sentences(text)
    )
    assert any(
        "one recorded pass" in sentence and "second pass" in sentence
        for sentence in sentences(text)
    )


def test_implementer_agent_mirrors_the_converge_resumption():
    agent = collapse((PLUGIN / "agents" / "implementer.md").read_text())
    intro = agent.split("## Stage agent contract", 1)[0]
    assert "converge" in intro and "without a third pass" in intro


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
