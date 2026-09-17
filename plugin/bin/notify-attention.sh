#!/usr/bin/env bash
# Hook: desktop notification when the agent waits for the user (question or permission).
# Must never block the tool call — every path exits 0, and without a notification tool
# it falls back to the terminal bell.

title="Claude Code"
message="Agent waits for your reaction"

if command -v notify-send >/dev/null 2>&1; then
  notify-send -a "$title" "$title" "$message" 2>/dev/null
elif command -v osascript >/dev/null 2>&1; then
  osascript -e "display notification \"$message\" with title \"$title\"" 2>/dev/null
else
  printf '\a'
fi

exit 0
