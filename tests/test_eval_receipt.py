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
        'API Error: 429 {"type":"error","error":{"type":"rate_limit_error"}}',
        'API Error: 529 {"type":"error","error":{"type":"overloaded_error"}}',
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
    [
        "timeout after 600s",
        "exit 1: something unknown",
        "exit 1: took 500s",
        "exit 1: 5000 files",
        # a number or a word that only looks like an infrastructure error
        "exit 1: wrote 429 lines",
        "exit 1: test_rate_limit failed",
        "exit 1: test_usage_limit failed",
        "exit 1: overloaded",
        "exit 1: API Error: 400 bad request",
    ],
)
def test_other_errors_are_failures(message):
    assert eval_receipt.run_verdict(run(score=0, error=message)) == "fail"


# Only a grader that threw is an infrastructure error: a judge that read about a rate limit
# in the transcript and voted FAIL gave a verdict.
def test_a_judge_explanation_without_grader_threw_is_a_verdict():
    explanation = "judge votes: FAIL FAIL FAIL; the skill hit a rate limit and stopped"
    assert eval_receipt.run_verdict(run(score=0, explanation=explanation)) == "fail"


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
    # Already passed by majority, yet an error run keeps it from `pass`: re-runnable.
    assert verdict(passed=2, errors=1, runs=3) == "error"
    assert verdict(passed=1, errors=1, runs=3) == "error"  # the error could decide it
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


def evals_dir(tmp_path, runs: dict[str, int]) -> Path:
    """A throwaway `plugin/evals/` of case.yaml files, as the pre-push hook reads them."""
    root = tmp_path / "evals"
    for name, asked in runs.items():
        (root / name).mkdir(parents=True, exist_ok=True)
        (root / name / "case.yaml").write_text(f"name: {name}\nruns: {asked}\n")
    return root


def merged_write(tmp_path, suite, *raws, fingerprint="f1", eval_args=()):
    """Write onto the receipt already in tmp_path, with the suite named by `suite`."""
    root = evals_dir(tmp_path, suite)
    return write(
        tmp_path,
        *raws,
        receipt=tmp_path / "last-run.json",
        fingerprint=fingerprint,
        eval_args=eval_args,
        extra=["--evals-dir", str(root)],
    )


NAMES = [f"case-{index}" for index in range(12)]


# AC7: a run cut short by a session limit, then only the errored cases again.
def test_a_rerun_of_errored_cases_merges_into_a_green_receipt(tmp_path):
    suite = {name: 1 for name in NAMES}
    first = raw_result({name: [PASS if index < 9 else ERROR] for index, name in enumerate(NAMES)})
    done, written = merged_write(tmp_path, suite, first)
    assert done.returncode == 1
    assert written["green"] is False
    before = written["cases"]

    second = raw_result({name: [PASS] for name in NAMES[9:]}, costUsd=0.5)
    done, written = merged_write(tmp_path, suite, second)
    assert done.returncode == 0, done.stdout
    assert written["green"] is True
    assert written["cases_total"] == 12
    assert written["cases_passed"] == 12
    assert {name: written["cases"][name] for name in NAMES[:9]} == {
        name: before[name] for name in NAMES[:9]
    }
    assert written["cost_usd"] == 1.5


def test_a_merged_receipt_equals_a_single_full_run(tmp_path):
    suite = {name: 1 for name in NAMES}
    full = tmp_path / "full"
    full.mkdir()
    _, single = merged_write(full, suite, raw_result({name: [PASS] for name in NAMES}))
    split = tmp_path / "split"
    split.mkdir()
    merged_write(split, suite, raw_result({name: [PASS] for name in NAMES[:4]}))
    _, merged = merged_write(split, suite, raw_result({name: [PASS] for name in NAMES[4:]}))
    assert merged["cases"] == single["cases"]
    assert (merged["green"], merged["cases_total"]) == (single["green"], single["cases_total"])


# AC8: a failure is replaced only by the five-run measurement.
@pytest.mark.parametrize(
    ("again", "replaced"),
    [
        ([PASS], False),
        ([PASS] * 4 + [FAIL], False),
        ([PASS] * 5, True),
        ([PASS] * 4 + [ERROR], False),
    ],
)
def test_a_failed_case_needs_five_of_five(tmp_path, again, replaced):
    suite = {"a": 1, "b": 1}
    merged_write(tmp_path, suite, raw_result({"a": [PASS], "b": [FAIL]}))
    done, written = merged_write(tmp_path, suite, raw_result({"b": again}))
    if replaced:
        assert written["cases"]["b"]["verdict"] == "pass"
        assert written["green"] is True
    else:
        assert written["cases"]["b"] == {"runs": 1, "passed": 0, "errors": 0, "verdict": "fail"}
        assert written["green"] is False
        assert "five-run measurement policy" in done.stdout
        assert "kept b" in done.stdout


# AC8: a later failing run replaces a pass, or a real failure would leave a stale green.
def test_a_failing_run_replaces_a_pass(tmp_path):
    suite = {"a": 1}
    _, written = merged_write(tmp_path, suite, raw_result({"a": [PASS]}))
    assert written["green"] is True
    done, written = merged_write(tmp_path, suite, raw_result({"a": [FAIL]}))
    assert written["cases"]["a"]["verdict"] == "fail"
    assert written["green"] is False
    assert done.returncode == 1


# AC8 as amended by the owner: an infrastructure error says nothing about the plugin, so it
# does not cost an earlier pass; a real verdict still replaces it.
def test_an_error_run_does_not_replace_a_pass(tmp_path):
    suite = {"a": 1, "b": 1}
    merged_write(tmp_path, suite, raw_result({"a": [PASS], "b": [PASS]}))
    done, written = merged_write(tmp_path, suite, raw_result({"a": [ERROR], "b": [PASS]}))
    assert written["cases"]["a"] == {"runs": 1, "passed": 1, "errors": 0, "verdict": "pass"}
    assert written["green"] is True
    assert done.returncode == 0, done.stdout
    assert "kept a" in done.stdout
    assert "infrastructure error" in done.stdout
    # An error still replaces an error.
    merged_write(tmp_path, {"c": 3}, raw_result({"c": [ERROR] * 3}), fingerprint="f2")
    _, written = merged_write(
        tmp_path, {"c": 3}, raw_result({"c": [PASS, PASS, ERROR]}), fingerprint="f2"
    )
    assert written["cases"]["c"]["passed"] == 2


# AC8: a case missing from the receipt is added only by a run as long as case.yaml asks.
def test_a_short_run_does_not_add_a_missing_case(tmp_path):
    suite = {"a": 1, "b": 3}
    merged_write(tmp_path, suite, raw_result({"a": [PASS]}))
    done, written = merged_write(tmp_path, suite, raw_result({"b": [PASS]}))
    assert list(written["cases"]) == ["a"]
    assert written["green"] is False
    assert done.returncode == 1
    assert "kept b out" in done.stdout
    assert "missing: b" in done.stdout
    _, written = merged_write(tmp_path, suite, raw_result({"b": [PASS] * 3}))
    assert written["cases"]["b"]["verdict"] == "pass"
    assert written["green"] is True


def test_write_lists_the_missing_cases(tmp_path):
    done, written = merged_write(tmp_path, {"a": 1, "b": 1, "c": 1}, raw_result({"a": [PASS]}))
    assert written["green"] is False
    assert "missing: b, c" in done.stdout
    assert "bash scripts/eval.sh --rerun-errors" in done.stdout


def test_a_short_run_does_not_replace_a_case(tmp_path):
    suite = {"a": 3}
    merged_write(tmp_path, suite, raw_result({"a": [PASS, ERROR, ERROR]}))
    done, written = merged_write(tmp_path, suite, raw_result({"a": [PASS]}))
    assert written["cases"]["a"]["verdict"] == "error"
    assert written["cases"]["a"]["runs"] == 3
    assert "kept a" in done.stdout
    # A full run of the case replaces it.
    _, written = merged_write(tmp_path, suite, raw_result({"a": [PASS] * 3}))
    assert written["cases"]["a"]["verdict"] == "pass"
    assert written["green"] is True


# AC9: another plugin state or model is a new receipt with only its own cases.
@pytest.mark.parametrize(
    ("fingerprint", "eval_args"), [("other", ()), ("f1", ("--model", "sonnet"))]
)
def test_a_different_fingerprint_or_model_starts_a_new_receipt(tmp_path, fingerprint, eval_args):
    suite = {"a": 3, "b": 1}
    merged_write(tmp_path, suite, raw_result({"a": [PASS] * 3, "b": [PASS]}))
    done, written = merged_write(
        tmp_path, suite, raw_result({"a": [PASS]}), fingerprint=fingerprint, eval_args=eval_args
    )
    assert "started a new receipt" in done.stdout
    assert ("fingerprint" if fingerprint == "other" else "model") in done.stdout
    assert list(written["cases"]) == ["a"]
    # Even a case that ran fewer times than its case.yaml asks is written as it ran.
    assert written["cases"]["a"]["runs"] == 1
    assert written["cases_total"] == 1
    assert written["green"] is False  # the suite has a case the receipt lacks


def test_an_old_format_receipt_is_not_merged(tmp_path):
    old = {
        "plugin_fingerprint": "f1",
        "model": "default",
        "cases_total": 2,
        "green": True,
        "cases": {"a": {"runs": 1, "passed": 1}, "b": {"runs": 1, "passed": 1}},
    }
    (tmp_path / "last-run.json").write_text(json.dumps(old))
    done, written = merged_write(tmp_path, {"a": 1, "b": 1}, raw_result({"a": [PASS]}))
    assert list(written["cases"]) == ["a"]
    assert "started a new receipt" in done.stdout
    assert "old format" in done.stdout


def test_two_raw_files_in_one_write_both_land(tmp_path):
    done, written = merged_write(
        tmp_path,
        {"a": 1, "b": 1},
        raw_result({"a": [PASS]}),
        raw_result({"b": [PASS]}),
    )
    assert done.returncode == 0, done.stdout
    assert sorted(written["cases"]) == ["a", "b"]
    assert written["cost_usd"] == 2.0


def test_a_partial_input_is_not_green(tmp_path):
    done, written = merged_write(tmp_path, {"a": 1}, raw_result({"a": [PASS]}, partial=True))
    assert written["green"] is False
    assert done.returncode == 1
    # A later complete merge clears it.
    _, written = merged_write(tmp_path, {"a": 1}, raw_result({"a": [PASS]}))
    assert written["green"] is True


def test_a_receipt_case_outside_the_suite_is_not_green(tmp_path):
    _, written = merged_write(tmp_path, {"a": 1}, raw_result({"a": [PASS], "gone": [PASS]}))
    assert written["green"] is False


def rerun(tmp_path, receipt: dict | None, *, fingerprint="f1", eval_args=(), env=None, suite=None):
    root = evals_dir(tmp_path, suite or {"ok": 1, "bad": 1, "limited": 1, "new": 1})
    path = tmp_path / "last-run.json"
    if receipt is not None:
        path.write_text(json.dumps(receipt))
    environ = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_MODEL"}
    environ.update(env or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), "rerun", str(path)]
        + ["--fingerprint", fingerprint, "--evals-dir", str(root), "--", *eval_args],
        capture_output=True,
        text=True,
        env=environ,
    )


def entry(verdict: str) -> dict:
    return {
        "runs": 1,
        "passed": int(verdict == "pass"),
        "errors": int(verdict == "error"),
        "verdict": verdict,
    }


def stored(**cases: str) -> dict:
    return {
        "plugin_fingerprint": "f1",
        "model": "default",
        "cases": {name: entry(verdict) for name, verdict in cases.items()},
    }


# AC11: errored and missing cases run again; a failed one is not retried.
def test_rerun_selects_errored_and_missing_cases(tmp_path):
    done = rerun(tmp_path, stored(ok="pass", bad="fail", limited="error"))
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == ["limited", "new"]


@pytest.mark.parametrize(
    ("kwargs", "words"),
    [
        ({"fingerprint": "other"}, "fingerprint"),
        ({"eval_args": ("--model", "sonnet")}, "model"),
        ({"env": {"ANTHROPIC_MODEL": "sonnet"}}, "model"),
    ],
)
def test_rerun_refuses_a_different_fingerprint_or_model(tmp_path, kwargs, words):
    done = rerun(tmp_path, stored(ok="pass", limited="error"), **kwargs)
    assert done.returncode == 1
    assert done.stdout == ""
    assert words in done.stderr


def test_rerun_refuses_without_a_receipt_or_with_an_old_one(tmp_path):
    done = rerun(tmp_path, None)
    assert (done.returncode, done.stdout) == (1, "")
    assert "bash scripts/eval.sh" in done.stderr
    old = {"plugin_fingerprint": "f1", "model": "default", "cases": {"ok": {"runs": 1}}}
    done = rerun(tmp_path, old)
    assert (done.returncode, done.stdout) == (1, "")
    assert "bash scripts/eval.sh" in done.stderr


def test_rerun_has_nothing_to_rerun(tmp_path):
    done = rerun(
        tmp_path,
        stored(ok="pass", bad="fail", limited="pass", new="pass"),
    )
    assert done.returncode == 0
    assert done.stdout == ""
    assert "nothing to re-run" in done.stderr


# AC13: the mapping from a changed path to the cases that need to run.
SUITE = [
    "final-review-finds-planted-defect",
    "guard-blocks-main-push",
    "implement-escalates-on-failing-test",
    "implement-example-case",
    "init-keeps-manual-edits",
    "plan-review-escalates-on-dependency",
]


@pytest.mark.parametrize(
    ("path", "selected"),
    [
        # the case's own directory
        ("plugin/evals/init-keeps-manual-edits/case.yaml", ["init-keeps-manual-edits"]),
        ("plugin/evals/init-keeps-manual-edits/files/x.md", ["init-keeps-manual-edits"]),
        # a deleted case has nothing to run
        ("plugin/evals/gone/case.yaml", []),
        # a skill selects the cases with its prefix
        ("plugin/skills/init/SKILL.md", ["init-keeps-manual-edits"]),
        (
            "plugin/skills/implement/SKILL.md",
            ["implement-escalates-on-failing-test", "implement-example-case"],
        ),
        ("plugin/skills/final-review/SKILL.md", ["final-review-finds-planted-defect"]),
        # `plan-review-` must not be picked by the `plan` skill (it has no case of its own)
        ("plugin/skills/plan-review/SKILL.md", ["plan-review-escalates-on-dependency"]),
        ("plugin/skills/plan/SKILL.md", []),
        # the stage agents
        (
            "plugin/agents/implementer.md",
            ["implement-escalates-on-failing-test", "implement-example-case"],
        ),
        ("plugin/agents/reviewer.md", ["final-review-finds-planted-defect"]),
        ("plugin/agents/plan-reviewer.md", ["plan-review-escalates-on-dependency"]),
        ("plugin/agents/planner.md", []),
        # the hooks
        ("plugin/hooks/hooks.json", ["guard-blocks-main-push"]),
        ("plugin/hooks/guard.py", ["guard-blocks-main-push"]),
        # anything else under plugin/ selects every case
        ("plugin/bin/workflow_metrics.py", SUITE),
        ("plugin/templates/PLAN.en.md", SUITE),
        ("plugin/.claude-plugin/plugin.json", SUITE),
        ("plugin/evals/.gitignore", SUITE),
        ("plugin/something-new/file", SUITE),
        # documents, tests and the receipt select none
        ("plugin/README.md", []),
        ("plugin/CHANGELOG.md", []),
        ("plugin/docs/INSTALL.md", []),
        ("plugin/tests/test_x.py", []),
        ("plugin/evals/last-run.json", []),
        ("plugin/skills/idea/SKILL.md", []),
        ("plugin/skills/ship/SKILL.md", []),
    ],
)
def test_changed_paths_map_to_cases(path, selected):
    assert sorted(eval_receipt.cases_for_paths([path], SUITE)) == sorted(selected)


def test_changed_paths_are_a_union():
    paths = ["plugin/hooks/hooks.json", "plugin/skills/init/SKILL.md", "plugin/README.md"]
    assert eval_receipt.cases_for_paths(paths, SUITE) == {
        "guard-blocks-main-push",
        "init-keeps-manual-edits",
    }


def test_changed_subcommand_reads_paths_from_stdin(tmp_path):
    root = evals_dir(tmp_path, {name: 1 for name in SUITE})
    done = subprocess.run(
        [sys.executable, str(SCRIPT), "changed", "--evals-dir", str(root)],
        input="plugin/hooks/hooks.json\nplugin/README.md\n",
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.split() == ["guard-blocks-main-push"]


# AC14: a case is reachable through a rule other than "everything" and its own directory.
# The candidate paths come from the real plugin tree, never from the case name, or a new
# case with an unknown prefix would be matched by a path built to fit it.
def reachable(cases: list[str]) -> set[str]:
    plugin = ROOT / "plugin"
    candidates = [f"plugin/skills/{d.name}/SKILL.md" for d in sorted((plugin / "skills").iterdir())]
    candidates += [
        f"plugin/agents/{name}.md" for name in ("implementer", "reviewer", "plan-reviewer")
    ]
    candidates.append("plugin/hooks/hooks.json")
    found = set()
    for path in candidates:
        selected = eval_receipt.cases_for_paths([path], cases)
        if selected != set(cases):
            found |= selected
    return found


def real_cases() -> list[str]:
    return sorted(eval_receipt.suite_cases(str(ROOT / "plugin" / "evals")))


def test_every_case_has_a_rule_of_its_own():
    cases = real_cases()
    assert cases
    assert set(cases) - reachable(cases) == set()


def test_a_case_with_an_unknown_prefix_fails_the_rule_check():
    cases = [*real_cases(), "zzz-unknown"]
    assert set(cases) - reachable(cases) == {"zzz-unknown"}


# SPEC 014, AC1, AC2, AC4: the cases of the removed rituals are gone, and nothing maps to them.
REMOVED_CASES = (
    "implement-converge-finds-missing-ac",
    "implement-escalates-on-never-red-test",
    "implement-stops-at-group-boundary",
)


def test_no_rule_names_a_removed_case():
    for name in REMOVED_CASES:
        assert not (ROOT / "plugin" / "evals" / name).exists(), name
        assert name not in (ROOT / "scripts" / "eval_receipt.py").read_text(), name
        assert f'"{name}"' not in Path(__file__).read_text().split("REMOVED_CASES = (")[0], name
