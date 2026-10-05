from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SHIP = (PLUGIN / "skills" / "ship" / "SKILL.md").read_text()


# Text is compared whitespace-collapsed, because the skills are hard-wrapped.
def collapse(text: str) -> str:
    return " ".join(text.split())


def section(heading: str) -> str:
    assert f"\n## {heading}\n" in SHIP, heading
    return collapse(SHIP.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0])


# SPEC 014, AC23: Closing runs `--close` after the reviewer's `apply` returns DONE and before the
# notification, which promises green CI on the PR's last commit.
CLOSE = "workflow_metrics.py --close <docs.specsDir>/NNN-<slug>"


def test_closing_runs_close_after_apply():
    closing = section("Closing")
    assert CLOSE in closing
    apply = closing.index("`reviewer/apply` RESULT")
    close = closing.index(CLOSE)
    notify = closing.index("`PushNotification`")
    assert apply < close < notify
    # By name through PATH, never by path (docs/DECISIONS.md, 2026-09-21).
    assert "${CLAUDE_PLUGIN_ROOT}/bin/workflow_metrics.py" not in SHIP
    assert "python3 workflow_metrics.py" not in SHIP
    assert "chore: record stage cost" not in SHIP
    # The wait for CI outlasts the foreground Bash limit, so ship runs the call in the background
    # and reads its exit code and stop line when it ends.
    assert "`run_in_background`" in closing
    assert "exit code" in closing and "stop line" in closing


def test_a_failed_close_asks_the_owner_to_resume_the_closing_step_only():
    closing = section("Closing")
    step = closing.split("4. A non-zero exit", 1)[1].split(" 5. ", 1)[0]
    first = step.index("resume the closing step only")
    assert "(Recommended)" in step[first : first + 80]
    assert "no new `reviewer`" in step
    assert "`reviewer` `apply` again" in step


def test_the_guardrail_says_close_sets_done():
    guardrails = section("Guardrails")
    assert "`workflow_metrics.py --close`" in guardrails
    assert "sets `done`" in guardrails


# SPEC 014, AC25: the start message names the model of every stage.
def test_the_start_message_names_every_stage_model():
    start = section("Start")
    for token in [
        "`plan`",
        "`plan-review`",
        "`implement`",
        "`final-review`",
        "`models.<stage>`",
        "as `model`",
        "session model",
        "`inherit`",
    ]:
        assert token in start, token


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
    assert "`--record-cost`" in starting and "`--close`" in starting


# The guard's warning about a bad `models` entry is not shown in a normal session, so the
# orchestrator names the ignored entries for the owner.
def test_ignored_models_entries_reach_the_owner():
    starting = section("Starting a stage agent")
    assert "name every `models` entry you ignored" in starting
    summary = section("Closing").split(" 5. Summary for the owner", 1)[1]
    assert "the `models` entries you ignored" in summary
    assert "a job `--close` named" in summary
