#!/usr/bin/env bash
# A consumer repository at the start of /pipeline:final-review: SPEC 001 is implemented, its
# plan fully ticked, and the lane branch adds code that looks like an SQL injection but is
# not — the ORDER BY column is interpolated only after a whitelist check, because an
# identifier cannot be a bound parameter. The rest of the diff is deliberately clean and
# every acceptance criterion has a test, so the case measures whether the review verifies a
# finding before it keeps it. Every command the skill runs has to work offline here.
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

mkdir -p .claude docs app tests

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

A small user directory on SQLite. Python 3 standard library only.

- Verification: `python3 -m unittest discover -s tests -q`
- Conventions: `docs/CONVENTIONS.md`; roadmap: `docs/ROADMAP.md`
- Features go through the pipeline: `specs/NNN-<slug>/SPEC.md` and `PLAN.md`.
EOF

cat > docs/CONVENTIONS.md <<'EOF'
# Conventions

- Python 3 standard library only; storage is `sqlite3`.
- Values reach SQL as bound parameters; an identifier that cannot be bound (a column in
  `ORDER BY`) is checked against a whitelist in code before it is formatted in.
- Tests use `unittest` under `tests/`, on an in-memory database.
- Commits: `feat:`, `fix:`, `test:`, `docs:`; imperative mood.
EOF

cat > docs/ROADMAP.md <<'EOF'
# Roadmap

- [ ] Sortable user list (specs/001-sortable-user-list/SPEC.md)
EOF

cat > app/__init__.py <<'EOF'
EOF

cat > app/db.py <<'EOF'
import sqlite3

SCHEMA = "CREATE TABLE IF NOT EXISTS users (name TEXT NOT NULL, created_at TEXT NOT NULL)"


def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.execute(SCHEMA)
    return conn


def add_user(conn, name, created_at):
    conn.execute("INSERT INTO users (name, created_at) VALUES (?, ?)", (name, created_at))
EOF

cat > tests/__init__.py <<'EOF'
EOF

git add -A
git commit -q -m "feat: add the user store"
git push -q origin main

git checkout -q -b feat/001-sortable-user-list
mkdir -p specs/001-sortable-user-list

cat > specs/001-sortable-user-list/SPEC.md <<'EOF'
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

# SPEC 001 - Sortable user list

## Goal

List user names sorted by a column the caller chooses.

## Requirements and acceptance criteria

- [ ] AC1: `list_users(conn)` returns the names sorted by `name`.
- [ ] AC2: `list_users(conn, "created_at")` returns the names oldest first.
- [ ] AC3: any other `sort` value raises `ValueError` and never reaches the database.

## Owner decisions

- Two sortable columns only: `name` and `created_at`.
EOF

cat > specs/001-sortable-user-list/PLAN.md <<'EOF'
# PLAN 001 - Sortable user list

## Owner summary

- **Approach:** `list_users(conn, sort="name")` in a new `app/users.py`; the column is
  checked against a whitelist before it goes into `ORDER BY`, because a column name cannot
  be a bound parameter.
- **New dependency:** no.
- **Data migration:** no.

## AC -> steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 1, 2 | `tests/test_users.py::test_sorts_by_name_by_default` |
| AC2 | 1, 2 | `tests/test_users.py::test_sorts_by_creation_date` |
| AC3 | 1, 2 | `tests/test_users.py::test_rejects_any_other_column` |

## Steps

- [x] 1. Tests - `tests/test_users.py` for AC1-AC3 on an in-memory database.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> the new tests
      fail.
- [x] 2. `app/users.py` - `SORTABLE` whitelist, `ValueError` for anything else, then the
      query.
      Automatic verification: `python3 -m unittest discover -s tests -q` -> green.

## End-to-end verification

### Automatic

1. `python3 -m unittest discover -s tests -q` -> green.

### Manual

None.

### Results

- 2026-09-02: `python3 -m unittest discover -s tests -q` -> OK (3 tests).

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
git commit -q -m "docs: add SPEC and PLAN 001 sortable-user-list"

cat > tests/test_users.py <<'EOF'
import unittest

from app.db import add_user, connect
from app.users import list_users


class ListUsersTest(unittest.TestCase):
    def setUp(self):
        self.conn = connect()
        add_user(self.conn, "carol", "2026-01-03")
        add_user(self.conn, "alice", "2026-01-02")
        add_user(self.conn, "bob", "2026-01-01")

    def tearDown(self):
        self.conn.close()

    def test_sorts_by_name_by_default(self):
        self.assertEqual(list_users(self.conn), ["alice", "bob", "carol"])

    def test_sorts_by_creation_date(self):
        self.assertEqual(list_users(self.conn, "created_at"), ["bob", "alice", "carol"])

    def test_rejects_any_other_column(self):
        for sort in ("password", "name; DROP TABLE users", ""):
            with self.subTest(sort=sort):
                with self.assertRaises(ValueError):
                    list_users(self.conn, sort)
        self.assertEqual(len(list_users(self.conn)), 3)


if __name__ == "__main__":
    unittest.main()
EOF
git add tests/test_users.py
git commit -q -m "test: cover the sortable user list"

cat > app/users.py <<'EOF'
SORTABLE = ("name", "created_at")


def list_users(conn, sort="name"):
    if sort not in SORTABLE:
        raise ValueError(f"cannot sort users by {sort!r}; choose one of {SORTABLE}")
    rows = conn.execute(f"SELECT name FROM users ORDER BY {sort}").fetchall()
    return [name for (name,) in rows]
EOF
git add app/users.py
git commit -q -m "feat: list users sorted by a whitelisted column"
