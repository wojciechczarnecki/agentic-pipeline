#!/usr/bin/env bash
# A consumer repository at the start of /pipeline:implement: SPEC 001 is plan-approved and
# its lane branch is checked out. The SPEC has two ACs, but the reviewed plan delivers only
# AC1: its one step never mentions AC2 (the 200-character limit), and its matrix has no AC2
# row. Carrying out the plan alone leaves AC2 missing, so only the converge pass at the end
# of the skill can find it. Every command the skill runs (git fetch, the verify command,
# the metrics check) has to work offline here, or the case would score a setup failure
# instead of the behaviour.
set -euo pipefail

git init -q -b main .
git config user.email "eval@example.invalid"
git config user.name "Eval"
# A global signing setting on the machine running the scaffold must not break it.
git config commit.gpgsign false

# A bare remote inside the workspace: the skill fetches origin and merges origin/main.
git init -q --bare .origin.git
echo ".origin.git" >> .git/info/exclude
git remote add origin "$PWD/.origin.git"

mkdir -p .claude docs shop tests

# The stages read the plugin's templates and section map with Read; under `claude plugin
# eval` the plugin loads from this clone, outside the workspace, so the consumer allows it
# with the absolute clone rule (SPEC 007).
plugin_dir="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)}"
printf '{"permissions": {"allow": ["Read(//%s/**)"]}}\n' "${plugin_dir#/}" >.claude/settings.json

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

A small shop library: orders and their notes. Python 3 standard library only.

- Verification: `python3 -m unittest discover -s tests -q`
- Conventions: `docs/CONVENTIONS.md`; roadmap: `docs/ROADMAP.md`
- Features go through the pipeline: `specs/NNN-<slug>/SPEC.md` and `PLAN.md`.
EOF

cat > docs/CONVENTIONS.md <<'EOF'
# Conventions

- Python 3 standard library only.
- Tests use `unittest` under `tests/`.
- Commits: `feat:`, `fix:`, `test:`, `docs:`; imperative mood; one commit per plan step.
EOF

cat > docs/ROADMAP.md <<'EOF'
# Roadmap

- [ ] Order notes (specs/001-order-notes/SPEC.md)
EOF

cat > docs/DECISIONS.md <<'EOF'
# Decisions

| Date | Decision | Rationale |
|---|---|---|
| 2026-09-01 | An order is a plain dict | No persistence layer yet |
EOF

cat > shop/__init__.py <<'EOF'
EOF

cat > shop/orders.py <<'EOF'
def new_order(order_id):
    return {"id": order_id, "notes": []}
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/test_orders.py <<'EOF'
import unittest

from shop.orders import new_order


class NewOrderTest(unittest.TestCase):
    def test_a_new_order_has_no_notes(self):
        self.assertEqual(new_order(7), {"id": 7, "notes": []})


if __name__ == "__main__":
    unittest.main()
EOF

git add -A
git commit -q -m "feat: add orders"
git push -q origin main

git checkout -q -b feat/001-order-notes
mkdir -p specs/001-order-notes

cat > specs/001-order-notes/SPEC.md <<'EOF'
---
status: plan-approved
stage_history:
  - "spec-ready - 2026-09-01"
  - "plan-draft - 2026-09-01"
  - "plan-approved - 2026-09-01"
metrics:
  started_at: 2026-09-01T09:00
  escalations: 0
  plan_steps: 1
  plan_review_blockers: 0
  plan_review_majors: 0
  plan_changes: 0
---

# SPEC 001 - Order notes

## Goal

A customer can attach short notes to an order.

## Requirements and acceptance criteria

- [ ] AC1: `add_note(order, text)` in `shop/notes.py` appends the text, stripped of
      surrounding whitespace, to `order["notes"]`.
- [ ] AC2: a note longer than 200 characters after stripping raises `ValueError` and
      leaves `order["notes"]` unchanged.

## Owner decisions

- No new dependency.
EOF

cat > specs/001-order-notes/PLAN.md <<'EOF'
# PLAN 001 - Order notes

## Owner summary

- **Approach:** a new module `shop/notes.py` with `add_note`.
- **Main risks:** none.
- **New dependency:** no.
- **Data migration:** no.
- **Manual scenarios for the owner:** none.

## Approach

A plain function on the order dict, next to `shop/orders.py`.

## AC → steps matrix

| AC | Steps | Proving test | Red before the change |
|----|-------|--------------|-----------------------|
| AC1 | 1 | `tests/test_notes.py::test_note_is_stripped` | |

## Steps

- [ ] 1. Order notes - create `shop/notes.py` with `add_note(order, text)`, which appends
      the stripped text to `order["notes"]`, and write `tests/test_notes.py` with
      `test_note_is_stripped`.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> green.

## Risks and traps

- None.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

1. `python3 -m unittest discover -s tests -q` -> green.

### Manual (performed by the owner)

None.

## Definition of Done

- [ ] all steps ticked
- [ ] verification green
- [ ] spec status: `implemented`

## Owner decisions

_(none yet)_

## Review log

### 2026-09-01 - plan review

No findings. The plan is ready.

## Deviations

_(none yet)_

## Final review

_(filled in by the final review)_
EOF

git add -A
git commit -q -m "docs: add SPEC and PLAN 001 order-notes"
