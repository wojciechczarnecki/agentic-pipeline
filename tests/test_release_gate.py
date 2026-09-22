"""The repository's own pre-push hook: main is protected, and a minor or major release
tag needs a green eval receipt for the very commit being tagged.

These are repository rules, not plugin behaviour — the plugin stays project-independent,
so they cannot live in plugin/tests.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "git-hooks" / "pre-push"
RECEIPT = ROOT / "plugin" / "evals" / "last-run.json"
EVAL_RECEIPT = ROOT / "scripts" / "eval_receipt.py"
RESULT = ROOT / "tests" / "fixtures" / "eval-result.json"
SHA = "0" * 40


def push(ref: str, local_ref: str = "refs/heads/local") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(HOOK), "origin", "git@github.com:o/r.git"],
        input=f"{local_ref} {SHA} {ref} {SHA}\n",
        text=True,
        capture_output=True,
        cwd=ROOT,
    )


@pytest.fixture
def receipt():
    """Swap in a receipt and restore whatever was there, so a real one is never lost."""
    previous = RECEIPT.read_text() if RECEIPT.exists() else None

    total = len(list((ROOT / "plugin" / "evals").glob("*/case.yaml")))

    def write(fingerprint: str, green: bool, cases_total: int = None, model="default"):
        written = {
            "plugin_fingerprint": fingerprint,
            "green": green,
            "cases_total": total if cases_total is None else cases_total,
        }
        if model is not None:
            written["model"] = model
        RECEIPT.write_text(json.dumps(written) + "\n")

    yield write

    if previous is None:
        RECEIPT.unlink(missing_ok=True)
    else:
        RECEIPT.write_text(previous)


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/heads/master"])
def test_push_to_protected_branch_is_rejected(ref):
    assert push(ref).returncode == 1


def test_push_to_feature_branch_passes():
    assert push("refs/heads/feat/001-x").returncode == 0


# A patch is usually a hook or a documentation fix, and a full suite costs real money.
def test_a_patch_tag_needs_no_eval():
    assert push("refs/tags/pipeline--v0.3.1").returncode == 0


@pytest.mark.parametrize("tag", ["pipeline--v0.3.0", "pipeline--v1.0.0"])
def test_a_minor_or_major_tag_without_a_receipt_is_rejected(tag):
    result = push(f"refs/tags/{tag}")
    assert result.returncode == 1
    assert "scripts/eval.sh" in result.stderr


def fingerprint(ref: str = "HEAD") -> str:
    """What plugin/ contains at `ref` — the receipt's own measure, recomputed."""
    listing = subprocess.run(
        ["git", "ls-tree", "-r", ref, "--", "plugin/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout
    kept = "".join(
        line + "\n" for line in listing.splitlines() if "evals/last-run.json" not in line
    )
    return hashlib.sha256(kept.encode()).hexdigest()


# A sha would not survive the squash merge that lands the release, so the receipt
# fingerprints plugin/'s contents and the hook recomputes them at tag time.
def test_a_receipt_from_a_different_plugin_state_is_rejected(receipt):
    receipt("0" * 64, green=True)
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert "plugin/ changed since the eval ran" in result.stderr


def test_the_fingerprint_ignores_the_receipt_itself(receipt):
    """Otherwise writing the receipt would invalidate the receipt."""
    before = fingerprint()
    receipt("whatever", green=True)
    assert fingerprint() == before


def test_a_red_receipt_is_rejected(receipt):
    receipt(fingerprint(), green=False)
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert "not green" in result.stderr


def test_a_green_receipt_with_plugin_unchanged_passes(receipt):
    receipt(fingerprint(), green=True)
    assert push("refs/tags/pipeline--v0.3.0", local_ref="HEAD").returncode == 0


# `eval.sh --case X` writes a receipt too, and a single-case run is trivially green.
def test_a_receipt_covering_only_some_cases_is_rejected(receipt):
    receipt(fingerprint(), green=True, cases_total=1)
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert "run the whole suite" in result.stderr


# The gate runs on the model consumers work on; a cheaper --model is for drafting cases.
def test_a_model_override_receipt_is_rejected(receipt):
    receipt(fingerprint(), green=True, model="sonnet")
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert "--model sonnet" in result.stderr
    assert "default model" in result.stderr


def test_a_receipt_without_a_model_is_rejected(receipt):
    receipt(fingerprint(), green=True, model=None)
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert "does not record the model" in result.stderr


def write_receipt(tmp_path, *eval_args: str, env: dict | None = None):
    out = tmp_path / "receipt.json"
    environ = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_MODEL"}
    environ.update(env or {})
    result = subprocess.run(
        [
            sys.executable,
            str(EVAL_RECEIPT),
            "write",
            str(RESULT),
            str(out),
            "--commit",
            "c0ffee",
            "--version",
            "0.0.0",
            "--fingerprint",
            "f1",
            "--",
            *eval_args,
        ],
        capture_output=True,
        text=True,
        env=environ,
    )
    return result, json.loads(out.read_text())


# A case with several runs counts by majority; the fixture holds a case at 2 of 3, one at
# 1 of 3 and one at 1 of 1, as `claude plugin eval --json` reports them.
def test_two_of_three_runs_count_as_passed(tmp_path):
    _, written = write_receipt(tmp_path)
    assert written["cases"]["two-of-three"] == {"runs": 3, "passed": 2}
    assert written["cases"]["one-of-one"] == {"runs": 1, "passed": 1}
    assert written["cases_total"] == 3
    assert written["cases_passed"] == 2


def test_one_of_three_runs_counts_as_failed(tmp_path):
    result, written = write_receipt(tmp_path)
    assert written["cases"]["one-of-three"] == {"runs": 3, "passed": 1}
    assert written["green"] is False
    assert result.returncode == 1
    assert "NOT green" in result.stdout


def test_receipt_ignores_the_cli_aggregate(tmp_path):
    """Under the CLI's default threshold a 2-of-3 case scores below 1.0 and fails."""
    assert json.loads(RESULT.read_text())["aggregates"]["casesPassed"] == 1
    _, written = write_receipt(tmp_path)
    assert written["cases_passed"] == 2


def test_a_green_result_writes_a_green_receipt(tmp_path):
    result_file = tmp_path / "green.json"
    data = json.loads(RESULT.read_text())
    data["cases"] = [case for case in data["cases"] if case["name"] != "one-of-three"]
    result_file.write_text(json.dumps(data))
    out = tmp_path / "receipt.json"
    result = subprocess.run(
        [sys.executable, str(EVAL_RECEIPT), "write", str(result_file), str(out)]
        + ["--commit", "c", "--version", "v", "--fingerprint", "f", "--"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    written = json.loads(out.read_text())
    assert written["green"] is True
    assert (written["commit"], written["plugin_version"], written["plugin_fingerprint"]) == (
        "c",
        "v",
        "f",
    )


def test_a_run_without_a_grader_verdict_counts_as_failed(tmp_path):
    result_file = tmp_path / "skipped.json"
    data = json.loads(RESULT.read_text())
    run = data["cases"][2]["arms"]["with"][0]
    run["skippedPaidGraders"] = True
    result_file.write_text(json.dumps(data))
    out = tmp_path / "receipt.json"
    subprocess.run(
        [sys.executable, str(EVAL_RECEIPT), "write", str(result_file), str(out)]
        + ["--commit", "c", "--version", "v", "--fingerprint", "f", "--"],
        capture_output=True,
        text=True,
    )
    assert json.loads(out.read_text())["cases"]["one-of-one"] == {"runs": 1, "passed": 0}


def test_receipt_records_the_model(tmp_path):
    assert write_receipt(tmp_path)[1]["model"] == "default"
    assert write_receipt(tmp_path, "--model", "sonnet")[1]["model"] == "sonnet"
    assert write_receipt(tmp_path, "--case", "x", "--model=sonnet")[1]["model"] == "sonnet"


def test_an_environment_model_counts_as_an_override(tmp_path):
    _, written = write_receipt(tmp_path, env={"ANTHROPIC_MODEL": "sonnet"})
    assert written["model"] == "sonnet"


def test_summary_prints_one_line_per_case():
    result = subprocess.run(
        [sys.executable, str(EVAL_RECEIPT), "summary", str(RESULT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines[:3] == ["two-of-three 2/3", "one-of-three 1/3", "one-of-one 1/1"]
    assert lines[3].startswith("cost ")


def test_a_model_override_named_in_the_result_counts_too(tmp_path):
    """A receipt must not say `default` for a run the CLI itself reports as overridden."""
    result_file = tmp_path / "override.json"
    data = json.loads(RESULT.read_text())
    data["suite"]["modelOverride"] = "haiku"
    result_file.write_text(json.dumps(data))
    out = tmp_path / "receipt.json"
    subprocess.run(
        [sys.executable, str(EVAL_RECEIPT), "write", str(result_file), str(out)]
        + ["--commit", "c", "--version", "v", "--fingerprint", "f", "--"],
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_MODEL"},
    )
    assert json.loads(out.read_text())["model"] == "haiku"
