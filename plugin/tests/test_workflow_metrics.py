import importlib.util
import subprocess
import sys
from pathlib import Path

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


def test_a_broken_config_is_reported(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "workflow.json").write_text('{"nope": 1}')
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=str(tmp_path), capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "unknown key `nope`" in result.stderr

