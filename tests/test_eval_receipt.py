"""The eval receipt tooling in scripts/eval_receipt.py: run verdicts, case verdicts, merging
and case selection. Repository tooling, so the tests live here and not in plugin/tests."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "eval_receipt.py"
SESSION_LIMIT = ROOT / "tests" / "fixtures" / "eval-result-session-limit.json"

_spec = importlib.util.spec_from_file_location("eval_receipt", SCRIPT)
eval_receipt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eval_receipt)


def run(score=1, error=None, skipped=False, explanation="judge votes: PASS PASS PASS") -> dict:
    return {
        "score": score,
        "error": error,
        "skippedPaidGraders": skipped,
        "graders": [{"name": "criteria", "explanation": explanation}],
    }


# AC1: every pattern of an infrastructure error has a test of its own.
@pytest.mark.parametrize(
    "message",
    [
        "exit 1: You've hit your session limit · resets 12:20pm (Europe/Warsaw)",
        "exit 1: usage limit reached",
        "exit 1: rate limit exceeded",
        "exit 1: Rate-Limit hit",
        "exit 1: HTTP 429 Too Many Requests",
        "exit 1: API is overloaded",
        "exit 1: HTTP 529",
        "exit 1: API Error: 500 internal",
        "exit 1: 503 Service Unavailable",
        "exit 1: 502 Bad Gateway",
    ],
)
def test_infrastructure_error_is_an_error(message):
    assert eval_receipt.run_verdict(run(score=0, error=message)) == "error"


# AC2: the run finished and only the judge gave no verdict.
def test_grader_threw_on_session_limit_is_an_error():
    result = json.loads(SESSION_LIMIT.read_text())
    verdicts = {
        case["name"]: eval_receipt.run_verdict(case["arms"]["with"][0]) for case in result["cases"]
    }
    assert verdicts == {
        "final-review-finds-planted-defect": "pass",
        "init-without-questions": "error",
        "init-writes-the-chosen-language": "error",
    }
    assert result["cases"][1]["arms"]["with"][0]["error"] is None


def test_a_grader_that_threw_for_another_reason_is_a_failure():
    threw = "grader threw: judge call failed: malformed output"
    assert eval_receipt.run_verdict(run(score=0, explanation=threw)) == "fail"


# AC3: no verdict is not a failure of the plugin.
def test_no_verdict_is_an_error():
    assert eval_receipt.run_verdict(run(score=0, skipped=True)) == "error"
    never_started = {"name": "x", "runsPerCase": 3, "arms": {"with": [run(), run()]}}
    assert eval_receipt.tally(never_started) == (2, 1, 3)


# AC4: anything else is the plugin's problem, and the gate refuses in doubt.
@pytest.mark.parametrize(
    "message",
    ["timeout after 600s", "exit 1: something unknown", "exit 1: took 500s", "exit 1: 5000 files"],
)
def test_other_errors_are_failures(message):
    assert eval_receipt.run_verdict(run(score=0, error=message)) == "fail"


def test_a_score_decides_a_run_without_errors():
    assert eval_receipt.run_verdict(run(score=1)) == "pass"
    assert eval_receipt.run_verdict(run(score=0)) == "fail"


LIMIT = "exit 1: You've hit your session limit · resets 12:20pm (Europe/Warsaw)"
PASS, FAIL, ERROR = run(1), run(0), run(0, error=LIMIT)


def raw_result(cases: dict[str, list[dict]], planned: int | None = None, **top) -> dict:
    """A raw `claude plugin eval --json` result from {case name: [its runs]}."""
    return {
        "schemaVersion": 1,
        "costUsd": 1.0,
        "partial": False,
        "suite": {"modelOverride": None},
        "cases": [
            {"name": name, "runsPerCase": planned or len(runs), "arms": {"with": runs}}
            for name, runs in cases.items()
        ],
        **top,
    }


def write(tmp_path, *raws: dict, receipt=None, fingerprint="f1", eval_args=(), extra=()):
    """Run `eval_receipt.py write` on raw results; returns (process, receipt dict)."""
    files = []
    for index, raw in enumerate(raws):
        files.append(tmp_path / f"raw{index}.json")
        files[-1].write_text(json.dumps(raw))
    out = receipt or tmp_path / "receipt.json"
    environ = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_MODEL"}
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "write", *map(str, files), str(out)]
        + ["--commit", "c0ffee", "--version", "1.0.0", "--fingerprint", fingerprint]
        + [*extra, "--", *eval_args],
        capture_output=True,
        text=True,
        env=environ,
    )
    return done, json.loads(out.read_text())


def test_a_case_with_errors_is_not_passed():
    verdict = eval_receipt.case_verdict
    assert verdict(passed=2, errors=1, runs=3) == "error"  # the error could decide it
    assert verdict(passed=3, errors=0, runs=3) == "pass"
    assert verdict(passed=1, errors=0, runs=3) == "fail"
    # Already failed by majority: a session limit on the last run cannot rescue the case
    # into a mere error.
    assert verdict(passed=0, errors=1, runs=3) == "fail"
    assert verdict(passed=0, errors=1, runs=1) == "error"


def test_receipt_keeps_a_verdict_per_case(tmp_path):
    raw = raw_result({"a": [PASS], "b": [FAIL], "c": [ERROR], "d": [PASS, PASS, FAIL]})
    done, written = write(tmp_path, raw)
    assert written["cases"] == {
        "a": {"runs": 1, "passed": 1, "errors": 0, "verdict": "pass"},
        "b": {"runs": 1, "passed": 0, "errors": 0, "verdict": "fail"},
        "c": {"runs": 1, "passed": 0, "errors": 1, "verdict": "error"},
        "d": {"runs": 3, "passed": 2, "errors": 0, "verdict": "pass"},
    }
    for key in ("cases_total", "green", "model", "plugin_fingerprint", "plugin_version", "commit"):
        assert key in written
    assert written["cases_total"] == 4
    assert written["cases_passed"] == 2
    assert done.returncode == 1


def test_an_errored_case_is_not_passed(tmp_path):
    done, written = write(tmp_path, raw_result({"a": [PASS], "b": [PASS, PASS, ERROR]}))
    assert written["cases"]["b"]["verdict"] == "error"
    assert written["green"] is False
    assert done.returncode == 1
    done, written = write(tmp_path, raw_result({"a": [PASS], "b": [PASS]}))
    assert written["green"] is True


def test_write_lists_errored_and_failed_cases(tmp_path):
    done, _ = write(tmp_path, raw_result({"a": [PASS], "b": [FAIL], "c": [ERROR]}))
    out = done.stdout
    assert "errored: c" in out
    assert "failed: b" in out
    assert "bash scripts/eval.sh --rerun-errors" in out
    assert "five-run measurement policy" in out


def summary(tmp_path, raw: dict) -> list[str]:
    raw_file = tmp_path / "summary.json"
    raw_file.write_text(json.dumps(raw))
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "summary", str(raw_file)], capture_output=True, text=True
    )
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


def test_summary_lists_errored_cases(tmp_path):
    lines = summary(tmp_path, raw_result({"a": [PASS], "b": [FAIL], "c": [PASS, ERROR, PASS]}))
    assert lines[:3] == ["a 1/1", "b 0/1", "c 2/3 (1 error)"]
    assert "errored: c" in lines
    assert "failed: b" in lines
    text = "\n".join(lines)
    assert "bash scripts/eval.sh --rerun-errors" in text
    assert "five-run measurement policy" in text
    assert lines[3].startswith("cost ")
