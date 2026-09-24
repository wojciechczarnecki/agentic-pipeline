from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SHIP = (PLUGIN / "skills" / "ship" / "SKILL.md").read_text()


# Text is compared whitespace-collapsed, because the skills are hard-wrapped.
def collapse(text: str) -> str:
    return " ".join(text.split())


def section(heading: str) -> str:
    assert f"\n## {heading}\n" in SHIP, heading
    return collapse(SHIP.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0])


# SPEC 011, AC13: the cost is recorded once every stage has finished — after apply returns
# DONE — and before the notification, which promises green CI on the PR's last commit.
def test_closing_records_cost_between_apply_and_notification():
    closing = section("Closing")
    call = "workflow_metrics.py --record-cost <docs.specsDir>/NNN-<slug>"
    assert call in closing
    apply = closing.index("`reviewer/apply` RESULT")
    record = closing.index(call)
    notify = closing.index("`PushNotification`")
    assert apply < record < notify
    for token in [
        "`chore: record stage cost for NNN`",
        "`git push`",
        "`gh pr checks",
        "git status --porcelain",
        "does not stop",
    ]:
        assert token in closing, token
    # By name through PATH, never by path (docs/DECISIONS.md, 2026-09-21).
    assert "${CLAUDE_PLUGIN_ROOT}/bin/workflow_metrics.py" not in SHIP
    assert "python3 workflow_metrics.py" not in SHIP


def test_the_guardrail_names_the_cost_exception():
    closing = section("Closing")
    sentence = closing.split("You do not edit spec files or documents yourself", 1)[1]
    sentence = sentence.split(".", 1)[0]
    assert "cost" in sentence
    assert "--record-cost" in sentence or "script" in sentence


# SPEC 011, AC15: `model` is passed only for a stage whose entry is not `inherit`.
def test_ship_passes_the_model_only_when_not_inherit():
    starting = section("Starting a stage agent")
    for token in [
        "`models.<stage>`",
        "`plan` → `planner`",
        "`plan-review` → `plan-reviewer`",
        "`implement` → `implementer`",
        "`final-review` → `reviewer`",
        "`sonnet`",
        "`opus`",
        "`haiku`",
        "`fable`",
        "`inherit`",
        "pass no `model`",
        "as `model`",
    ]:
        assert token in starting, token


# `--record-cost` attributes a stage agent to its spec by the spec directory in its prompt.
def test_the_stage_prompt_names_the_spec_directory():
    starting = section("Starting a stage agent")
    assert "`<docs.specsDir>/NNN-<slug>/SPEC.md`" in starting
    assert "`--record-cost`" in starting
