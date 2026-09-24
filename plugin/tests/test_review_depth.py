import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]


# SPEC 010, AC5/AC6: the plan and the reviews scale with the change, with no size tiers, and
# the final-review report keeps at most five nits. Text is compared whitespace-collapsed,
# because the skills are hard-wrapped.
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


def step(name: str, heading: str, number: int) -> str:
    return collapse(numbered_step(section(name, heading), number))


def report_step(number: int) -> str:
    return step("final-review", "Report mode", number)


def test_depth_plan_follows_the_change():
    text = step("plan", "Steps", 5)
    for phrase in ["length follows the change", "`n/a — <reason>`"]:
        assert phrase in text, phrase


def test_depth_plan_review_one_line_verdict():
    assert "does not apply gets a one-line verdict" in step("plan-review", "Steps", 3)


def test_depth_final_review_always_runs_three():
    assert "always runs all three perspectives" in report_step(2)


def test_depth_final_review_report_follows_the_findings():
    assert "follows the findings" in report_step(4)


SIZE_WORDS = [
    re.compile(r"\btiers?\b", re.IGNORECASE),
    re.compile("threshold"),
    re.compile("size:"),
]
SIZE_FILES = sorted(
    [
        *PLUGIN.glob("skills/*/SKILL.md"),
        *PLUGIN.glob("agents/*.md"),
        *[
            PLUGIN / "templates" / f"{d}.{lang}.md"
            for d in ("SPEC", "PLAN")
            for lang in ("en", "pl")
        ],
    ]
)


# Green before the change by design: it keeps size classes from coming back.
def test_no_size_tiers_anywhere():
    found = [
        (path.relative_to(PLUGIN).as_posix(), pattern.pattern)
        for path in SIZE_FILES
        for pattern in SIZE_WORDS
        if pattern.search(path.read_text())
    ]
    assert not found, found


def test_nit_cap_in_merge_and_verify():
    text = report_step(3)
    for phrase in ["at most five `nit` findings", "risk or maintenance cost", "left out"]:
        assert phrase in text, phrase


# Checked step by step: the merge sets the count, the report carries it, the decision shows it
# (final review F10).
def test_nit_cap_states_the_count():
    for number in (3, 4, 5):
        assert "`Left out: N nit findings`" in report_step(number), number
    decisions = report_step(5)
    assert "RESULT" in decisions and "SUMMARY" in decisions


def test_nit_cap_metric_counts_reported_nits():
    assert "`final_review_nits` counts the reported nits" in report_step(4)


# A reviewer told to report less finds less, so the cap sits in the merge, not in the prompts.
# Any cap or severity filter in the perspectives' step is rejected, not only the words the
# merge step uses (final review F10).
PERSPECTIVE_FILTERS = [
    re.compile(r"\b(at most|no more than|up to|maximum|limit(ed)? to)\b", re.IGNORECASE),
    re.compile(r"\b(\d+|one|two|three|four|five|six|ten)\s+`?(nit|blocker|worth-fixing)"),
    re.compile(r"\b(only|just)\b[^.;]*\bfindings?\b", re.IGNORECASE),
    re.compile(r"\b(skip|drop|omit|leave out|ignore)\b[^.;]*`?nit", re.IGNORECASE),
]


def test_nit_cap_leaves_the_perspectives_alone():
    text = report_step(2)
    assert "every finding with its severity" in text
    found = [pattern.pattern for pattern in PERSPECTIVE_FILTERS if pattern.search(text)]
    assert not found, found


def test_perspective_filter_patterns_catch_a_cap():
    for sentence in [
        "Report only `blocker` and `worth-fixing` findings.",
        "Report no more than 5 `nit` findings.",
        "Report at most five findings.",
        "Skip `nit` findings.",
    ]:
        assert any(pattern.search(sentence) for pattern in PERSPECTIVE_FILTERS), sentence


def test_nit_cap_reaches_reviewer_and_ship():
    reviewer = collapse((PLUGIN / "agents" / "reviewer.md").read_text())
    metrics = reviewer.split("METRICS of this stage:", 1)[1].split("## Stage agent contract")[0]
    assert "left out" in metrics
    assert "left out" in collapse(section("ship", "Gate: final review"))


def test_compliance_checks_the_red_column():
    assert "red record" in report_step(2)
