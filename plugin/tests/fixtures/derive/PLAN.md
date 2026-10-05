# PLAN 001 — derive fixture

## Owner summary

- **Approach:** a fixture.

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 1 | `test_one` |
| AC2, AC3 | 2, 3 | `test_two` |

## Steps

- [x] 1. First step — files: `a.py` — `iterations: 0`
      Automatic verification: `pytest a`
- [x] 2. Second step — files: `b.py`
      Automatic verification: `pytest b` — `iterations: 2`
- [x] 3. Third step — files: `c.py` — `iterations: 1`
      Automatic verification: `pytest c`
- [X] 4. Fourth step — files: `d.py` — `iterations: 0`
      Automatic verification: `pytest d`

## End-to-end verification

### Automatic (performed by /pipeline:implement)

- `pytest` is green.

### Manual (performed by the owner)

- Open the page and read the heading.
  Pass when: the heading says "Hello".

## Owner decisions

- 2026-10-05 — implement — `decision` — Rename the helper? — Yes, within the plan.
- 2026-10-05 - implement - `permission` - The classifier refused `uv lock` - Run it alone.
- 2026-10-05 – final-review – `tooling` – CI runner died – Re-run.
- 2026-10-04 — final-review — `gate` — An earlier report — `accepted`: F1; `rejected`: none
- 2026-10-05 — final-review — `gate` — The report — `accepted`: F1, F2, F3; `rejected`: F4

## Review log

Findings:

- `blocker` — The plan skipped AC3.
- `major` — A step depended on a later one.
- `major` — The verification command was approximate.
- `minor` — A file name was misspelled.

Later findings, numbered:

1. `major` — A numbered finding.

Checked and found sound:

- Coverage: every AC has a row.

## Deviations

- `minor` — A helper got another name.
- `major` — The scope grew by one file.
- A deviation written without a token counts as minor.

## Final review

- **F1** `blocker` — A null dereference.
- **F2** `worth-fixing` — A missing test.
- **F3** `worth-fixing` — A misleading message.
- **F4** `nit` — A long line.
- **F2** `worth-fixing` — the same finding named again, counted once.
- A claimed leak, rejected as false by the reviewer, has no id here.
