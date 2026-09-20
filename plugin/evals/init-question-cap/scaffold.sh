#!/usr/bin/env bash
# Runs in the empty workspace before the agent starts. Stack detection is the whole point
# of this case: without pyproject.toml the detection fails and the grader would score the
# "second round allowed" exception instead of the question cap.
set -euo pipefail

cat > pyproject.toml <<'INNER'
[project]
name = "zbiorka"
version = "0.1.0"
requires-python = ">=3.12"
INNER
