import subprocess
import sys
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[1] / "bin"
SCRIPT = BIN / "workflow_metrics.py"
SECTIONS = BIN.parent / "templates" / "sections.md"
CONSUMER_SPECS = sorted((Path(__file__).parent / "fixtures" / "consumer-specs").glob("*/SPEC.md"))

METRICS = """  started_at: 2026-10-05T09:00
  finished_at: 2026-10-05T12:00
  escalations: 0
  plan_steps: 3
  plan_review_blockers: 0
  plan_review_majors: 1
  plan_changes: 2
  implement_steps: 3
  implement_iterations: 1
  deviations_minor: 0
  deviations_major: 0
  final_review_blockers: 0
  final_review_worth_fixing: 1
  final_review_nits: 3
  findings_accepted: 3
  findings_rejected: 1
"""

SPEC_BODY = """
# SPEC 001 — lint

## Requirements and acceptance criteria

- [ ] AC1: first
- [ ] AC2: second
- [ ] AC3: third
"""

PLAN_BODY = """# PLAN 001 — lint

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 1 | `t1` |
| AC3 | 2 | `t3` |

## End-to-end verification

### Manual (performed by the owner)

- Open the page.
  Pass when: the page shows the heading.
- Press the button.

## Owner decisions
"""


def pass_literals() -> tuple[str, str]:
    for line in SECTIONS.read_text(encoding="utf-8").splitlines():
        if line.startswith("| `pass-condition`"):
            cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
            return cells[2], cells[3]
    raise AssertionError("no pass-condition row in the section map")


def make_spec(tmp_path: Path, status: str, plan: str | None = PLAN_BODY, spec: str = SPEC_BODY):
    directory = tmp_path / "001-lint"
    directory.mkdir(exist_ok=True)
    (directory / "SPEC.md").write_text(f"---\nstatus: {status}\nmetrics:\n{METRICS}---\n{spec}")
    plan_file = directory / "PLAN.md"
    if plan is None:
        plan_file.unlink(missing_ok=True)
    else:
        plan_file.write_text(plan)
    return directory


def run_check(directory: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(directory)], capture_output=True, text=True
    )


LINTED = ["plan-draft", "plan-approved", "implemented"]


@pytest.mark.parametrize("status", LINTED)
def test_an_ac_without_a_matrix_row_is_reported(tmp_path, status):
    result = run_check(make_spec(tmp_path, status))
    assert result.returncode == 1, result.stderr
    assert "AC2" in result.stderr
    assert "AC1" not in result.stderr and "AC3" not in result.stderr.replace("PLAN", "")


def test_a_shared_row_counts_for_every_ac_in_it(tmp_path):
    plan = PLAN_BODY.replace("| AC1 | 1 |", "| AC1, AC2 | 1 |")
    plan = plan.replace(
        "- Press the button.\n", "- Press the button.\n  Pass when: a toast appears.\n"
    )
    result = run_check(make_spec(tmp_path, "implemented", plan))
    assert result.returncode == 0, result.stderr


def test_every_missing_ac_is_named_in_one_report(tmp_path):
    plan = PLAN_BODY.replace("| AC1 | 1 | `t1` |\n", "")
    result = run_check(make_spec(tmp_path, "plan-approved", plan))
    assert result.returncode == 1
    assert "AC1" in result.stderr and "AC2" in result.stderr


def test_a_manual_item_without_a_pass_line_is_reported(tmp_path):
    result = run_check(
        make_spec(tmp_path, "implemented", PLAN_BODY.replace("| AC3 |", "| AC2, AC3 |"))
    )
    assert result.returncode == 1
    assert "Press the button" in result.stderr
    assert "Open the page" not in result.stderr


def test_the_polish_pass_literal_passes_in_a_polish_plan(tmp_path):
    polish, english = pass_literals()
    plan = PLAN_BODY.replace("| AC3 |", "| AC2, AC3 |")
    plan = plan.replace(
        "- Press the button.\n", f"- Press the button.\n  {polish} a toast appears.\n"
    )
    assert english in plan
    result = run_check(make_spec(tmp_path, "implemented", plan))
    assert result.returncode == 0, result.stderr


def test_a_manual_section_of_one_na_line_passes(tmp_path):
    plan = PLAN_BODY.split("- Open the page.")[0] + "n/a — nothing a person has to check.\n\n"
    plan = plan.replace("| AC3 |", "| AC2, AC3 |") + "## Owner decisions\n"
    result = run_check(make_spec(tmp_path, "implemented", plan))
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("status", ["spec-draft", "spec-ready", "done"])
def test_unlinted_statuses_pass(tmp_path, status):
    result = run_check(make_spec(tmp_path, status))
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("status", LINTED)
def test_no_plan_reports_every_ac(tmp_path, status):
    result = run_check(make_spec(tmp_path, status, plan=None))
    assert result.returncode == 1
    for ac in ("AC1", "AC2", "AC3"):
        assert ac in result.stderr


def test_a_spec_without_acs_has_nothing_to_report(tmp_path):
    result = run_check(make_spec(tmp_path, "plan-approved", plan=None, spec="\n# SPEC 001\n"))
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("path", CONSUMER_SPECS, ids=lambda p: p.parent.name)
def test_consumer_specs_pass_the_check(path):
    result = run_check(path.parent)
    assert result.returncode == 0, result.stderr


def test_there_are_nine_consumer_fixtures():
    assert len(CONSUMER_SPECS) == 9


def map_literals(key: str) -> tuple[str, str]:
    for line in SECTIONS.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"| `{key}` | PLAN"):
            cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
            return cells[2], cells[3]
    raise AssertionError(f"no {key} row in the section map")


GOOD_PLAN = PLAN_BODY.replace("| AC3 |", "| AC2, AC3 |").replace(
    "- Press the button.\n", "- Press the button.\n  Pass when: a toast appears.\n"
)


def test_the_good_plan_passes(tmp_path):
    result = run_check(make_spec(tmp_path, "implemented", GOOD_PLAN))
    assert result.returncode == 0, result.stderr


# Final review F10: AC10 is not AC1, and an AC named in another cell is not a row of its own.
def test_ac10_does_not_cover_ac1(tmp_path):
    spec = SPEC_BODY + "- [ ] AC10: tenth\n"
    plan = GOOD_PLAN.replace("| AC1 | 1 | `t1` |", "| AC10 | 1 | `t10` |")
    result = run_check(make_spec(tmp_path, "implemented", plan, spec))
    assert result.returncode == 1
    assert "AC1 has no row" in result.stderr


def test_an_ac_in_the_proving_test_cell_is_not_a_row(tmp_path):
    plan = GOOD_PLAN.replace("| AC1 | 1 | `t1` |", "| AC2 | 1 | covers AC1 too |")
    result = run_check(make_spec(tmp_path, "implemented", plan))
    assert result.returncode == 1
    assert "AC1 has no row" in result.stderr


# Final review F16: the message agrees in number and names the way out.
def test_the_lint_messages_name_the_way_out(tmp_path):
    result = run_check(make_spec(tmp_path, "implemented"))
    assert "AC2 has no row in the PLAN.md AC → steps matrix; add a row for each" in result.stderr
    assert "add a `Pass when:` line" in result.stderr


def test_a_polish_plan_without_a_pass_line_is_reported(tmp_path):
    plan = PLAN_BODY.replace("| AC3 |", "| AC2, AC3 |")
    for key in ("ac-matrix", "e2e-manual", "e2e"):
        polish, english = map_literals(key)
        plan = plan.replace(english + "\n", polish + "\n")
    polish_pass, english_pass = pass_literals()
    plan = plan.replace(english_pass, polish_pass)
    assert english_pass not in plan
    result = run_check(make_spec(tmp_path, "implemented", plan))
    assert result.returncode == 1, result.stderr
    assert "Press the button" in result.stderr
    assert "Open the page" not in result.stderr


# Final review F7: the template's bullets also hold the n/a line, numbered items are items, and
# prose without a pass line is a scenario without one.
def manual(tmp_path: Path, body: str) -> subprocess.CompletedProcess:
    plan = GOOD_PLAN.split("- Open the page.")[0] + body + "\n\n## Owner decisions\n"
    return run_check(make_spec(tmp_path, "implemented", plan))


def test_a_bulleted_na_line_passes(tmp_path):
    result = manual(tmp_path, "- n/a — nothing a person has to check.")
    assert result.returncode == 0, result.stderr


def test_a_numbered_item_without_a_pass_line_is_reported(tmp_path):
    result = manual(tmp_path, "1. Open the page.\n   Pass when: it loads.\n2. Press the button.")
    assert result.returncode == 1
    assert "Press the button" in result.stderr
    assert "Open the page" not in result.stderr


def test_prose_without_a_pass_line_is_reported(tmp_path):
    result = manual(tmp_path, "Open the page and press the button.")
    assert result.returncode == 1
    assert "Open the page and press the button" in result.stderr


def test_prose_with_a_pass_line_passes(tmp_path):
    result = manual(tmp_path, "Open the page and press the button.\nPass when: a toast appears.")
    assert result.returncode == 0, result.stderr
