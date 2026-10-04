"""The eval receipt tooling in scripts/eval_receipt.py: run verdicts, case verdicts, merging
and case selection. Repository tooling, so the tests live here and not in plugin/tests."""

import importlib.util
import json
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
