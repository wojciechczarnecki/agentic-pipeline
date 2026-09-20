#!/usr/bin/env bash
# Runs the plugin eval suite locally and writes a receipt the pre-push hook checks before
# a minor or major release tag. `claude plugin eval` costs real money and needs a sandbox
# backend, so this is never wired into CI (docs/DECISIONS.md, 2026-09-20).
set -euo pipefail

cd "$(dirname "$0")/.."

command -v socat >/dev/null && command -v bwrap >/dev/null || {
  echo "eval.sh: the sandbox backend is missing; a granted shell tool is refused without it." >&2
  echo "eval.sh: install it with: sudo apt-get install -y bubblewrap socat" >&2
  exit 1
}

receipt="plugin/evals/last-run.json"
raw="$(mktemp --suffix=.json)"
trap 'rm -f "$raw"' EXIT

# --allow-tools is not implied by --trust-plugin, and every case declares Bash.
# A red suite exits non-zero, and the receipt has to record that rather than vanish.
set +e
claude plugin eval plugin/ \
  --scaffold \
  --allow-tools Bash Write Edit \
  --trust-plugin \
  --no-publish \
  --ablation none \
  --json "$raw" "$@"
set -e

[[ -s "$raw" ]] || { echo "eval.sh: the run produced no result file; nothing to record." >&2; exit 1; }

commit="$(git rev-parse HEAD)"
version="$(python3 -c 'import json;print(json.load(open("plugin/.claude-plugin/plugin.json"))["version"])')"

python3 - "$raw" "$receipt" "$commit" "$version" <<'PY'
import json, sys, datetime

raw, receipt, commit, version = sys.argv[1:5]
result = json.load(open(raw))
agg = result["aggregates"]
passed = agg["casesPassed"] == agg["casesTotal"] and agg["casesTotal"] > 0

json.dump(
    {
        "commit": commit,
        "plugin_version": version,
        "ran_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "cases_total": agg["casesTotal"],
        "cases_passed": agg["casesPassed"],
        "green": passed,
        "cost_usd": round(result["costUsd"], 4),
    },
    open(receipt, "w"),
    indent=2,
)
open(receipt, "a").write("\n")
print(f"\neval.sh: receipt written to {receipt} ({'green' if passed else 'NOT green'})")
sys.exit(0 if passed else 1)
PY
