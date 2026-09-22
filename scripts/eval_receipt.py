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
import sys


def run_passed(run: dict) -> bool:
    # A run whose paid grader was skipped (the cost ceiling hit) has no verdict, and a
    # run without a verdict is no evidence that the case passes.
    if run.get("skippedPaidGraders"):
        return False
    return (run.get("score") or 0) >= 1


def case_runs(result: dict) -> dict[str, tuple[int, int]]:
    counted = {}
    for case in result["cases"]:
        runs = case["arms"]["with"]
        counted[case["name"]] = (sum(run_passed(run) for run in runs), len(runs))
    return counted


# The CLI's own aggregate is not the verdict: under its default threshold a case that
# passed 2 of 3 runs scores below 1.0 and counts as failed.
def majority(passed: int, runs: int) -> bool:
    return 2 * passed > runs


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
    counted = case_runs(result)
    passed = sum(majority(*runs) for runs in counted.values())
    model = model_override(args, environ) or result.get("suite", {}).get("modelOverride")
    return {
        **recorded,
        "ran_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "cases_total": len(counted),
        "cases_passed": passed,
        "green": passed == len(counted) > 0,
        "cost_usd": round(result["costUsd"], 4),
        "model": model or "default",
        "cases": {name: {"runs": runs, "passed": ok} for name, (ok, runs) in counted.items()},
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
    return 0 if written["green"] else 1


def summary(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="eval_receipt.py summary")
    parser.add_argument("raw")
    options = parser.parse_args(argv)
    with open(options.raw) as handle:
        result = json.load(handle)
    for name, (passed, runs) in case_runs(result).items():
        print(f"{name} {passed}/{runs}")
    judged = judge_cost(result)
    print(
        f"cost {result['costUsd'] + judged:.4f} "
        f"(runs {result['costUsd']:.4f}, judge {judged:.4f}); "
        f"model {result.get('suite', {}).get('modelOverride') or 'default'}"
    )
    return 0


def main(argv: list[str]) -> int:
    commands = {"write": write, "summary": summary}
    if len(argv) < 2 or argv[1] not in commands:
        print("usage: eval_receipt.py write|summary …", file=sys.stderr)
        return 2
    return commands[argv[1]](argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
