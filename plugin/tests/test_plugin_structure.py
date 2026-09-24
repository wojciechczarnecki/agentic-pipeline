import json
import os
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
HOOKS = PLUGIN / "hooks" / "hooks.json"
PLUGIN_ROOT_VARIABLE = "${CLAUDE_PLUGIN_ROOT}"

EXPECTED_EVENTS = {"PreToolUse", "PostToolUse", "Notification"}
EXPECTED_SKILLS = {"idea", "plan", "plan-review", "implement", "final-review", "ship", "init"}
EXPECTED_AGENTS = {"planner", "plan-reviewer", "implementer", "reviewer"}


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text().splitlines()
    assert lines and lines[0] == "---", path
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            return fields
        if not line.startswith((" ", "-")) and ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    raise AssertionError(f"{path}: the frontmatter never closes")


def test_skills_and_agents_are_complete():
    skills = {path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md")}
    assert skills == EXPECTED_SKILLS
    for name in skills:
        fields = frontmatter(PLUGIN / "skills" / name / "SKILL.md")
        assert fields.get("name") == name
        assert fields.get("description")
    agents = {path.stem for path in (PLUGIN / "agents").glob("*.md")}
    assert agents == EXPECTED_AGENTS
    for name in agents:
        fields = frontmatter(PLUGIN / "agents" / f"{name}.md")
        assert fields.get("name") == name
        assert fields.get("description")
        assert "skills" in fields
        assert fields.get("model")


def test_every_agent_points_at_an_existing_skill():
    for path in (PLUGIN / "agents").glob("*.md"):
        referenced = [
            line.strip().removeprefix("- ").strip()
            for line in path.read_text().splitlines()
            if line.startswith("  - ")
        ]
        assert referenced, path
        for skill in referenced:
            assert (PLUGIN / "skills" / skill / "SKILL.md").is_file(), (path, skill)


def hook_commands() -> list[str]:
    data = json.loads(HOOKS.read_text())
    commands = []
    for entries in data["hooks"].values():
        for entry in entries:
            for hook in entry["hooks"]:
                commands.append(hook["command"])
    return commands


def test_every_expected_event_is_wired():
    data = json.loads(HOOKS.read_text())
    assert EXPECTED_EVENTS <= set(data["hooks"])
    matchers = {entry.get("matcher") for entry in data["hooks"]["PreToolUse"]}
    assert {"Bash", "AskUserQuestion"} <= matchers
    assert {entry.get("matcher") for entry in data["hooks"]["PostToolUse"]} == {"Edit|Write"}


EXPECTED_WIRING = {
    ("PreToolUse", "Bash"): "bin/guard",
    ("PreToolUse", "AskUserQuestion"): "bin/notify-attention.sh",
    ("PostToolUse", "Edit|Write"): "bin/format-file.sh",
    ("Notification", None): "bin/notify-attention.sh",
}


# The event a script is wired to is the whole point of the file: a guard moved off
# PreToolUse/Bash switches the guardrails off while every other assertion stays green.
@pytest.mark.parametrize("event, matcher", sorted(EXPECTED_WIRING, key=str))
def test_each_event_runs_its_own_script(event, matcher):
    data = json.loads(HOOKS.read_text())
    entries = [entry for entry in data["hooks"][event] if entry.get("matcher") == matcher]
    assert len(entries) == 1, (event, matcher)
    commands = [hook["command"] for hook in entries[0]["hooks"]]
    assert commands == [f'"{PLUGIN_ROOT_VARIABLE}/{EXPECTED_WIRING[(event, matcher)]}"']


# An unquoted path splits into several words when the plugin directory holds a space, and
# `claude plugin validate --strict` refuses it; the command is the quoted path and nothing else.
@pytest.mark.parametrize("command", hook_commands())
def test_hook_commands_are_one_quoted_path(command):
    assert command.startswith('"') and command.endswith('"'), command
    assert command.count('"') == 2, command


@pytest.mark.parametrize("command", hook_commands())
def test_hook_paths_are_plugin_relative(command):
    command = command.strip('"')
    assert command.startswith(PLUGIN_ROOT_VARIABLE)
    assert "CLAUDE_PROJECT_DIR" not in command
    relative = command[len(PLUGIN_ROOT_VARIABLE) :].lstrip("/")
    assert not relative.startswith("/")
    target = PLUGIN / relative
    assert target.is_file(), relative
    assert os.access(target, os.X_OK), relative


def test_every_eval_case_has_a_grader():
    # `results/` is where `claude plugin eval` writes its reports; it is gitignored, so
    # CI never sees it, but a local run would otherwise fail this test as a case
    # without a case.yaml.
    cases = sorted(
        path for path in (PLUGIN / "evals").iterdir() if path.is_dir() and path.name != "results"
    )
    assert cases, "plugin/evals holds no case"
    for case in cases:
        manifest = case / "case.yaml"
        assert manifest.is_file(), f"{case.name}: no case.yaml"
        assert "schema_version" in manifest.read_text(), f"{case.name}: no schema_version"
        graders = case / "graders"
        assert graders.is_dir() and any(graders.iterdir()), f"{case.name}: no grader"


# The stage skills call the metrics checker by name through PATH, which Claude Code extends
# with the plugin's `bin/`; the call resolves only while the script is executable and
# carries its own interpreter.
def test_metrics_checker_runs_from_path():
    script = PLUGIN / "bin" / "workflow_metrics.py"
    assert os.access(script, os.X_OK)
    assert script.read_text().splitlines()[0] == "#!/usr/bin/env python3"


# SPEC 011, AC17: effort stays inherited from the session until the Stage 7 comparison
# measures the defaults. Remove this test when the measured defaults land.
def test_no_agent_sets_effort_yet():
    for path in sorted((PLUGIN / "agents").glob("*.md")):
        assert "effort" not in frontmatter(path), path.name
