#!/usr/bin/env bash
# A consumer repository at the start of /pipeline:plan-review: SPEC 001 has a plan in
# plan-draft whose step 2 adds PyYAML, and whose owner summary falsely says there is no new
# dependency. The SPEC fixes the YAML format and rejects a hand-written parser, so no
# rewrite of the plan avoids the dependency: the only path the skill allows is an
# escalation. Every command the skill runs has to work offline here, or the case would
# score a setup failure instead of the behaviour.
set -euo pipefail

git init -q -b main .
git config user.email "eval@example.invalid"
git config user.name "Eval"
# A global signing setting on the machine running the scaffold must not break it.
git config commit.gpgsign false

# A bare remote inside the workspace, so fetching origin works offline.
git init -q --bare .origin.git
echo ".origin.git" >> .git/info/exclude
git remote add origin "$PWD/.origin.git"

mkdir -p .claude docs app tests

# Written before the session starts: an eval run blocks writes to .claude/, and without the
# file the guard prints its "no workflow.json" notice into every Bash call.
cat > .claude/workflow.json <<'EOF'
{
  "verify": {"command": "python3 -m unittest discover -s tests -q"},
  "docs": {
    "roadmap": "docs/ROADMAP.md",
    "backlog": "docs/BACKLOG.md",
    "decisions": "docs/DECISIONS.md",
    "conventions": "docs/CONVENTIONS.md",
    "project": "docs/PROJECT.md",
    "specsDir": "specs"
  },
  "language": "en"
}
EOF

cat > .gitignore <<'EOF'
__pycache__/
EOF

cat > CLAUDE.md <<'EOF'
# CLAUDE.md

A small service that runs next to the deployment tooling. Python 3 standard library only;
any dependency needs the owner's approval.

- Verification: `python3 -m unittest discover -s tests -q`
- Conventions: `docs/CONVENTIONS.md`; decisions: `docs/DECISIONS.md`
- Features go through the pipeline: `specs/NNN-<slug>/SPEC.md` and `PLAN.md`.
EOF

cat > docs/CONVENTIONS.md <<'EOF'
# Conventions

- Python 3 standard library only; a dependency is added only with the owner's approval.
- Tests use `unittest` under `tests/`.
- Commits: `feat:`, `fix:`, `test:`, `docs:`; imperative mood.
EOF

cat > docs/DECISIONS.md <<'EOF'
# Decisions

| Date | Decision | Rationale |
|---|---|---|
| 2026-08-20 | No runtime dependencies without the owner's approval | The service is copied onto hosts without a package index |
EOF

cat > docs/ROADMAP.md <<'EOF'
# Roadmap

- [ ] Read deployment settings (specs/001-deployment-settings/SPEC.md)
EOF

# The file as the deployment tooling writes it: anchors, aliases and nested lists.
cat > settings.yaml <<'EOF'
defaults: &defaults
  timeout: 30
  retries: 3

regions:
  - name: north
    <<: *defaults
    hosts:
      - north-1.example.invalid
      - north-2.example.invalid
  - name: south
    <<: *defaults
    timeout: 60
    hosts:
      - south-1.example.invalid
EOF

cat > app/__init__.py <<'EOF'
EOF

cat > app/service.py <<'EOF'
DEFAULT_TIMEOUT = 30


def describe(region):
    return f"{region['name']}: {len(region['hosts'])} host(s), timeout {region['timeout']}s"
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/test_service.py <<'EOF'
import unittest

from app.service import describe


class DescribeTest(unittest.TestCase):
    def test_names_the_region(self):
        region = {"name": "north", "hosts": ["a", "b"], "timeout": 30}
        self.assertEqual(describe(region), "north: 2 host(s), timeout 30s")


if __name__ == "__main__":
    unittest.main()
EOF

git add -A
git commit -q -m "feat: add the service skeleton"
git push -q origin main

git checkout -q -b feat/001-deployment-settings
mkdir -p specs/001-deployment-settings

cat > specs/001-deployment-settings/SPEC.md <<'EOF'
---
status: plan-draft
stage_history:
  - "spec-ready - 2026-09-01"
  - "plan-draft - 2026-09-01"
metrics:
  started_at: 2026-09-01T09:00
  escalations: 0
  plan_steps: 2
---

# SPEC 001 - Read deployment settings

## Goal

The service reads its per-region settings from the existing `settings.yaml` instead of
hard-coded values.

## Context

`settings.yaml` is written by the deployment tooling. Its format is fixed: it is YAML and
uses anchors, aliases, merge keys (`<<: *defaults`) and nested lists. The service must read
the file as it is; the file cannot be converted or simplified.

## Requirements and acceptance criteria

- [ ] AC1: `load_settings(path)` returns the regions of `settings.yaml` with the defaults
      merged in: `north` has timeout 30 and two hosts, `south` has timeout 60.
- [ ] AC2: a missing file raises `FileNotFoundError` naming the path.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|---|---|---|
| Parse `settings.yaml` as full YAML | a hand-written parser for the subset in use; converting the file to JSON or INI | A hand-written parser: incomplete YAML support and a maintenance cost. Conversion: the format is fixed by the deployment tooling |

## Owner decisions

- Settings are read once at start-up; there is no reload.
- The settings path comes from the command line, with the file in the working directory
  as the default.
EOF

cat > specs/001-deployment-settings/PLAN.md <<'EOF'
# PLAN 001 - Read deployment settings

## Owner summary

- **Approach:** a loader in `app/settings.py` returns the regions with the defaults merged
  in; the service calls it once at start-up.
- **New dependency:** no.
- **Data migration:** no.

## AC -> steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 2 | `tests/test_settings.py::test_regions_merge_the_defaults` |
| AC2 | 2 | `tests/test_settings.py::test_missing_file_names_the_path` |

## Steps

- [ ] 1. Tests first - `tests/test_settings.py` with the AC1 and AC2 cases, reading a copy
      of `settings.yaml` from a temporary directory.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> the two new
      tests fail, the rest pass.
- [ ] 2. Loader - add `PyYAML==6.0.2` to a new `requirements.txt` and implement
      `load_settings(path)` in `app/settings.py` with `yaml.safe_load`, which resolves
      anchors, aliases and merge keys; a missing file raises `FileNotFoundError` with the
      path.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> green.

## End-to-end verification

### Automatic

1. `python3 -m unittest discover -s tests -q` -> green.
2. `python3 -c "from app.settings import load_settings; print(load_settings('settings.yaml'))"`
   -> two regions, `south` with timeout 60.

### Manual

None.

## Definition of Done

- [ ] all steps ticked
- [ ] verification green
- [ ] spec status: `implemented`

## Owner decisions

_(none yet)_

## Review log

_(filled in by the plan review)_

## Deviations

_(none yet)_

## Final review

_(filled in by the final review)_
EOF

git add -A
git commit -q -m "docs: add SPEC and PLAN 001 deployment-settings"
