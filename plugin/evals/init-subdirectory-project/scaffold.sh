#!/usr/bin/env bash
# The case measures how /pipeline:init spells a project that lives in a subdirectory: the
# fixture has a Python manifest in `backend/` that declares its dev tools and no test file,
# so the right CI job is a passing placeholder named `backend`. Nothing else is in the
# repository, so every `backend/` in the output comes from the skill.
set -euo pipefail

git init -q -b main .
git config user.email "eval@example.invalid"
git config user.name "Eval"

mkdir backend
cat > backend/pyproject.toml <<'INNER'
[project]
name = "ledger"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = [
    "pytest>=8",
    "ruff>=0.6",
]
INNER
git add backend/pyproject.toml
git commit -q -m "chore: add the backend manifest"
