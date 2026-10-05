import re
import sys
from pathlib import Path

import pytest
from test_stage_skills import CLOSING_STEPS, closing_step

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "bin"))

import workflow_metrics  # noqa: E402

# SPEC 014: fewer rituals, more code in the pipeline loop. The tests here pin the identifiers
# and the order the stage text must keep, not its prose.
DERIVE = "`workflow_metrics.py --derive <spec-dir>`"
CHECK = "`workflow_metrics.py --check <spec-dir>`"
# Skills whose closing step runs --derive and then --check; the others join as their step lands.
CLOSING_SKILLS = ["plan", "plan-review", "implement"]


def collapse(text: str) -> str:
    return " ".join(text.split())


def skill(name: str) -> str:
    return (PLUGIN / "skills" / name / "SKILL.md").read_text()


def agent(name: str) -> str:
    return (PLUGIN / "agents" / f"{name}.md").read_text()


def agent_body(name: str) -> str:
    return agent(name).split("## Stage agent contract", 1)[0]


def heading_block(text: str, heading: str) -> str:
    assert heading in text, f"no section `{heading}`"
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def test_implement_has_no_ritual_sections():
    text = skill("implement")
    for heading in ("## Test-first evidence", "## Converge pass", "## Chunk mode"):
        assert heading not in text, heading
    body = agent_body("implementer").lower()
    for word in ("chunk", "converge"):
        assert word not in body, word


# AC3: test-first stays as one paragraph of guidance.
def test_implement_keeps_test_first_guidance():
    block = collapse(heading_block(skill("implement"), "## Test first"))
    for token in (
        "proving test",
        "before the product change",
        "run it",
        "does not exercise the AC",
        "rewrite",
        "gap in the SPEC",
        "tests perspective",
    ):
        assert token in block, token
    assert "\n\n" not in heading_block(skill("implement"), "## Test first").strip()


# AC8: the iteration count is a note on the ticked step, so it survives an escalation.
def test_implement_ticks_with_the_iteration_note():
    procedure = collapse(heading_block(skill("implement"), "## Procedure"))
    step = procedure.split("2. **Step by step", 1)[1].split(" 3. ", 1)[0]
    assert "`iterations: <k>`" in step
    assert "beyond the first attempt" in step
    assert "never zero" in step
    assert "0 when the step was green at once" in step


# AC17: dependencies the SPEC or the plan accepts are installed by the implementer itself.
def test_implement_installs_accepted_dependencies():
    text = collapse(skill("implement"))
    for token in (
        "## Owner decisions",
        "accepts you add yourself",
        "escalates",
        "beyond what the change needs",
        "its own Bash call",
        "`uv add`",
        "`uv lock`",
        "`uv sync`",
        "`npm install`",
    ):
        assert token in text, token
    body = collapse(agent_body("implementer"))
    for token in ("## Owner decisions", "its own Bash call", "`uv add`"):
        assert token in body, token


def test_implement_deviation_form():
    procedure = collapse(heading_block(skill("implement"), "## Procedure"))
    step = procedure.split("3. **Deviations:**", 1)[1].split(" 4. ", 1)[0]
    assert "`- `major` — " in step and "`- `minor` — " in step


@pytest.mark.parametrize("name", CLOSING_SKILLS)
def test_every_stage_closes_with_derive_then_check(name):
    step = collapse(closing_step(name))
    assert DERIVE in step and CHECK in step, name
    assert step.index(DERIVE) < step.index(CHECK), name
    assert "CLAUDE_PLUGIN_ROOT" not in step


# A key `--derive` writes is not one the agent counts: a derived key in the closing step is
# only named in a sentence that says `--derive` writes it.
@pytest.mark.parametrize("name", CLOSING_SKILLS)
def test_no_skill_counts_a_derived_key(name):
    step = collapse(closing_step(name))
    for sentence in re.split(r"(?<=[.;:])\s+", step):
        for key in workflow_metrics.DERIVED:
            if f"`{key}`" in sentence:
                assert "--derive" in sentence, (name, key, sentence)
    assert set(CLOSING_STEPS[name][1]).isdisjoint(workflow_metrics.DERIVED), name


# AC13: the plan and its review require the pass line of a manual scenario.
@pytest.mark.parametrize("name", ["plan", "plan-review"])
def test_plan_requires_the_pass_line(name):
    text = collapse(skill(name))
    assert "`Pass when:`" in text
    assert "Section map" in text
    assert "`n/a — <reason>`" in text


# AC18: no step is performed by the owner; manual verification stays in its own section.
def test_plan_writes_no_owner_step():
    text = collapse(skill("plan"))
    assert "no step for the owner to perform" in text
    assert "### Manual (performed by the owner)" in text
    review = collapse(skill("plan-review"))
    assert "performed by the owner" in review
    assert "`major`" in review.split("**manual:**", 1)[1].split(" - **", 1)[0]
    assert "fix it in place" in review or "fix in place" in review
    assert "stays allowed" in review


# AC11: a review-log finding is a list item that starts with its severity token.
def test_plan_review_finding_form():
    step = collapse(heading_block(skill("plan-review"), "## Steps"))
    record = step.split("4. **Make the fixes", 1)[1].split(" 5. ", 1)[0]
    assert "list item" in record
    for token in ("`blocker`", "`major`", "`minor`"):
        assert token in record, token


@pytest.mark.parametrize("name", ["plan", "plan-review"])
def test_no_group_or_test_first_column_left(name):
    text = skill(name)
    for token in (
        "## Step groups",
        "**groups:**",
        "**test-first:**",
        "fourth column",
        "implement.chunked",
        "Group N",
    ):
        assert token not in text, (name, token)


def test_plan_no_longer_sets_the_derived_counters():
    step = collapse(closing_step("plan"))
    assert "`started_at`" in step
    assert "set `escalations: 0`" not in step
