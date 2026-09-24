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


def chunk() -> str:
    return collapse(section("implement", "Chunk mode"))


def agent_intro(name: str) -> str:
    text = (PLUGIN / "agents" / f"{name}.md").read_text()
    return collapse(text.split("\n## Stage agent contract\n", 1)[0])


# AC6: a chunk carries out one group and ends on a committed, pushed boundary.
def test_implement_chunk_ends_at_the_group_boundary():
    text = chunk()
    for token in [
        "`implement.chunked`",
        "more than one group",
        "first unticked step",
        "green, ticked and committed",
        "`## Chunk notes`",
        "push",
        "`plan-approved`",
        "never ends on a red or uncommitted step",
    ]:
        assert token in text, token


# AC7: the chunk with the last group converges and finishes as one context does.
def test_implement_last_chunk_converges_and_finishes():
    text = chunk()
    for token in [
        "last group",
        "converge pass",
        "the steps it adds",
        "Definition of Done",
        "as one context does",
        "converge-resume rules apply unchanged",
        "after the last group",
    ]:
        assert token in text, token


# AC8: chunking off, or a plan with one group or none, runs as 0.7.0 did.
def test_implement_off_or_one_group_runs_one_context():
    text = chunk()
    for token in [
        "one group or none",
        "one context",
        "as in 0.7.0",
        "no `## Chunk notes` entry",
        "no `implement_chunks`",
    ]:
        assert token in text, token


# AC9: what a chunk note holds, and that the next chunk reads it.
def test_implement_chunk_note_contents():
    text = chunk()
    for token in [
        "the group",
        "decisions taken within the plan's latitude",
        "traps",
        "running `implement_iterations` total",
    ]:
        assert token in text, token


def test_implement_start_reads_the_chunk_notes():
    start = numbered(section("implement", "Procedure"), 1)
    for token in ["`## Chunk notes`", "Chunk mode"]:
        assert token in start, token


# AC10: run on its own, a chunk hands off to a fresh session.
def test_implement_standalone_handoff_after_clear():
    handoff = section("implement", "Handoff")
    bullet = collapse(handoff.split("- **Run on its own:**", 1)[1].split("\n- **", 1)[0])
    for token in ["group boundary", "run `/pipeline:implement NNN` again after `/clear`"]:
        assert token in bullet, token


# AC14: the final chunk writes the metrics once, with the running total.
def test_implement_final_chunk_writes_the_metrics():
    finish = numbered(section("implement", "Procedure"), 6)
    for token in ["`implement_chunks`", "running total"]:
        assert token in finish, token


# AC13: the implementer agent reports its chunk.
def test_implementer_agent_reports_the_chunk():
    intro = agent_intro("implementer")
    for token in ["`CHUNK: <group>/<groups>`", "`STATUS: plan-approved`", "Chunk mode"]:
        assert token in intro, token


def ship_state_row() -> str:
    rows = [
        line
        for line in section("ship", "State").splitlines()
        if line.startswith("| `plan-approved`")
    ]
    assert len(rows) == 1
    return rows[0]


def result_protocol() -> str:
    return collapse(section("ship", "Result protocol"))


# AC12: `ship` reads `plan-approved` from the implementer as the end of a chunk.
def test_ship_state_table_names_the_chunk():
    assert "a chunk ended" in ship_state_row()
    protocol = result_protocol()
    for token in [
        "`STATUS: plan-approved`",
        "a chunk ended",
        "same prompt",
        "`STATUS: implemented`",
    ]:
        assert token in protocol, token


# AC13: a chunk with no progress is a missing RESULT, compared only with the last `DONE`.
def test_ship_no_progress_is_a_missing_result():
    protocol = result_protocol()
    for token in [
        "`CHUNK: <group>/<groups>`",
        "same group as the previous chunk that returned",
        "missing RESULT",
        "escalat",
        "never with the escalated one",
    ]:
        assert token in protocol, token


def readme_section(heading: str) -> str:
    text = (PLUGIN / "README.md").read_text()
    assert f"\n{heading}\n" in text, heading
    return text.split(f"\n{heading}\n", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]


def test_readme_documents_the_chunk_line():
    assert "`CHUNK: <group>/<groups>`" in collapse(readme_section("### The `RESULT` contract"))
    assert "**The chunked implementer.**" in readme_section("### Implementation and review")
    rows = [
        line
        for line in readme_section("### Spec statuses").splitlines()
        if line.startswith("| `plan-approved`")
    ]
    assert len(rows) == 1 and "chunk" in rows[0], rows
