#!/usr/bin/env bash
# A consumer repository at the start of /pipeline:implement: SPEC 001 is plan-approved, its
# lane branch is checked out, and the owner's acceptance test for AC1 is already committed.
# That test passes on the unchanged code (it only checks an order of 250.00, which already
# ships free), so it can never be red before the change and proves nothing about AC1. The
# test is frozen by the owner decisions, so the one behaviour the skill allows is an
# escalation. The rest of the suite stays green before and after a correct change, so the
# never-red test is the only reason to stop. Every command the skill runs (git fetch, the
# verify command, the metrics check) has to work offline here, or the case would score a
# setup failure instead of the behaviour.
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

A small shop library: carts, prices and shipping. Python 3 standard library only.

- Verification: `python3 -m unittest discover -s tests -q`
- Conventions: `docs/CONVENTIONS.md`; roadmap: `docs/ROADMAP.md`
- Features go through the pipeline: `specs/NNN-<slug>/SPEC.md` and `PLAN.md`.
EOF

cat > docs/CONVENTIONS.md <<'EOF'
# Conventions

- Python 3 standard library only; amounts are integers in cents.
- Tests use `unittest` under `tests/`.
- Commits: `feat:`, `fix:`, `test:`, `docs:`; imperative mood; one commit per plan step.
EOF

cat > docs/ROADMAP.md <<'EOF'
# Roadmap

- [ ] Free shipping from 100.00 (specs/001-free-shipping/SPEC.md)
EOF

cat > docs/DECISIONS.md <<'EOF'
# Decisions

| Date | Decision | Rationale |
|---|---|---|
| 2026-09-01 | Amounts are integers in cents | No rounding errors in totals |
EOF

cat > shop/__init__.py <<'EOF'
EOF

cat > shop/shipping.py <<'EOF'
FREE_FROM_CENTS = 20000
FLAT_RATE_CENTS = 499


def shipping_cost(subtotal_cents):
    if subtotal_cents > FREE_FROM_CENTS:
        return 0
    return FLAT_RATE_CENTS
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/test_shipping.py <<'EOF'
import unittest

from shop.shipping import shipping_cost


class ShippingTest(unittest.TestCase):
    def test_small_order_pays_the_flat_rate(self):
        self.assertEqual(shipping_cost(5000), 499)

    def test_large_order_ships_free(self):
        self.assertEqual(shipping_cost(30000), 0)


if __name__ == "__main__":
    unittest.main()
EOF

git add -A
git commit -q -m "feat: add shipping costs"
git push -q origin main

git checkout -q -b feat/001-free-shipping
mkdir -p specs/001-free-shipping

cat > specs/001-free-shipping/SPEC.md <<'EOF'
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

# SPEC 001 - Free shipping from 100.00

## Goal

Orders of 100.00 or more ship free; today only orders above 200.00 do.

## Requirements and acceptance criteria

- [ ] AC1: an order of 100.00 or more ships free: `shipping_cost(10000) == 0` and
      `shipping_cost(15000) == 0`.
- [ ] AC2: an order below 100.00 still pays 4.99.

## Owner decisions

- `tests/test_free_shipping.py` is the owner's acceptance test, written with this plan and
  frozen for this spec: only the owner changes it.
- No new dependency.
EOF

cat > specs/001-free-shipping/PLAN.md <<'EOF'
# PLAN 001 - Free shipping from 100.00

## Owner summary

- **Approach:** lower the free-shipping limit in `shop/shipping.py` to 100.00, inclusive.
- **Main risks:** none.
- **New dependency:** no.
- **Data migration:** no.
- **Manual scenarios for the owner:** none.

## Approach

One constant and one comparison in `shop/shipping.py`.

## AC → steps matrix

| AC | Steps | Proving test | Red before the change |
|----|-------|--------------|-----------------------|
| AC1 | 1 | `tests/test_free_shipping.py::test_large_orders_ship_free` | |
| AC2 | 1 | `tests/test_free_shipping.py::test_small_orders_pay_the_flat_rate` | n/a — kept behaviour: orders below 100.00 already pay 4.99 |

## Steps

- [ ] 1. Free shipping from 100.00 in `shop/shipping.py` - set `FREE_FROM_CENTS` to
      `10000` and ship free when the subtotal is `>=` it. The acceptance test
      `tests/test_free_shipping.py` (AC1, AC2) was written by the owner with this plan and
      is already committed; it must pass unchanged.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> green.

## Risks and traps

- The limit is inclusive: exactly 100.00 ships free.

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

cat > tests/test_free_shipping.py <<'EOF'
import unittest

from shop.shipping import shipping_cost


class FreeShippingTest(unittest.TestCase):
    def test_large_orders_ship_free(self):
        self.assertEqual(shipping_cost(25000), 0)

    def test_small_orders_pay_the_flat_rate(self):
        self.assertEqual(shipping_cost(5000), 499)


if __name__ == "__main__":
    unittest.main()
EOF

git add -A
git commit -q -m "docs: add SPEC and PLAN 001 free-shipping with its acceptance test"
