import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "workflow_metrics.py"
_spec = importlib.util.spec_from_file_location("workflow_metrics", SCRIPT)
workflow_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(workflow_metrics)

MEASURED_SPEC = """---
status: done
stage_history:
  - "spec-ready — 2026-09-15"
metrics:
  started_at: "2026-09-15T09:00"
  finished_at: "2026-09-15T13:30"
  plan_review_blockers: 1
  plan_review_majors: 2
  final_review_blockers: 0
  final_review_worth_fixing: 1
  findings_accepted: 3
  findings_rejected: 1
  escalations: 2
---

# SPEC 014 — e2e
"""

LEGACY_SPEC = """---
status: done
stage_history:
  - "done — 2026-08-12"
---

# SPEC 013 — legacy
"""


def write_specs(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, text in [("013-legacy", LEGACY_SPEC), ("014-e2e", MEASURED_SPEC)]:
        (root / name).mkdir(parents=True)
        (root / name / "SPEC.md").write_text(text)
    return root


def test_metrics_block_is_parsed_without_stage_history():
    metrics = workflow_metrics.parse_metrics(MEASURED_SPEC)
    assert metrics["plan_review_blockers"] == "1"
    assert metrics["started_at"] == "2026-09-15T09:00"
    assert not any(key.startswith("-") for key in metrics)


def test_spec_without_metrics_yields_nothing():
    assert workflow_metrics.parse_metrics(LEGACY_SPEC) == {}


def test_lead_time_needs_both_timestamps():
    assert workflow_metrics.lead_time_hours(workflow_metrics.parse_metrics(MEASURED_SPEC)) == 4.5
    assert workflow_metrics.lead_time_hours({"started_at": "2026-09-15T09:00"}) is None


def test_report_skips_legacy_specs_and_computes_ratios(tmp_path):
    report = workflow_metrics.render(workflow_metrics.collect(write_specs(tmp_path)))
    assert "013-legacy" not in report
    assert "| 014-e2e | 4.5 |" in report
    assert "Significant findings caught before code: 75% (3/4)" in report
    assert "Final-review findings accepted: 75% (3/4)" in report
    assert "Escalations per spec: 2.0" in report


def test_empty_specs_dir_reports_missing_metrics(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path)], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "No spec carries a metrics block yet." in result.stdout


def test_specs_dir_comes_from_the_config(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "workflow.json").write_text('{"docs": {"specsDir": "plans"}}')
    write_specs(tmp_path / "plans")
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "| 014-e2e | 4.5 |" in result.stdout


def test_a_faulty_key_warns_and_the_report_goes_on(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "workflow.json").write_text(
        '{"nope": 1, "docs": {"specsDir": "plans"}}'
    )
    write_specs(tmp_path / "plans")
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "workflow.json: unknown key `nope`" in result.stderr
    assert "| 014-e2e | 4.5 |" in result.stdout


@pytest.mark.parametrize("language", ["EN", "polski"])
def test_an_unsupported_language_warns_and_does_not_stop_the_report(tmp_path, language):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "workflow.json").write_text(
        f'{{"language": "{language}", "docs": {{"specsDir": "plans"}}}}'
    )
    write_specs(tmp_path / "plans")
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "workflow.json: `language` has to be one of: en, pl" in result.stderr
    assert "| 014-e2e | 4.5 |" in result.stdout


def test_an_unreadable_config_is_reported(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "workflow.json").write_text("{not json")
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "is not valid JSON" in result.stderr


COMPLETE = {
    "started_at": '"2026-09-15T09:00"',
    "finished_at": '"2026-09-15T13:30"',
    "plan_steps": "5",
    "plan_review_blockers": "1",
    "plan_review_majors": "2",
    "plan_changes": "7",
    "implement_steps": "5",
    "implement_iterations": "2",
    "deviations": "1",
    "escalations": "2",
    "final_review_blockers": "0",
    "final_review_worth_fixing": "1",
    "final_review_nits": "3",
    "findings_accepted": "3",
    "findings_rejected": "1",
}


def spec_dir(tmp_path: Path, status: str, metrics: dict[str, str], name="014-e2e") -> Path:
    directory = tmp_path / name
    directory.mkdir(parents=True, exist_ok=True)
    block = "".join(f"  {key}: {value}\n" for key, value in metrics.items())
    (directory / "SPEC.md").write_text(
        f"---\nstatus: {status}\nmetrics:\n{block}---\n\n# SPEC 014 — e2e\n"
    )
    return directory


def run_check(directory) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(directory)],
        capture_output=True,
        text=True,
    )


def test_check_is_silent_on_a_complete_spec(tmp_path):
    result = run_check(spec_dir(tmp_path, "done", COMPLETE))
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_check_accepts_unquoted_timestamps(tmp_path):
    metrics = dict(COMPLETE, started_at="2026-09-15T09:00", finished_at="2026-09-15T13:30")
    assert workflow_metrics.check(spec_dir(tmp_path, "done", metrics)) == []


def test_check_rejects_a_malformed_timestamp(tmp_path):
    metrics = dict(COMPLETE, started_at="2026-09-15 09:00")
    problems = workflow_metrics.check(spec_dir(tmp_path, "done", metrics))
    assert any("started_at" in problem and "%Y-%m-%dT%H:%M" in problem for problem in problems)


@pytest.mark.parametrize("value", ["two", "3.5", "-1"])
def test_check_rejects_a_non_integer_counter(tmp_path, value):
    metrics = dict(COMPLETE, plan_steps=value)
    problems = workflow_metrics.check(spec_dir(tmp_path, "done", metrics))
    assert any(
        "plan_steps" in problem and "is not a non-negative integer" in problem
        for problem in problems
    )


# An empty value is deliberately reported as a missing key rather than as a bad integer —
# there is nothing there to have measured. Pinned so the two branches cannot be confused.
def test_an_empty_counter_is_reported_as_missing(tmp_path):
    metrics = dict(COMPLETE, plan_steps="")
    problems = workflow_metrics.check(spec_dir(tmp_path, "done", metrics))
    assert any("missing" in problem and "plan_steps" in problem for problem in problems)


def test_check_reports_unbalanced_findings(tmp_path):
    metrics = dict(COMPLETE, findings_accepted="2")
    problems = workflow_metrics.check(spec_dir(tmp_path, "done", metrics))
    balance = [problem for problem in problems if "findings_accepted" in problem]
    assert balance and "= 3" in balance[0] and "= 4" in balance[0]


def test_the_balance_needs_all_five_counters(tmp_path):
    metrics = {key: value for key, value in COMPLETE.items() if key != "final_review_nits"}
    problems = workflow_metrics.check(spec_dir(tmp_path, "implemented", metrics))
    assert not any("do not match" in problem for problem in problems)


@pytest.mark.parametrize(
    "status, due",
    [
        ("plan-draft", ["started_at", "escalations", "plan_steps"]),
        (
            "plan-approved",
            ["plan_review_blockers", "plan_review_majors", "plan_changes"],
        ),
        ("implemented", ["implement_steps", "implement_iterations"]),
        ("done", ["finished_at", "findings_accepted", "final_review_nits"]),
    ],
)
def test_keys_due_per_status(tmp_path, status, due):
    assert set(due) <= set(workflow_metrics.REQUIRED[status])
    for key in due:
        metrics = {name: value for name, value in COMPLETE.items() if name != key}
        problems = workflow_metrics.check(spec_dir(tmp_path, status, metrics))
        assert any("missing" in problem and key in problem for problem in problems)


# AC9 says "exactly": an extra key in REQUIRED would hand every consumer a false
# escalation, so the whole table is asserted by equality, not by containment.
def test_the_required_table_is_exactly_ac9():
    assert workflow_metrics.REQUIRED == {
        "spec-draft": [],
        "spec-ready": [],
        "plan-draft": ["started_at", "escalations", "plan_steps"],
        "plan-approved": [
            "started_at",
            "escalations",
            "plan_steps",
            "plan_review_blockers",
            "plan_review_majors",
            "plan_changes",
        ],
        "implemented": [
            "started_at",
            "escalations",
            "plan_steps",
            "plan_review_blockers",
            "plan_review_majors",
            "plan_changes",
            "implement_steps",
            "implement_iterations",
        ],
        "done": ["started_at", "finished_at", *workflow_metrics.REQUIRED_DONE_COUNTERS],
    }


# SPEC 011 keeps the old thirteen counters due at `done`, less `deviations`, which moved to
# the either-or rule; none of the new keys is ever required (SPEC 010: a new required key
# turns specs in progress red).
def test_the_done_counters_are_the_old_ones_without_deviations():
    assert workflow_metrics.REQUIRED_DONE_COUNTERS == [
        "plan_steps",
        "plan_review_blockers",
        "plan_review_majors",
        "plan_changes",
        "implement_steps",
        "implement_iterations",
        "escalations",
        "final_review_blockers",
        "final_review_worth_fixing",
        "final_review_nits",
        "findings_accepted",
        "findings_rejected",
    ]


@pytest.mark.parametrize("status", ["spec-draft", "spec-ready"])
def test_early_statuses_require_nothing(tmp_path, status):
    assert workflow_metrics.check(spec_dir(tmp_path, status, {})) == []


def test_missing_keys_are_named_with_the_status(tmp_path):
    metrics = {"started_at": "2026-09-15T09:00", "plan_steps": "3"}
    result = run_check(spec_dir(tmp_path, "plan-draft", metrics))
    assert result.returncode == 1
    assert result.stdout == ""
    assert "escalations" in result.stderr
    assert "plan-draft" in result.stderr
    assert "Traceback" not in result.stderr


# AC10 says "every missing key", so more than one has to be missing here — with a single
# one the message passes whether it joins the list or prints only the first entry.
def test_every_missing_key_is_named(tmp_path):
    result = run_check(spec_dir(tmp_path, "done", {"started_at": '"2026-09-15T09:00"'}))
    assert result.returncode == 1
    missing = [line for line in result.stderr.splitlines() if "missing" in line]
    assert len(missing) == 1
    for key in ["finished_at", *workflow_metrics.REQUIRED_DONE_COUNTERS]:
        assert key in missing[0], key


def test_a_directory_without_a_readable_spec_fails_cleanly(tmp_path):
    empty = tmp_path / "015-empty"
    empty.mkdir()
    missing = run_check(empty)
    assert missing.returncode == 1
    assert "no SPEC.md" in missing.stderr
    assert "Traceback" not in missing.stderr

    bare = tmp_path / "016-bare"
    bare.mkdir()
    (bare / "SPEC.md").write_text("# SPEC 016 — no frontmatter\n")
    result = run_check(bare)
    assert result.returncode == 1
    assert "no frontmatter" in result.stderr
    assert "Traceback" not in result.stderr


def test_check_without_a_directory_is_a_usage_error():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "usage" in result.stderr


def test_an_unknown_status_is_reported(tmp_path):
    problems = workflow_metrics.check(spec_dir(tmp_path, "shipped", COMPLETE))
    assert problems == [f'{tmp_path / "014-e2e" / "SPEC.md"}: unknown status "shipped"']


def test_frontmatter_without_a_status_says_so(tmp_path):
    directory = tmp_path / "017-no-status"
    directory.mkdir()
    (directory / "SPEC.md").write_text("---\nmetrics:\n  escalations: 0\n---\n\n# SPEC 017\n")
    result = run_check(directory)
    assert result.returncode == 1
    assert "has no `status` key" in result.stderr
    assert "has no frontmatter" not in result.stderr
    assert "Traceback" not in result.stderr


# A typo in a metric key used to drop the value without a word; at `implemented` nothing
# else would have caught it.
def test_a_key_that_is_not_a_metric_is_reported(tmp_path):
    metrics = dict(COMPLETE, final_review_nit="3")
    problems = workflow_metrics.check(spec_dir(tmp_path, "implemented", metrics))
    assert any(
        "keys that are not metrics" in problem and "final_review_nit" in problem
        for problem in problems
    )


def test_a_missing_specs_directory_is_not_an_empty_report(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "typo")], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "is not a directory" in result.stderr
    assert "No spec carries a metrics block yet." not in result.stdout


@pytest.mark.skipif(sys.platform == "win32", reason="chmod does not deny reads on Windows")
def test_an_unreadable_spec_is_skipped_by_the_report_and_named_by_the_check(tmp_path):
    specs = write_specs(tmp_path / "specs")
    unreadable = specs / "013-legacy" / "SPEC.md"
    unreadable.chmod(0o000)
    try:
        if unreadable.is_file() and _readable(unreadable):
            pytest.skip("running as a user that ignores file permissions")
        report = subprocess.run(
            [sys.executable, str(SCRIPT), str(specs)], capture_output=True, text=True
        )
        assert report.returncode == 0
        assert "| 014-e2e |" in report.stdout
        assert "cannot be read, skipped" in report.stderr
        assert "Traceback" not in report.stderr

        result = run_check(specs / "013-legacy")
        assert result.returncode == 1
        assert "cannot be read" in result.stderr
        assert "Traceback" not in result.stderr
    finally:
        unreadable.chmod(0o644)


def _readable(path: Path) -> bool:
    try:
        path.read_text()
    except OSError:
        return False
    return True


NEW_KEYS = [
    "converge_gaps",
    "deviations_minor",
    "deviations_major",
    "cost_plan_cents",
    "cost_plan_review_cents",
    "cost_implement_cents",
    "cost_final_review_cents",
    "implement_chunks",
]
STATUSES = ["spec-draft", "spec-ready", "plan-draft", "plan-approved", "implemented", "done"]


# SPEC 011, AC9: the new keys are known integer counters and never required.
def test_new_counters_are_known_and_never_required(tmp_path):
    for key in NEW_KEYS:
        assert key in workflow_metrics.COUNTERS, key
        for status in STATUSES:
            assert key not in workflow_metrics.REQUIRED[status], (key, status)
    for status in STATUSES:
        metrics = dict(COMPLETE, **{key: "4" for key in NEW_KEYS})
        assert workflow_metrics.check(spec_dir(tmp_path, status, metrics)) == [], status
    for key in NEW_KEYS:
        metrics = dict(COMPLETE, **{key: "1.5"})
        problems = workflow_metrics.check(spec_dir(tmp_path, "done", metrics))
        assert any(
            key in problem and "is not a non-negative integer" in problem for problem in problems
        ), key


def without_deviations(**extra: str) -> dict[str, str]:
    metrics = {key: value for key, value in COMPLETE.items() if key != "deviations"}
    metrics.update(extra)
    return metrics


# SPEC 011, AC10: at `implemented` and `done` either the old key or both split keys pass.
@pytest.mark.parametrize("status", ["implemented", "done"])
@pytest.mark.parametrize(
    "form",
    [{"deviations": "1"}, {"deviations_minor": "1", "deviations_major": "0"}],
    ids=["old", "split"],
)
def test_either_deviations_form_satisfies_the_check(tmp_path, status, form):
    metrics = without_deviations(**form)
    assert workflow_metrics.check(spec_dir(tmp_path, status, metrics)) == []


@pytest.mark.parametrize("status", ["implemented", "done"])
@pytest.mark.parametrize(
    "form",
    [{}, {"deviations_minor": "1"}, {"deviations_major": "0"}],
    ids=["none", "minor", "major"],
)
def test_neither_deviations_form_names_both(tmp_path, status, form):
    problems = workflow_metrics.check(spec_dir(tmp_path, status, without_deviations(**form)))
    named = [problem for problem in problems if "deviations_minor" in problem]
    assert len(named) == 1, problems
    for key in ["`deviations`", "`deviations_minor`", "`deviations_major`"]:
        assert key in named[0], key
    assert "missing" not in named[0]


# SPEC 010's regression, guarded by AC9 and AC10: a spec in progress carries only the keys its
# status requires, and no deviations key before `implemented`. Widening DEVIATIONS_DUE to an
# earlier status would turn every such spec red.
@pytest.mark.parametrize("status", ["plan-draft", "plan-approved"])
def test_a_spec_in_progress_needs_no_deviations_key(tmp_path, status):
    metrics = {key: COMPLETE[key] for key in workflow_metrics.REQUIRED[status]}
    assert "deviations" not in metrics
    assert workflow_metrics.check(spec_dir(tmp_path, status, metrics)) == []


def costed(**extra: str) -> dict[str, str]:
    return dict(COMPLETE, **extra)


# SPEC 011, AC12. Three specs:
#   015-a: plan review 300 cents, findings 1 + 2 = 3; final review 500, findings 0 + 1 = 1;
#          all four costs (100 + 300 + 900 + 500 = 1800) and 5 plan steps.
#   016-b: plan review 101 cents, findings 2 + 0 = 2; no final-review cost, so no four costs.
#   017-c: no cost keys at all — neither numerator nor denominator.
# Plan review: (300 + 101) / (3 + 2) = 80.2 → 80. Final review: 500 / 1 = 500.
# Per plan step: 1800 / 5 = 360.
def test_report_shows_cost_per_finding_and_per_step(tmp_path):
    spec_dir(
        tmp_path,
        "done",
        costed(
            cost_plan_cents="100",
            cost_plan_review_cents="300",
            cost_implement_cents="900",
            cost_final_review_cents="500",
        ),
        name="015-a",
    )
    spec_dir(
        tmp_path,
        "done",
        costed(cost_plan_review_cents="101", plan_review_blockers="2", plan_review_majors="0"),
        name="016-b",
    )
    spec_dir(tmp_path, "done", costed(final_review_worth_fixing="9"), name="017-c")
    report = workflow_metrics.render(workflow_metrics.collect(tmp_path))
    assert "Plan review cost per significant finding: 80 cents (401/5)" in report
    assert "Final review cost per significant finding: 500 cents (500/1)" in report
    assert "Cost per plan step: 360 cents (1800/5)" in report


def test_the_cost_ratio_rounds_half_up(tmp_path):
    # 5 / 2 = 2.5 → 3, where round() would give the even 2.
    spec_dir(
        tmp_path,
        "done",
        costed(cost_plan_review_cents="5", plan_review_blockers="1", plan_review_majors="1"),
    )
    report = workflow_metrics.render(workflow_metrics.collect(tmp_path))
    assert "Plan review cost per significant finding: 3 cents (5/2)" in report


def test_cost_lines_are_hidden_without_data(tmp_path):
    spec_dir(tmp_path, "done", COMPLETE, name="015-a")
    report = workflow_metrics.render(workflow_metrics.collect(tmp_path))
    assert "cost per" not in report.lower()

    spec_dir(
        tmp_path,
        "done",
        costed(
            cost_plan_review_cents="40",
            plan_review_blockers="0",
            plan_review_majors="0",
            cost_final_review_cents="70",
            final_review_blockers="0",
            final_review_worth_fixing="0",
        ),
        name="015-a",
    )
    report = workflow_metrics.render(workflow_metrics.collect(tmp_path))
    assert "Plan review cost per significant finding" not in report
    assert "Final review cost per significant finding" not in report
    assert "Cost per plan step" not in report


def test_report_has_columns_for_the_new_keys(tmp_path):
    spec_dir(tmp_path, "done", costed(converge_gaps="2"), name="015-a")
    report = workflow_metrics.render(workflow_metrics.collect(tmp_path))
    header = report.splitlines()[0]
    cells = [cell.strip() for cell in header.strip("|").split("|")]
    for key in NEW_KEYS:
        assert key in cells, key
    row = next(line for line in report.splitlines() if line.startswith("| 015-a"))
    values = dict(zip(cells, [cell.strip() for cell in row.strip("|").split("|")], strict=True))
    assert values["converge_gaps"] == "2"
    assert values["cost_plan_cents"] == "-"
    assert values["deviations_minor"] == "-"


# SPEC 012, AC14: the chunk count is a report column, `-` where a spec ran in one context.
def test_implement_chunks_is_a_report_column(tmp_path):
    spec_dir(tmp_path, "done", dict(COMPLETE, implement_chunks="3"), name="015-a")
    spec_dir(tmp_path, "done", COMPLETE, name="016-b")
    report = workflow_metrics.render(workflow_metrics.collect(tmp_path))
    header = report.splitlines()[0]
    cells = [cell.strip() for cell in header.strip("|").split("|")]
    assert "implement_chunks" in cells
    values = {}
    for name in ("015-a", "016-b"):
        row = next(line for line in report.splitlines() if line.startswith(f"| {name}"))
        row_cells = [cell.strip() for cell in row.strip("|").split("|")]
        values[name] = dict(zip(cells, row_cells, strict=True))["implement_chunks"]
    assert values == {"015-a": "3", "016-b": "-"}
