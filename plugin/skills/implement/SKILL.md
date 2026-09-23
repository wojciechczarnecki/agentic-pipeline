---
name: implement
description: Pipeline stage 4 — implementing a feature from the approved PLAN.md (status plan-approved), step by step, in the self-correction loop with end-to-end verification and a commit after every step.
argument-hint: <spec number or slug>
---

# /pipeline:implement — carrying out the approved plan

Role: the plan's executor. The plan has been reviewed and approved — you carry it out
faithfully and verifiably, you do not improve it along the way. You consider the code
correct only when the verification commands say so — never because it "looks good".

## Project configuration

- Read `.claude/workflow.json`; no file = the defaults from the plugin README → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` etc. = values from this configuration (keys in the README).

## Language

- Files you write into the repository (SPEC, PLAN — every section, including decision
  entries, the review log, deviations and the final review report) and the PR description
  are written in the language from `language` in `.claude/workflow.json`; a missing key or
  a value other than `en`/`pl` = `en`. You name a section by its English heading and accept
  either heading from the section map (the "Section map" section).
- Always in English, regardless of `language` and the session: commit messages, PR titles,
  branch names and spec slugs, the `RESULT` block keys, metric keys and severity tokens.
- The conversation with the owner — questions, escalations, summaries and the handoff — in
  the Claude Code session language, never by `language`.

## Section map

- Before you look for a section in a SPEC or PLAN, load the section map
  `${CLAUDE_PLUGIN_ROOT}/templates/sections.md` with the `Read` tool (key → Polish heading →
  English heading). You name a section by its English heading and accept either heading
  the map gives.
- A failed read of the map or a template ends the stage — you do not guess headings and do
  not rebuild a template from memory. Under `/pipeline:ship`: `RESULT: ESCALATE`; run on
  its own: STOP with the same message to the owner. The message gives the file path and
  the rule to add to `permissions.allow` (the project's `.claude/settings.json` or the user
  settings): `Read(~/.claude/plugins/cache/<marketplace>/pipeline/**)`, and for a
  `--plugin-dir` clone — `Read(//<plugin directory path without the leading />/**)`; you
  read `<marketplace>` from the expanded path `${CLAUDE_PLUGIN_ROOT}`
  (`…/plugins/cache/<marketplace>/pipeline/<version>`); when the guard has already shown a
  warning with a ready rule, you give that rule.

## Input / output

- Input: `<docs.specsDir>/NNN-<slug>/` with status `plan-approved`.
- Output: the implementation committed step by step and pushed to the branch
  `feat/NNN-<slug>`, PLAN.md ticked and filled in, spec status → `implemented`.

## Overriding rules

- Precondition: `status: plan-approved` — otherwise STOP, no exceptions
  (no approved plan = no consent to edits).
- Git: you commit yourself, only on the lane branch — after every green step, only
  the files of that step (`git add <files>`, never `git add -A` blindly). `main`, merging
  PRs and rewriting published history are out of your reach (enforced by this plugin's
  command guard).
- Read the files named in the SPEC/PLAN IN FULL (no limit/offset) before you change them —
  working on a fragment is working on a stale model of the code.
- Edits within the plan's scope — without asking. Escalation before: adding a dependency or
  a migration the plan does not provide for (or that `## Owner decisions` does not
  accept); deleting files outside the plan's scope.
- Escalation in a session on its own: `AskUserQuestion` with options and a recommendation,
  the decision appended to PLAN.md → `## Owner decisions`. Under
  `/pipeline:ship`: the RESULT block.

## Procedure

1. **Start:** read SPEC.md, PLAN.md (including `## Owner decisions`)
   and `<docs.conventions>`. Check `git status` (a clean tree)
   and `git branch --show-current` (the lane branch). `git fetch origin`; if `origin/main`
   has commits the branch does not have — `git merge origin/main` (not rebase: the branch
   may already be pushed, and force-push is blocked). A conflict → escalation.
   If the PLAN already has ticked steps (resuming work) — trust them and continue from
   the first unticked one.
2. **Step by step, in order:** the step's implementation + tests → **the self-correction
   loop** (below) → green → tick the checkbox in PLAN.md → commit the step
   (`<type>: <message>` in English, the format from `<docs.conventions>`; the step's files +
   PLAN.md) → the next step.
3. **Deviations:** minor and necessary (a different file name, a small helper) → do it
   and add it to `## Deviations` with a rationale. Ones that change the scope, the
   architecture or the data schema → escalation; do not carry on on your own.
4. **Screen:** when `verify.scopes` has a UI scope and the change touches the interface —
   run `<verify.command> <UI scope>` and LOOK AT the visual artifacts required by
   `<docs.conventions>`; without it the step is not green, and record the result in PLAN.md.
5. **Finish — the plan's Definition of Done:**
   - `<verify.command>` fully green;
   - the plan's end-to-end verification (the automatic section) REALLY performed,
     the result recorded in PLAN.md; the manual items you leave to the owner — list them;
   - `<docs.roadmap>` updated (checkboxes!), `<docs.decisions>` and the domain documents
     from the map in `CLAUDE.md`, if applicable;
   - `status: implemented` + an entry in `stage_history`; in the `metrics:` block of
     SPEC.md: `implement_steps`, `implement_iterations` (the sum of loop iterations beyond
     the first attempt, over all steps), `deviations`;
   - the flat `metrics:` block: integer counters, times `%Y-%m-%dT%H:%M`; before reporting
     success `workflow_metrics.py --check <spec-dir>`;
     a red you cannot fix from your own artifacts = `RESULT: ESCALATE` (on its own:
     STOP with a question) with the names of the missing keys; you do not invent an
     unmeasured value;
   - the closing commit, then `git push -u origin feat/NNN-<slug>`.

## Self-correction loop (mandatory for every step)

You take the commands from the `Automatic verification:` section of the given
plan step — you run exactly those, not approximations (for fast iteration on one
layer there is `<verify.command>` with a scope from `verify.scopes`).

```
1. Run ALL the step's verification commands.
2. Everything green → end of the loop, the step is done.
3. Something red:
   a. read the FULL error output — do not skim; with many errors start from
      the FIRST (the next ones are often a cascade of the first);
   b. establish the cause: an implementation bug / a wrong assumption / a mismatch with
      the plan / a product defect the test rightly found;
   c. a mismatch with the plan → escalation (Expected / Found / Why it matters);
   d. a product defect (also in code from before this spec) → fix the product, if the fix
      fits within the plan's scope and the owner decisions; otherwise escalation.
      NEVER fit the test to the defect — no change of test data, assertions,
      selectors, timeouts or views just so that the error stops being visible;
   e. a bug → fix it and go back to 1. — run ALL the commands AGAIN
      (a fix can break what already passed).
4. The fourth iteration on the same error → escalation: what you tried (a list of attempts
   with results), a hypothesis of the cause, what you need. Do not guess any further.
```

**Gate:** you do NOT go on to the next step with the current one's verification red.
No exceptions, no "it is probably flaky", no skipping tests.

## Guardrails

- Do not weaken, skip (`skip`) or change existing tests or their data
  to make them pass — a conflict with a test is an escalation (unless the plan explicitly
  provides for changing the test). A test red because of a product defect is a signal to fix
  the product, not the test.
- Do not touch files unrelated to the plan — "while at it" (formatting, refactors,
  typos outside the scope) does not exist.
- Secrets and real users' data never in code, logs, commits or tests.

## Handoff

- **Run on its own:** summarise what was done, the deviations, the verification result
  and the manual scenarios; the next stage is `/pipeline:final-review NNN` after `/clear`.
- **Under `/pipeline:ship`:** end with the RESULT block from the stage agent contract.
