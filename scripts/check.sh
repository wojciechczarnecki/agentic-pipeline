#!/usr/bin/env bash
# Single verification entrypoint — the feedback signal for the agent self-correction loop
# (`verify.command` in .claude/workflow.json) and a pre-PR sanity check.
# Usage: scripts/check.sh
set -u

root="$(cd "$(dirname "$0")/.." && pwd)"
failed=()

run() {
  local name="$1"
  shift
  echo "== $name"
  if ! "$@"; then
    failed+=("$name")
  fi
}

cd "$root" || exit 1

if command -v claude >/dev/null 2>&1; then
  run "validate: plugin" claude plugin validate --strict plugin/
  run "validate: marketplace" claude plugin validate --strict .
else
  echo "== validate: skipped (claude is not on PATH; CI runs it)"
fi

run "ruff" uv run ruff check .
run "black" uv run black --check --quiet .
run "pytest" uv run pytest -q -p no:cacheprovider plugin/tests

echo
if [ "${#failed[@]}" -gt 0 ]; then
  echo "FAILED: ${failed[*]}"
  exit 1
fi
echo "ALL GREEN"
