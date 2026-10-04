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

# The receipt ships inside the release it certifies, so it cannot name its own commit —
# and a squash merge would invalidate any sha it did name. It records what plugin/ CONTAINS
# instead, which survives squashing, rebasing and a fresh clone.
plugin_fingerprint() {
  git ls-tree -r "$1" -- plugin/ | grep -v 'evals/last-run.json' | sha256sum | cut -d" " -f1
}

# `git diff` ignores untracked files, which are part of what runs yet absent from the
# fingerprint, so the check is `git status`. The receipt itself may be dirty: it is output.
[[ -z "$(git status --porcelain -- plugin/ ":(exclude)$receipt")" ]] || {
  echo "eval.sh: plugin/ has uncommitted or untracked files; commit them first so the" >&2
  echo "eval.sh: receipt can fingerprint what actually ran." >&2
  exit 1
}

# Two options are the script's own and never reach the CLI, which rejects unknown flags:
# --rerun-errors runs the cases the receipt records as an error or does not have yet, and
# --changed runs the cases a diff against origin/main touches (docs/CONVENTIONS.md).
rerun=0
changed=0
has_case=0
eval_args=()
for arg in "$@"; do
  case "$arg" in
    --rerun-errors) rerun=1 ;;
    --changed) changed=1 ;;
    --case | --case=*) has_case=1; eval_args+=("$arg") ;;
    *) eval_args+=("$arg") ;;
  esac
done

if (( rerun + changed + has_case > 1 )); then
  echo "eval.sh: --rerun-errors, --changed and --case each pick the cases to run and" >&2
  echo "eval.sh: cannot be combined." >&2
  exit 1
fi

# The receipt ships inside the release it certifies, so it records what plugin/ CONTAINS;
# a re-run is only merged into a receipt of the same plugin state.
fingerprint="$(plugin_fingerprint HEAD)"

# The cases to run, one `--case` call each: the CLI takes a single name glob. An empty
# list means the whole suite in one call.
cases=()
if (( rerun )); then
  selected="$(python3 scripts/eval_receipt.py rerun "$receipt" \
    --fingerprint "$fingerprint" --evals-dir plugin/evals -- "${eval_args[@]+"${eval_args[@]}"}")" || exit 1
  [[ -n "$selected" ]] || exit 0
  mapfile -t cases <<<"$selected"
elif (( changed )); then
  # The cases the branch touches, measured against where it left origin/main. A development
  # run only: the release receipt needs the whole suite, and pre-push refuses less.
  base="$(git merge-base HEAD origin/main 2>/dev/null)" || {
    echo "eval.sh: cannot find origin/main or the merge-base with it, so --changed has" >&2
    echo "eval.sh: nothing to compare against; run: git fetch origin" >&2
    exit 1
  }
  selected="$(git diff --name-only "$base" HEAD -- plugin/ |
    python3 scripts/eval_receipt.py changed --evals-dir plugin/evals)" || exit 1
  [[ -n "$selected" ]] || {
    echo "eval.sh: the changes since origin/main touch no eval case; nothing to run." >&2
    exit 0
  }
  mapfile -t cases <<<"$selected"
fi

rawdir="$(mktemp -d)"
trap 'rm -rf "$rawdir"' EXIT

# --allow-tools is not implied by --trust-plugin, and every case declares Bash.
# A red suite exits non-zero, and the receipt has to record that rather than vanish.
run_cli() {
  claude plugin eval plugin/ \
    --scaffold \
    --allow-tools Bash Write Edit \
    --trust-plugin \
    --no-publish \
    --ablation none \
    "$@"
}

raws=()
set +e
if (( ${#cases[@]} == 0 )); then
  run_cli --json "$rawdir/all.json" "${eval_args[@]+"${eval_args[@]}"}"
  raws+=("$rawdir/all.json")
else
  for index in "${!cases[@]}"; do
    run_cli --case "${cases[index]}" --json "$rawdir/$index.json" "${eval_args[@]+"${eval_args[@]}"}"
    if [[ -s "$rawdir/$index.json" ]]; then
      raws+=("$rawdir/$index.json")
    else
      echo "eval.sh: ${cases[index]} produced no result; it stays as the receipt had it." >&2
    fi
  done
fi
set -e

# A full run leaves one file; a selective run leaves the non-empty ones only.
existing=()
for file in "${raws[@]}"; do
  if [[ -s "$file" ]]; then existing+=("$file"); fi
done
(( ${#existing[@]} > 0 )) || { echo "eval.sh: the run produced no result file; nothing to record." >&2; exit 1; }

commit="$(git rev-parse HEAD)"
version="$(python3 -c 'import json;print(json.load(open("plugin/.claude-plugin/plugin.json"))["version"])')"

# A case with several runs counts by majority, a result merges into the receipt of the same
# plugin state and model, and the receipt records the model it ran on; all of it lives in a
# script so it is testable without a model.
python3 scripts/eval_receipt.py write "${existing[@]}" "$receipt" \
  --commit "$commit" --version "$version" --fingerprint "$fingerprint" \
  --evals-dir plugin/evals -- "${eval_args[@]+"${eval_args[@]}"}"
