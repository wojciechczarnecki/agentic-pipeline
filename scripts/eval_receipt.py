#!/usr/bin/env python3
# Turns a `claude plugin eval --json` result into the release receipt the pre-push hook
# checks, and summarises a result per case. Repository tooling, not plugin runtime.
# Usage: eval_receipt.py write <raw.json> <receipt.json> --commit C --version V
#                              --fingerprint F -- <arguments eval.sh passed to the CLI>
#        eval_receipt.py summary <raw.json>
# Exit codes: write — 0 when the receipt is green, 1 when it is not; summary — 0.
import argparse
import datetime
import json
import os
import re
import sys

# Messages that say the infrastructure failed, not the plugin: the account's session or
# usage limit, a rate limit, an overloaded API and an API 5xx. A bare 5xx number is not
# matched, so a duration such as `timeout after 500s` stays a failure.
INFRA_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"session limit|usage limit",
        r"rate.?limit|\b429\b",
        r"overloaded|\b529\b",
        r"api error:?\s*5\d\d"
        r"|\b5\d\d\b.{0,3}(internal server error|bad gateway|service unavailable|gateway timeout)",
    )
]


def is_infrastructure(message: str) -> bool:
    return any(pattern.search(message) for pattern in INFRA_PATTERNS)


def run_verdict(run: dict) -> str:
    """`pass`, `fail` or `error`. An error is a known infrastructure failure or a run without
    a verdict; anything else that is not a pass is a failure, so the gate refuses in doubt."""
    error = run.get("error")
    if error:
        return "error" if is_infrastructure(error) else "fail"
    # A run whose paid grader was skipped (the cost ceiling hit) has no verdict.
    if run.get("skippedPaidGraders"):
        return "error"
    for grader in run.get("graders") or []:
        explanation = grader.get("explanation") or ""
        if explanation.startswith("grader threw:") and is_infrastructure(explanation):
            return "error"
    return "pass" if (run.get("score") or 0) >= 1 else "fail"


# `--max-cost-usd` stops launching runs, so a case can report fewer runs than it asked
# for; a run that never started has no verdict, so it counts as an error.
def tally(case: dict) -> tuple[int, int, int]:
    """(passed, errors, planned runs) of one case."""
    runs = case["arms"]["with"]
    planned = max(len(runs), case.get("runsPerCase") or 0)
    verdicts = [run_verdict(run) for run in runs]
    errors = verdicts.count("error") + planned - len(runs)
    return verdicts.count("pass"), errors, planned


# The CLI's own aggregate is not the verdict: under its default threshold a case that
# passed 2 of 3 runs scores below 1.0 and counts as failed.
def majority(passed: int, runs: int) -> bool:
    return 2 * passed > runs


def case_verdict(passed: int, errors: int, runs: int) -> str:
    """A case with an error run is never `pass`. It is `error` (re-runnable) when the errors
    could have changed the outcome, and `fail` when it had already failed by majority."""
    if errors == 0:
        return "pass" if majority(passed, runs) else "fail"
    return "error" if majority(passed + errors, runs) else "fail"


def case_entries(result: dict) -> dict[str, dict]:
    entries = {}
    for case in result["cases"]:
        passed, errors, planned = tally(case)
        entries[case["name"]] = {
            "runs": planned,
            "passed": passed,
            "errors": errors,
            "verdict": case_verdict(passed, errors, planned),
        }
    return entries


def problem_lines(entries: dict[str, dict]) -> list[str]:
    """The errored and the failed cases, apart: an error is re-run, a failure is not."""
    lines = []
    errored = [name for name, entry in entries.items() if entry["verdict"] == "error"]
    failed = [name for name, entry in entries.items() if entry["verdict"] == "fail"]
    if errored:
        lines += [
            f"errored: {', '.join(errored)}",
            "  infrastructure errors, not failures; re-run only these: "
            "bash scripts/eval.sh --rerun-errors",
        ]
    if failed:
        lines += [
            f"failed: {', '.join(failed)}",
            "  a failed case is not retried until it passes: the five-run measurement "
            "policy applies (docs/CONVENTIONS.md)",
        ]
    return lines


def model_override(args: list[str], environ: dict[str, str]) -> str | None:
    for index, arg in enumerate(args):
        if arg == "--model" and index + 1 < len(args):
            return args[index + 1]
        if arg.startswith("--model="):
            return arg.split("=", 1)[1]
    # The environment changes the model without a flag, so it is an override too.
    return environ.get("ANTHROPIC_MODEL") or None


def judge_cost(result: dict) -> float:
    return sum(
        run.get("judgeCostUsd") or 0 for case in result["cases"] for run in case["arms"]["with"]
    )


def receipt(result: dict, args: list[str], environ: dict[str, str], **recorded) -> dict:
    entries = case_entries(result)
    passed = sum(entry["verdict"] == "pass" for entry in entries.values())
    model = model_override(args, environ) or result.get("suite", {}).get("modelOverride")
    return {
        **recorded,
        "ran_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "cases_total": len(entries),
        "cases_passed": passed,
        # A partial result (the cost ceiling or an abort cut the suite short) is no release.
        "green": passed == len(entries) > 0 and not result.get("partial"),
        "cost_usd": round(result["costUsd"], 4),
        "model": model or "default",
        "cases": entries,
    }


def write(argv: list[str]) -> int:
    own, eval_args = argv, []
    if "--" in argv:
        split = argv.index("--")
        own, eval_args = argv[:split], argv[split + 1 :]
    parser = argparse.ArgumentParser(prog="eval_receipt.py write")
    parser.add_argument("raw")
    parser.add_argument("receipt")
    parser.add_argument("--commit", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--fingerprint", required=True)
    options = parser.parse_args(own)

    with open(options.raw) as handle:
        result = json.load(handle)
    written = receipt(
        result,
        eval_args,
        dict(os.environ),
        commit=options.commit,
        plugin_fingerprint=options.fingerprint,
        plugin_version=options.version,
    )
    with open(options.receipt, "w") as handle:
        json.dump(written, handle, indent=2)
        handle.write("\n")
    verdict = "green" if written["green"] else "NOT green"
    print(f"\neval.sh: receipt written to {options.receipt} ({verdict})")
    for line in problem_lines(written["cases"]):
        print(line)
    return 0 if written["green"] else 1


def summary(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="eval_receipt.py summary")
    parser.add_argument("raw")
    options = parser.parse_args(argv)
    with open(options.raw) as handle:
        result = json.load(handle)
    entries = case_entries(result)
    for name, entry in entries.items():
        errors = f" ({entry['errors']} error)" if entry["errors"] else ""
        print(f"{name} {entry['passed']}/{entry['runs']}{errors}")
    judged = judge_cost(result)
    print(
        f"cost {result['costUsd'] + judged:.4f} "
        f"(runs {result['costUsd']:.4f}, judge {judged:.4f}); "
        f"model {result.get('suite', {}).get('modelOverride') or 'default'}"
    )
    for line in problem_lines(entries):
        print(line)
    return 0


def main(argv: list[str]) -> int:
    commands = {"write": write, "summary": summary}
    if len(argv) < 2 or argv[1] not in commands:
        print("usage: eval_receipt.py write|summary …", file=sys.stderr)
        return 2
    return commands[argv[1]](argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
