# PLAN NNN — <feature name>

## Owner summary

- **Approach:** <2–4 sentences>
- **Main risks:** <…>
- **New dependency:** no | yes — <name, what for; accepted in SPEC → "Owner decisions"?>
- **Data migration:** no | yes — <what it changes; accepted in SPEC → "Owner decisions"?>
- **Manual scenarios for the owner:** <a number + one sentence on what they cover>

## Approach

<how and why; existing patterns/utilities to reuse, with file paths>

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|

## Steps

- [ ] 1. <what> — files: `…`
      Automatic verification: `<exact commands, e.g. running a specific test file>`
      (when the step is ticked, its line ends with `iterations: <k>` in backticks: the loop
      iterations beyond the first attempt, 0 when the step was green at once)
- [ ] 2. …

## Risks and traps

- <e.g. test vs production database differences, migrations, time zones, user-facing
  texts, authorisation>

## End-to-end verification

### Automatic (performed by /pipeline:implement)

<commands against the running application: bringing the stack up, HTTP requests, scripts,
visual review tests — with the expected results>

### Manual (performed by the owner)

- <a scenario — only what cannot be automated>
  Pass when: <a command, a query or a place in the UI, with the expected result>

## Definition of Done

- [ ] all steps ticked
- [ ] `<verify.command>` fully green
- [ ] end-to-end verification (automatic) performed, result recorded here
- [ ] `<docs.roadmap>` updated; `<docs.decisions>` / domain documents from the map
      in `CLAUDE.md`, if applicable
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation, one entry per line: `- YYYY-MM-DD — <stage> — `<kind>` — <question> — <decision>`, with the kind `decision`, `permission` or `tooling`; a final-review gate entry has the kind `gate` and ends with `accepted`: F1, F2; `rejected`: F3, `none` for an empty list)_

## Review log

_(filled in by /pipeline:plan-review — one list item per finding, starting with its severity in backticks: `- `blocker` — …`, `major` or `minor`)_

## Deviations

_(filled in by /pipeline:implement — one entry per deviation, with its rationale: `- `minor` — …` or `- `major` — …`)_

## Final review

_(filled in by /pipeline:final-review — one line per finding: `- **F<n>** `<blocker|worth-fixing|nit>` — …`)_
