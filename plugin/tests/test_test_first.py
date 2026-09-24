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


def green_before_branches() -> list[str]:
    raw = section("implement", "Test-first evidence")
    block = raw.split("\n- A proving test that is green before the change", 1)[1]
    block = block.split("\n- ", 1)[0]
    return [collapse(item) for item in block.split("\n  - ")[1:]]


def test_implement_records_red_in_the_fourth_column():
    text = evidence()
    assert "Before that change, run the AC's proving test." in text
    assert "fourth column of the AC → steps matrix" in text
    assert "the command and the failing assertion line" in text


def test_implement_red_is_an_assertion():
    text = evidence()
    assert "An import, collection or syntax error is not red" in text
    assert "add a stub first" in text


# The gate sits on the step that makes the AC's proving test pass, so an AC delivered across
# several steps does not lock the earlier ones (final review F4).
def test_implement_gates_the_tick_on_red():
    text = evidence()
    for phrase in [
        "The step that makes an AC's proving test pass is not green and is not ticked while "
        "that AC has no red record",
        "`manual`",
        "`n/a — <reason>`",
    ]:
        assert phrase in text, phrase


# Each branch is pinned on its own bullet, so swapping rewrite and escalate fails (F3, F9).
def test_implement_handles_a_test_green_before_the_change():
    branches = green_before_branches()
    assert len(branches) == 3, branches
    weak, exists, given = branches
    assert "the step writes the test" in weak and "does not exercise" in weak
    assert "rewrite" in weak and "escalate" not in weak
    assert "the step writes the test" in exists and "does exercise" in exists
    assert "gap in the SPEC" in exists and "escalate" in exists and "rewrite" not in exists
    for phrase in [
        "existed before",
        "the plan gives it verbatim",
        "escalate",
        "Expected / Found / Why it matters",
        "the test unchanged",
    ]:
        assert phrase in given, phrase
    assert "rewrite" not in given


def test_implement_new_behaviour_is_never_kept_behaviour():
    assert "An AC that asks for new behaviour never gets this mark." in evidence()


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
    order = ["proving test first", "red record", "product change", "self-correction loop"]
    positions = [step.index(phrase) for phrase in order]
    assert positions == sorted(positions), order


def plan_step(name: str, number: int) -> str:
    return collapse(numbered_step(section(name, "Steps"), number))


def test_plan_orders_the_proving_test_first():
    step = plan_step("plan", 5)
    assert "writes and runs its proving test before the product change" in step


def test_plan_leaves_the_red_column_to_implement():
    step = plan_step("plan", 6)
    for phrase in ["fourth column", "`manual`", "`n/a — <reason>`"]:
        assert phrase in step, phrase


def test_plan_review_checks_the_order_and_the_column():
    step = numbered_step(section("plan-review", "Steps"), 3)
    items = [collapse(item) for item in step.split("\n   - ")[1:]]
    matching = [item for item in items if item.startswith("**test-first:**")]
    assert len(matching) == 1, "no **test-first:** bullet"
    for phrase in ["before the product change", "fourth column"]:
        assert phrase in matching[0], phrase
