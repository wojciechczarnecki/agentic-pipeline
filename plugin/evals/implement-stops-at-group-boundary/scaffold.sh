#!/usr/bin/env bash
# A consumer repository at the start of /pipeline:implement with chunking on: SPEC 001 is
# plan-approved, its lane branch is checked out, and `.claude/workflow.json` has
# `"implement": {"chunked": true}`. The reviewed plan has two step groups: group 1 (steps 1
# and 2, `add_tag`) and group 2 (step 3, `tags_line`). Each step is small and green on its
# own, so the only reason to stop after step 2 is the group boundary. Every command the
# skill runs (git fetch, git push, the verify command, the metrics check) has to work
# offline here, or the case would score a setup failure instead of the behaviour.
set -euo pipefail

git init -q -b main .
git config user.email "eval@example.invalid"
git config user.name "Eval"
# A global signing setting on the machine running the scaffold must not break it.
git config commit.gpgsign false

# A bare remote inside the workspace: the skill fetches origin, and a chunk pushes its
# branch at the group boundary.
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
  "language": "en",
  "implement": {"chunked": true}
}
EOF

cat > .gitignore <<'EOF'
__pycache__/
EOF

cat > CLAUDE.md <<'EOF'
# CLAUDE.md

A small shop library: orders and their tags. Python 3 standard library only.

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

- [ ] Order tags (specs/001-order-tags/SPEC.md)
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
    return {"id": order_id, "tags": []}
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/test_orders.py <<'EOF'
import unittest

from shop.orders import new_order


class NewOrderTest(unittest.TestCase):
    def test_a_new_order_has_no_tags(self):
        self.assertEqual(new_order(7), {"id": 7, "tags": []})


if __name__ == "__main__":
    unittest.main()
EOF

git add -A
git commit -q -m "feat: add orders"
git push -q origin main

git checkout -q -b feat/001-order-tags
mkdir -p specs/001-order-tags

cat > specs/001-order-tags/SPEC.md <<'EOF'
---
status: plan-approved
stage_history:
  - "spec-ready - 2026-09-01"
  - "plan-draft - 2026-09-01"
  - "plan-approved - 2026-09-01"
metrics:
  started_at: 2026-09-01T09:00
  escalations: 0
  plan_steps: 3
  plan_review_blockers: 0
  plan_review_majors: 0
  plan_changes: 0
---

# SPEC 001 - Order tags

## Goal

A clerk can tag an order and print its tags on the packing label.

## Requirements and acceptance criteria

- [ ] AC1: `add_tag(order, tag)` in `shop/tags.py` appends the tag, lower-cased, to
      `order["tags"]`.
- [ ] AC2: adding a tag the order already has (in any case) leaves `order["tags"]`
      unchanged.
- [ ] AC3: `tags_line(order)` in `shop/labels.py` returns the tags sorted and joined by
      ", ", and an empty string for an order without tags.

## Owner decisions

- No new dependency.
EOF

cat > specs/001-order-tags/PLAN.md <<'EOF'
# PLAN 001 - Order tags

## Owner summary

- **Approach:** `add_tag` in a new module `shop/tags.py`, then `tags_line` in a new module
  `shop/labels.py`.
- **Main risks:** none.
- **New dependency:** no.
- **Data migration:** no.
- **Manual scenarios for the owner:** none.

## Approach

Plain functions on the order dict, next to `shop/orders.py`. Group 1 delivers tagging,
group 2 the label line that reads the tags.

## AC → steps matrix

| AC | Steps | Proving test | Red before the change |
|----|-------|--------------|-----------------------|
| AC1 | 1 | `tests/test_tags.py::AddTagTest::test_tag_is_lower_cased` | |
| AC2 | 2 | `tests/test_tags.py::AddTagTest::test_duplicate_is_ignored` | |
| AC3 | 3 | `tests/test_labels.py::TagsLineTest::test_tags_are_sorted_and_joined` | |

## Steps

### Group 1 — Tags

- [ ] 1. Add a tag - create `shop/tags.py` with `add_tag(order, tag)`, which appends the
      lower-cased tag to `order["tags"]`, and `tests/test_tags.py` with
      `AddTagTest.test_tag_is_lower_cased`.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> green.
- [ ] 2. Ignore a duplicate - `add_tag` leaves `order["tags"]` unchanged when the
      lower-cased tag is already there; test `AddTagTest.test_duplicate_is_ignored`.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> green.

### Group 2 — Label

- [ ] 3. The label line - create `shop/labels.py` with `tags_line(order)`, which returns
      the tags sorted and joined by ", " (an empty string without tags), and
      `tests/test_labels.py` with `TagsLineTest.test_tags_are_sorted_and_joined` and
      `TagsLineTest.test_no_tags_is_empty`.
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

No findings. Two groups: tagging and the label line need different modules. The plan is
ready.

## Chunk notes

_(filled in by /pipeline:implement in chunk mode - one entry per chunk that ends at a group boundary)_

## Deviations

_(none yet)_

## Final review

_(filled in by the final review)_
EOF

git add -A
git commit -q -m "docs: add SPEC and PLAN 001 order-tags"
git push -q -u origin feat/001-order-tags
