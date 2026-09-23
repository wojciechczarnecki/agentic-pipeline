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
- [ ] 2. …

## Risks and traps

- <e.g. test vs production database differences, migrations, time zones, user-facing
  texts, authorisation>

## End-to-end verification

### Automatic (performed by /pipeline:implement)

<commands against the running application: bringing the stack up, HTTP requests, scripts,
visual review tests — with the expected results>

### Manual (performed by the owner)

<a short list of scenarios — only what cannot be automated>

## Definition of Done

- [ ] all steps ticked
- [ ] `<verify.command>` fully green
- [ ] end-to-end verification (automatic) performed, result recorded here
- [ ] `<docs.roadmap>` updated; `<docs.decisions>` / domain documents from the map
      in `CLAUDE.md`, if applicable
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

_(filled in by /pipeline:plan-review)_

## Deviations

_(filled in by /pipeline:implement — every deviation from the plan with its rationale)_

## Final review

_(filled in by /pipeline:final-review)_
