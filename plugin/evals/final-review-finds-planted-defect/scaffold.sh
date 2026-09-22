#!/usr/bin/env bash
# A consumer repository at the start of /pipeline:final-review: SPEC 001 is implemented, its
# plan fully ticked, and the lane branch carries a boundary defect (`>` where the SPEC needs
# `>=`) behind a green suite. The fixture is kept tiny because report mode starts three
# review subagents on it. Every command the skill runs (git fetch, the diff against
# origin/main, the verify command, the metrics check) has to work offline here.
set -euo pipefail

git init -q -b main .
git config user.email "eval@example.invalid"
git config user.name "Eval"
# A global signing setting on the machine running the scaffold must not break it.
git config commit.gpgsign false

# A bare remote inside the workspace: the skill diffs the branch against origin/main.
git init -q --bare .origin.git
echo ".origin.git" >> .git/info/exclude
git remote add origin "$PWD/.origin.git"

mkdir -p .claude docs shop tests

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

A small shop library: carts, prices and shipping. Python 3 standard library only.

- Verification: `python3 -m unittest discover -s tests -q`
- Conventions: `docs/CONVENTIONS.md`; roadmap: `docs/ROADMAP.md`
- Features go through the pipeline: `specs/NNN-<slug>/SPEC.md` and `PLAN.md`.
EOF

cat > docs/CONVENTIONS.md <<'EOF'
# Conventions

- Python 3 standard library only; amounts are integers in cents.
- Tests use `unittest` under `tests/`.
- Commits: `feat:`, `fix:`, `test:`, `docs:`; imperative mood.
EOF

cat > docs/ROADMAP.md <<'EOF'
# Roadmap

- [ ] Free shipping (specs/001-free-shipping/SPEC.md)
EOF

cat > shop/__init__.py <<'EOF'
EOF

cat > tests/__init__.py <<'EOF'
EOF

git add -A
git commit -q -m "chore: start the shop library"
git push -q origin main

git checkout -q -b feat/001-free-shipping
mkdir -p specs/001-free-shipping

cat > specs/001-free-shipping/SPEC.md <<'EOF'
---
status: implemented
stage_history:
  - "spec-ready - 2026-09-01"
  - "plan-draft - 2026-09-01"
  - "plan-approved - 2026-09-01"
  - "implemented - 2026-09-02"
metrics:
  started_at: 2026-09-01T09:00
  escalations: 0
  plan_steps: 2
  plan_review_blockers: 0
  plan_review_majors: 0
  plan_changes: 0
  implement_steps: 2
  implement_iterations: 0
  deviations: 0
---

# SPEC 001 - Free shipping

## Goal

Orders above a threshold ship free; the others pay a flat rate.

## Requirements and acceptance criteria

- [ ] AC1: orders whose subtotal is 100.00 or more ship free.
- [ ] AC2: orders below 100.00 pay a flat 9.90 for shipping.

## Owner decisions

- The threshold and the flat rate are constants in code; no configuration.
EOF

cat > specs/001-free-shipping/PLAN.md <<'EOF'
# PLAN 001 - Free shipping

## Owner summary

- **Approach:** `shipping_cost(subtotal_cents)` in a new `shop/shipping.py`.
- **New dependency:** no.
- **Data migration:** no.

## AC -> steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 1, 2 | `tests/test_shipping.py::test_large_orders_ship_free` |
| AC2 | 1, 2 | `tests/test_shipping.py::test_small_orders_pay_the_flat_rate` |

## Steps

- [x] 1. Tests - `tests/test_shipping.py` for AC1 and AC2.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> the new tests
      fail.
- [x] 2. `shop/shipping.py` - `shipping_cost(subtotal_cents)`: free from the threshold up,
      the flat rate below it.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> green.

## End-to-end verification

### Automatic

1. `python3 -m unittest discover -s tests -q` -> green.

### Manual

None.

### Results

- 2026-09-02: `python3 -m unittest discover -s tests -q` -> OK (2 tests).

## Definition of Done

- [x] all steps ticked
- [x] verification green
- [x] spec status: `implemented`

## Owner decisions

_(none yet)_

## Review log

### 2026-09-01 - plan review

No findings. The plan is ready.

## Deviations

_(none)_

## Final review

_(filled in by the final review)_
EOF

git add specs
git commit -q -m "docs: add SPEC and PLAN 001 free-shipping"

cat > tests/test_shipping.py <<'EOF'
import unittest

from shop.shipping import shipping_cost


class ShippingTest(unittest.TestCase):
    def test_large_orders_ship_free(self):
        self.assertEqual(shipping_cost(15000), 0)

    def test_small_orders_pay_the_flat_rate(self):
        self.assertEqual(shipping_cost(5000), 990)


if __name__ == "__main__":
    unittest.main()
EOF
git add tests/test_shipping.py
git commit -q -m "test: cover free shipping"

cat > shop/shipping.py <<'EOF'
FLAT_RATE_CENTS = 990
FREE_FROM_CENTS = 10000


def shipping_cost(subtotal_cents):
    if subtotal_cents > FREE_FROM_CENTS:
        return 0
    return FLAT_RATE_CENTS
EOF
git add shop/shipping.py
git commit -q -m "feat: add free shipping from 100.00"
