#!/usr/bin/env bash
# PostToolUse hook (Edit|Write): formats the file the agent just edited, following the
# `format` map from .claude/workflow.json. Formats only — it must never block the edit,
# so every path exits 0, including a missing interpreter, a broken configuration and
# a formatter that fails. Only shell builtins run before the interpreter check.

python=$(command -v python3 2>/dev/null) || python=""
[ -n "$python" ] || python=$(command -v python 2>/dev/null) || python=""
[ -n "$python" ] || exit 0

dir=${0%/*}
case "$dir" in /*) ;; *) dir="$PWD/$dir" ;; esac

read_file_path='import json, sys
print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))'
file=$("$python" -c "$read_file_path" 2>/dev/null)
[ -n "$file" ] && [ -f "$file" ] || exit 0

root="${CLAUDE_PROJECT_DIR:-$PWD}"
cd "$root" 2>/dev/null || exit 0

formatter=$("$python" "$dir/workflow_config.py" --format-for "$file" 2>/dev/null)
[ -n "$formatter" ] || exit 0

sh -c "$formatter" >/dev/null 2>&1

exit 0
