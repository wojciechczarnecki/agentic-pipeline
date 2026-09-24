from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


# SPEC 010, AC2/AC3: `implement` proves each acceptance test red before the change that makes
# it pass, and `plan`/`plan-review` order the proving test before the product change. Text is
# compared whitespace-collapsed, because the skills are hard-wrapped.
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


def evidence() -> str:
    return collapse(section("implement", "Test-first evidence"))


def test_implement_has_the_test_first_section():
    text = skill_text("implement")
    positions = [
        text.index(f"\n## {heading}\n")
        for heading in [
            "Procedure",
            "Test-first evidence",
            "Self-correction loop (mandatory for every step)",
        ]
        if f"\n## {heading}\n" in text
    ]
    assert len(positions) == 3, "missing section"
    assert positions == sorted(positions)


def test_implement_records_red_in_the_fourth_column():
    text = evidence()
    assert "fourth column of the AC → steps matrix" in text
    assert "the command and the failing assertion line" in text


def test_implement_red_is_an_assertion():
    text = evidence()
    assert "An import, collection or syntax error is not red" in text
    assert "stub" in text


def test_implement_gates_the_tick_on_red():
    text = evidence()
    for phrase in ["is not ticked while its AC has no red record", "`manual`", "`n/a — <reason>`"]:
        assert phrase in text, phrase


def test_implement_handles_a_test_green_before_the_change():
    text = evidence()
    for phrase in [
        "the step writes the test",
        "rewrite",
        "Expected / Found / Why it matters",
        "the test unchanged",
    ]:
        assert phrase in text, phrase


def test_implement_kept_behaviour_rows():
    text = evidence()
    for phrase in [
        "`n/a — kept behaviour`",
        "`${CLAUDE_PLUGIN_ROOT}/templates/PLAN.<language>.md`",
    ]:
        assert phrase in text, phrase


def test_implement_procedure_points_to_the_evidence():
    step = collapse(numbered_step(section("implement", "Procedure"), 2))
    assert "test-first evidence" in step
