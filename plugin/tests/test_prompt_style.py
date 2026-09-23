import re
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
AUDITED = sorted([*PLUGIN.glob("skills/*/SKILL.md"), *PLUGIN.glob("agents/*.md")])

# SPEC 009, AC1: a rule is stated at normal volume with its reason beside it; capitals are
# kept for contract tokens and identifiers only. The list grows only by identifiers.
ALLOWED = frozenset(
    {
        "STOP",
        "RESULT",
        "DONE",
        "ESCALATE",
        "STATUS",
        "METRICS",
        "ESCALATION",
        "SUMMARY",
        "SPEC",
        "PLAN",
        "NNN",
        "AC",
        "ACs",
        "CI",
        "PR",
        "UI",
        "API",
        "CLI",
        "JSON",
        "HTTPS",
        "README",
        "CLAUDE",
        "GATE",
        "E2E",
        "URL",
        "TODO",
    }
)
CAPITALS = re.compile(r"\b[A-Z]{3,}\b")


def prose(text: str) -> str:
    kept, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    # An unclosed fence would hide the rest of the text from the scan.
    assert not fenced, "unbalanced code fence"
    return re.sub(r"`[^`\n]*`", "", "\n".join(kept))


def emphasis_words(text: str) -> list[str]:
    return [word for word in CAPITALS.findall(prose(text)) if word not in ALLOWED]


@pytest.mark.parametrize(
    "path", AUDITED, ids=[path.relative_to(PLUGIN).as_posix() for path in AUDITED]
)
def test_no_capitals_as_emphasis(path):
    assert emphasis_words(path.read_text()) == []


def test_the_audited_set_is_complete():
    names = {path.relative_to(PLUGIN).as_posix() for path in AUDITED}
    skills = ["idea", "plan", "plan-review", "implement", "final-review", "ship", "init"]
    agents = ["planner", "plan-reviewer", "implementer", "reviewer"]
    expected = {f"skills/{name}/SKILL.md" for name in skills} | {
        f"agents/{name}.md" for name in agents
    }
    assert expected <= names


def test_the_scanner_flags_the_old_style():
    old = (
        "**Gate:** you do NOT go on to the next step.\n"
        "## IMPORTANT — what the status triggers\n"
        "- Read the files IN FULL before you change them.\n"
    )
    assert emphasis_words(old) == ["NOT", "IMPORTANT", "FULL"]


def test_the_scanner_ignores_code_and_tokens():
    text = (
        "Write `NOT` as code.\n"
        "```\nALWAYS inside a fence\n```\n"
        "End with `RESULT: ESCALATE`; the SPEC and the PLAN pass GATE 1, and AC2 too.\n"
    )
    assert emphasis_words(text) == []


def test_the_implement_loop_has_no_emphasis():
    text = (PLUGIN / "skills" / "implement" / "SKILL.md").read_text()
    body = text.split("\n## Self-correction loop", 1)[1]
    loop = body.split("```", 2)[1]
    assert loop.strip(), "the loop fence is empty"
    assert [word for word in CAPITALS.findall(loop) if word not in ALLOWED] == []
