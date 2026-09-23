import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


# SPEC 009: the sentence-level findings of the prompt audit (AUDIT.md beside the SPEC). Text is
# compared whitespace-collapsed, because the skills are hard-wrapped.
def skill_text(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


def section(name: str, heading: str) -> str:
    text = skill_text(name)
    assert f"\n## {heading}\n" in text, f"{name}: no section `{heading}`"
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0].strip()


def collapse(text: str) -> str:
    return " ".join(text.split())


def role(name: str) -> str:
    return collapse(skill_text(name).split("\n## ", 1)[0])


# P2: the plan reviewer is asked for the real targets, not told that its success is findings.
def test_plan_review_role_drops_the_success_line():
    text = collapse(skill_text("plan-review"))
    assert "Assume the plan has gaps" not in text
    assert "your success is" not in text


def test_plan_review_role_names_the_targets_and_the_report():
    paragraph = role("plan-review")
    for phrase in [
        "an AC without steps or a test",
        "a broken decision",
        "a step whose verification cannot run",
        "with its severity",
        "what you checked and found sound",
        "it is you who decides whether the plan is ready for implementation",
    ]:
        assert phrase in paragraph, phrase


# P3: the heading that only raised the volume is gone; the paragraph under it is unchanged.
STATUS_PARAGRAPH = """\
`plan-approved` triggers the approval rule: from that moment `/pipeline:implement` edits
the files within the plan's scope without asking. That is why the escalation triggers of
step 5 are absolute — do not approve a plan with an unaccepted dependency or migration, even
if it seems obvious."""


def test_plan_review_status_heading_keeps_the_paragraph():
    assert section("plan-review", "What the status triggers") == STATUS_PARAGRAPH


def test_plan_review_status_heading_has_no_emphasis():
    headings = [line for line in skill_text("plan-review").splitlines() if line.startswith("#")]
    assert not [line for line in headings if "IMPORTANT" in line]


# S1: the strategy hint (read the full output, start from the first error) is gone from the
# loop; the other sub-points keep their content under new letters. Lower-cased, so the check
# survives the P1 case changes in the same fence.
def implement_loop() -> str:
    body = section("implement", "Self-correction loop (mandatory for every step)")
    return body.split("```", 2)[1].lower()


def test_implement_loop_drops_the_strategy_hint():
    loop = implement_loop()
    assert "read the full error output" not in collapse(loop)
    assert "start from the first" not in collapse(loop)


def test_implement_loop_keeps_the_other_sub_points():
    loop = implement_loop()
    assert re.findall(r"^\s+([a-z])\. ", loop, re.M) == ["a", "b", "c", "d"]
    points = dict(re.findall(r"^\s+([a-z])\. (.*)$", loop, re.M))
    assert points["a"].startswith("establish the cause")
    assert points["b"].startswith("a mismatch with the plan → escalation")
    assert points["c"].startswith("a product defect")
    assert points["d"].startswith("a bug → fix it and go back to 1.")
    assert "never fit the test to the defect" in collapse(loop)


# S2: the gate is stated plainly, without the run of "no exceptions / no … / no …".
GATE = (
    "**Gate:** you go on to the next step only when the current one's verification is green. "
    "A test you suspect is flaky is still red, and a skipped test is not green."
)


def test_implement_gate_is_stated_plainly():
    text = skill_text("implement")
    paragraphs = [p for p in text.split("\n\n") if p.startswith("**Gate:**")]
    assert [collapse(p) for p in paragraphs] == [GATE]


def test_implement_gate_drops_the_no_exceptions_line():
    assert "No exceptions" not in skill_text("implement")


# S3: the "be thorough" line is gone; the three perspectives set the depth of the review.
def test_final_review_drops_the_thoroughness_line():
    assert "Green tests ≠ correct code" not in skill_text("final-review")


def test_final_review_keeps_the_other_guardrails():
    bullets = [
        line for line in section("final-review", "Guardrails").splitlines() if line.startswith("- ")
    ]
    assert len(bullets) == 4


# R1: idea neither chains into ship nor approves its own assumptions (0.6.0 canary).
def test_idea_guardrails_end_the_stage_at_the_handoff():
    guardrails = collapse(section("idea", "Guardrails"))
    for phrase in ["You end the stage at the handoff", "never by `idea`", "GATE 1 is the owner's"]:
        assert phrase in guardrails, phrase


def test_idea_guardrails_keep_assumptions_for_the_owner():
    guardrails = collapse(section("idea", "Guardrails"))
    for phrase in [
        "You do not remove the `(assumption)` suffix or set `spec-ready` before the owner has "
        "answered on every such item",
        "including in a session without `AskUserQuestion`, leaves the SPEC `spec-draft`",
    ]:
        assert phrase in guardrails, phrase
