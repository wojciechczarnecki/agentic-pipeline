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
CLOSING_SKILLS = ["plan", "plan-review", "implement", "final-review"]


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


def final_review_step(mode: str, number: int) -> str:
    block = skill("final-review").split(f"\n## {mode}\n", 1)[1].split("\n## ", 1)[0]
    return collapse(f"\n{block}".split(f"\n{number}. ", 1)[1].split(f"\n{number + 1}. ", 1)[0])


# AC3: the tests perspective still proves that tests test something by breaking the code.
def test_final_review_tests_break_the_code():
    step = final_review_step("Report mode", 2)
    tests = step.split("**Tests:**", 1)[1].split("The finding format", 1)[0]
    assert "Break the code" in tests
    assert "see it fail" in tests and "restore" in tests


# AC27: without the Agent tool the perspectives are not independent, and the report says so.
def test_final_review_notes_one_context():
    sentence = "the three perspectives ran in one context and are not independent"
    assert "`Agent` tool" in final_review_step("Report mode", 2)
    report = final_review_step("Report mode", 4)
    assert sentence in report and "SUMMARY" in report
    assert sentence in collapse(agent_body("reviewer"))


def test_final_review_finding_form():
    assert "`- **F<n>** `<blocker|worth-fixing|nit>` — " in final_review_step("Report mode", 4)


# AC23: apply ends at a PR with green CI; `--close` sets `done`.
def test_final_review_apply_ends_at_green_ci():
    text = collapse(skill("final-review"))
    apply = collapse(skill("final-review").split("\n## Apply mode\n", 1)[1].split("\n## ", 1)[0])
    assert "status stays `implemented`" in apply
    assert "never set `done`" in text
    third = final_review_step("Apply mode", 3)
    assert "`workflow_metrics.py --derive <spec-dir>`" in third
    assert third.index("--derive") < third.index("--check") < third.index("commit")
    assert "own commit" in final_review_step("Apply mode", 4)
    sixth = final_review_step("Apply mode", 6)
    assert "`workflow_metrics.py --close <spec-dir>`" in sixth
    assert "`run_in_background`" in sixth
    assert "status `done`" not in collapse(agent(("reviewer")))


def ship_section(heading: str) -> str:
    assert f"\n## {heading}\n" in skill("ship"), heading
    return collapse(skill("ship").split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0])


# AC16: the kind goes into the fixed-form entry; only `decision` entries count toward the STOP.
def test_ship_stops_on_the_third_decision():
    protocol = ship_section("Result protocol")
    assert "Increment `metrics.escalations`" not in skill("ship")
    for token in (
        "`KIND`",
        "`- YYYY-MM-DD — <stage> — `<kind>` — <question> — <decision>`",
        "valid `KIND:`",
        "counts as `decision`",
    ):
        assert token in protocol, token
    third = protocol.split("for the third time", 1)[0].rsplit("- ", 1)[1]
    assert "`decision`" in third and "same stage" in third
    assert "`permission` or `tooling`" in protocol
    assert "do not count" in protocol


def test_the_state_table_names_close_and_no_chunk():
    state = ship_section("State")
    assert "`workflow_metrics.py --close`" in state and "`done`" in state
    assert "chunk" not in state.lower()
    assert "status stays `implemented`" in state


def test_the_gate_records_the_gate_entry_form():
    gate = ship_section("Gate: final review")
    assert (
        "`- YYYY-MM-DD — final-review — `gate` — <question> — `accepted`: F1, F2; `rejected`: F3`"
        in gate
    )
    assert "`none`" in gate


def test_ship_no_longer_counts_a_derived_key():
    text = collapse(skill("ship"))
    for sentence in re.split(r"(?<=[.;:])\s+", text):
        for key in workflow_metrics.DERIVED:
            if f"`{key}`" in sentence:
                assert "--derive" in sentence or "--close" in sentence, (key, sentence)


RITUAL_WORDS = (
    "converge pass",
    "converge_gaps",
    "Red before the change",
    "Czerwony przed zmian\u0105",
    "Test-first evidence",
    "chunk mode",
    "Chunk notes",
    "Notatki chunk\u00f3w",
    "CHUNK:",
    "implement_chunks",
    "### Group N",
    "### Grupa N",
)


# AC1, AC2, AC4: none of the three rituals is described as current behaviour in the stage text.
def test_no_ritual_returns():
    found = []
    for folder in ("skills", "agents", "templates"):
        for path in sorted((PLUGIN / folder).rglob("*")):
            if not path.is_file():
                continue
            text = path.read_text().lower()
            found += [(path.name, word) for word in RITUAL_WORDS if word.lower() in text]
    assert not found, found


# Final review of SPEC 014. F1: a report with no findings still records a gate entry with two
# empty lists, which --derive needs and --close checks.
def test_a_review_without_findings_records_an_empty_gate():
    gate = collapse(ship_section("Gate: final review"))
    assert "`accepted`: none; `rejected`: none" in gate
    report = collapse(final_review_step("Report mode", 5))
    assert "`accepted`: none; `rejected`: none" in report


# F4: the flaky entry names the CI job as a code span and gets its own commit and push.
def test_the_flaky_entry_names_the_job_and_is_committed():
    wait = collapse(final_review_step("Apply mode", 4))
    assert "names the CI job as a code span" in wait
    assert "`docs: record flaky job of NNN <slug>`" in wait


# F8: run on their own, implement and plan-review append escalations in the fixed form.
@pytest.mark.parametrize("name", ["implement", "plan-review"])
def test_a_standalone_escalation_uses_the_fixed_form(name):
    text = collapse(skill(name))
    assert f"`- YYYY-MM-DD — {name} — `<kind>` — <question> — <decision>`" in text


# F9: a review log without findings says so with a `none` item.
def test_plan_review_writes_none_without_findings():
    assert "`- `none` — no findings`" in collapse(skill("plan-review"))


# F14: a verbatim test green before the change is the SPEC-gap trigger, not a trigger of its own.
def test_a_verbatim_green_test_is_a_spec_gap():
    first = collapse(heading_block(skill("implement"), "## Test first"))
    assert "the same gap in the SPEC, escalated under the same trigger" in first


# F15: the implementer agent repeats the minimality rule of AC17.
def test_the_implementer_adds_nothing_beyond_the_change():
    assert "nothing beyond what the change needs" in collapse(agent_body("implementer"))
