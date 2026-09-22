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

    names = [path.parent.name for path in (ROOT / "plugin" / "evals").glob("*/case.yaml")]
    total = len(names)

    def write(
        fingerprint: str, green: bool, cases_total: int = None, model="default", runs: int = 3
    ):
        written = {
            "plugin_fingerprint": fingerprint,
            "green": green,
            "cases_total": total if cases_total is None else cases_total,
            "cases": {name: {"runs": runs, "passed": runs} for name in names},
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


def commit_with_runs(runs: int) -> str:
    """A throwaway commit of HEAD whose first case asks for `runs` — no ref, no checkout."""
    case = sorted((ROOT / "plugin" / "evals").glob("*/case.yaml"))[0]
    text = case.read_text().replace("runs: 1", f"runs: {runs}")

    def git(*args: str, **kwargs) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True, **kwargs
        ).stdout.strip()

    blob = git("hash-object", "-w", "--stdin", input=text)
    index = ROOT / ".git" / "test-release-gate.index"
    env = {**os.environ, "GIT_INDEX_FILE": str(index)}
    try:
        git("read-tree", "HEAD", env=env)
        path = case.relative_to(ROOT).as_posix()
        git("update-index", "--cacheinfo", f"100644,{blob},{path}", env=env)
        tree = git("write-tree", env=env)
    finally:
        index.unlink(missing_ok=True)
    return git("commit-tree", tree, "-p", "HEAD", "-m", "runs override test")


# `eval.sh --runs 1` would measure a `runs: 3` case once — the bypass `--model` is refused for.
def test_a_receipt_with_fewer_runs_than_case_yaml_is_rejected(receipt):
    tagged = commit_with_runs(3)
    receipt(fingerprint(tagged), green=True, runs=1)
    result = push("refs/tags/pipeline--v0.3.0", local_ref=tagged)
    assert result.returncode == 1
    assert "ran 1 of 3" in result.stderr
    assert "fewer runs than case.yaml" in result.stderr


def test_a_receipt_with_the_runs_case_yaml_asks_passes(receipt):
    tagged = commit_with_runs(3)
    receipt(fingerprint(tagged), green=True, runs=3)
    assert push("refs/tags/pipeline--v0.3.0", local_ref=tagged).returncode == 0


def test_a_receipt_missing_a_case_is_rejected(receipt):
    receipt(fingerprint(), green=True)
    written = json.loads(RECEIPT.read_text())
    missing = sorted(written["cases"])[0]
    del written["cases"][missing]
    RECEIPT.write_text(json.dumps(written))
    result = push("refs/tags/pipeline--v0.3.0", local_ref="HEAD")
    assert result.returncode == 1
    assert f"{missing} ran 0 of 1" in result.stderr


def write_result(tmp_path, data: dict) -> dict:
    result_file = tmp_path / "result.json"
    result_file.write_text(json.dumps(data))
    out = tmp_path / "receipt.json"
    subprocess.run(
        [sys.executable, str(EVAL_RECEIPT), "write", str(result_file), str(out)]
        + ["--commit", "c", "--version", "v", "--fingerprint", "f", "--"],
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "ANTHROPIC_MODEL"},
    )
    return json.loads(out.read_text())


def green_result() -> dict:
    data = json.loads(RESULT.read_text())
    data["cases"] = [case for case in data["cases"] if case["name"] != "one-of-three"]
    return data


# `--max-cost-usd` stops launching runs: one passing run of three must not read 1/1.
def test_runs_that_never_started_count_as_failed(tmp_path):
    data = green_result()
    two_of_three = data["cases"][0]
    assert two_of_three["runsPerCase"] == 3
    two_of_three["arms"]["with"] = [run for run in two_of_three["arms"]["with"] if run["passed"]][
        :1
    ]
    written = write_result(tmp_path, data)
    assert written["cases"]["two-of-three"] == {"runs": 3, "passed": 1}
    assert written["green"] is False


def test_a_partial_result_is_not_green(tmp_path):
    data = green_result()
    assert write_result(tmp_path, data)["green"] is True
    data["partial"] = True
    assert write_result(tmp_path, data)["green"] is False


STUB_CLAUDE = """#!/usr/bin/env bash
# Stands in for `claude plugin eval`: writes the canned result where --json points.
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--json" ]]; then cp "$STUB_RESULT" "$2"; shift; fi
  shift
done
"""


# `-- "$@"` is the only path by which `--model` reaches the receipt; run eval.sh itself,
# with stubs for the CLI and the sandbox backend, in a copy of the repository layout.
@pytest.mark.parametrize(("args", "model"), [((), "default"), (("--model", "sonnet"), "sonnet")])
def test_eval_sh_passes_the_model_to_the_receipt(tmp_path, args, model):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "plugin" / ".claude-plugin").mkdir(parents=True)
    (repo / "plugin" / "evals").mkdir()
    for name in ["eval.sh", "eval_receipt.py"]:
        (repo / "scripts" / name).write_text((ROOT / "scripts" / name).read_text())
    (repo / "plugin" / ".claude-plugin" / "plugin.json").write_text('{"version": "9.9.9"}')
    git_env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    for command in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", *command], cwd=repo, env=git_env, check=True)

    stubs = tmp_path / "bin"
    stubs.mkdir()
    for name, body in [("claude", STUB_CLAUDE), ("socat", "#!/bin/sh\n"), ("bwrap", "#!/bin/sh\n")]:
        (stubs / name).write_text(body)
        (stubs / name).chmod(0o755)
    result_file = tmp_path / "result.json"
    result_file.write_text(json.dumps(green_result()))
    env = {k: v for k, v in git_env.items() if k != "ANTHROPIC_MODEL"}
    env.update(PATH=f"{stubs}{os.pathsep}{os.environ['PATH']}", STUB_RESULT=str(result_file))

    run = subprocess.run(
        ["bash", str(repo / "scripts" / "eval.sh"), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    assert run.returncode == 0, run.stderr
    written = json.loads((repo / "plugin" / "evals" / "last-run.json").read_text())
    assert written["model"] == model
    assert written["plugin_version"] == "9.9.9"
