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
