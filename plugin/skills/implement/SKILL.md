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
- Read the files named in the SPEC/PLAN in full (no limit/offset) before you change them —
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
2. **Step by step, in order:** the step's proving test first → its red record (the
   test-first evidence section below) → the product change and the step's other tests →
   **the self-correction loop** (below) → green → tick the checkbox in PLAN.md → commit the
   step (`<type>: <message>` in English, the format from `<docs.conventions>`; the step's
   files + PLAN.md) → the next step.
3. **Deviations:** minor and necessary (a different file name, a small helper) → do it
   and add it to `## Deviations` with a rationale. Ones that change the scope, the
   architecture or the data schema → escalation; do not carry on on your own.
4. **Screen:** when `verify.scopes` has a UI scope and the change touches the interface —
   run `<verify.command> <UI scope>` and look at the visual artifacts required by
   `<docs.conventions>`; without it the step is not green, and record the result in PLAN.md.
5. **Converge pass:** after the last planned step, before the Definition of Done — the
   converge pass section below.
6. **Finish — the plan's Definition of Done:**
   - `<verify.command>` fully green;
   - the plan's end-to-end verification (the automatic section) really performed,
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

## Test-first evidence

A test that was never red proves nothing: it may pass for a reason that has nothing to do
with the change. So each AC's proving test is seen failing before the change that is meant
to make it pass.

- Before that change, run the AC's proving test. Record the command and the failing
  assertion line in the fourth column of the AC → steps matrix, as
  `` `<command>` → `<failing assertion line>` ``.
- Red means a failed assertion about the AC's behaviour. An import, collection or syntax
  error is not red, because such an error is red for any reason. When the symbol under
  test does not exist yet, add a stub first (a function that returns a placeholder value),
  so that the test reaches its assertion, and record that assertion failure.
- The step that makes an AC's proving test pass is not green and is not ticked while that
  AC has no red record, unless the row is marked `manual` (the owner checks it by hand) or
  `n/a — <reason>`. Earlier steps that deliver part of the same AC are ticked on their own
  verification.
- A proving test that is green before the change:
  - when the step writes the test and the test does not exercise the AC's behaviour,
    rewrite it until it fails on the assertion — a test that passes on the old code does
    not check the new behaviour;
  - when the step writes the test and the test does exercise the AC's behaviour, the
    behaviour already exists: that is a gap in the SPEC, so escalate
    (Expected / Found / Why it matters) and leave the step unticked instead of bending the
    test away from the AC;
  - when the test existed before, or the plan gives it verbatim, escalate
    (Expected / Found / Why it matters), leave the test unchanged and the step unticked —
    that test belongs to the owner or to the plan, and changing it is the owner's call.
- An AC whose own words require existing behaviour to stay as it is (a regression guard)
  is green before the change by design; its row is marked `n/a — kept behaviour`. An AC
  that asks for new behaviour never gets this mark.
- A plan written before 0.7.0 has no fourth column: add it, with the heading taken from
  `${CLAUDE_PLUGIN_ROOT}/templates/PLAN.<language>.md`, and mark the kept-behaviour rows
  yourself, quoting the AC's words. A plan with no matrix at all gets one the same way.

## Converge pass

A plan can miss an AC, and the implementer who carried it out shares the plan's blind
spots. So before the Definition of Done a fresh reader compares the code with the SPEC.

- An AC that the SPEC has and the plan leaves out is not a plan mismatch to escalate at
  the start: carry out the planned steps and leave that AC to the converge pass.
- Start a fresh subagent with `Agent`. Give it the path of SPEC.md, the diff command
  `git diff origin/main...HEAD -- . ':(exclude)<docs.specsDir>/NNN-<slug>'`, the four gap
  classes and the finding format
  `` [missing|partial|contradicts|unrequested] AC<n> or file:line — what — evidence ``.
  Give it not your reasoning, your hypotheses or PLAN.md: it judges the code against the
  ACs, not against the plan. The diff leaves out the spec directory, because the
  committed spec directory holds PLAN.md. The classes: `missing` (an AC with no code),
  `partial` (an AC delivered in part), `contradicts` (code that does the opposite of an
  AC), `unrequested` (code no AC asks for).
- When the subagent reports, check each gap in the code yourself and reject a false one
  with a one-sentence reason; the subagent reads the diff cold and can be wrong.
- For each real gap, the pass adds a step at the end of the steps list in PLAN.md and you
  carry it out like any other step: test-first evidence, the self-correction loop, a tick
  and a commit. An added step for an AC adds or updates that AC's row in the AC → steps
  matrix, so its red record has a place. A gap of the class `unrequested` that no plan step
  and no `## Deviations` entry covers gets a removal step; code a plan step asked for stays.
- The escalation triggers apply to added steps as to planned ones. A step that delivers an
  AC of the SPEC stays within the SPEC's scope, so it is not a change of scope by itself;
  escalate for work beyond the SPEC, a new dependency, a migration, or a change of
  architecture or data schema.
- When the first pass added steps, run a second pass with a new fresh subagent, because
  one pass never checks the steps it added. There are at most two passes, which bounds the
  cost: a real gap after the second pass is an escalation.
- Record each pass in PLAN.md, below the last step, under a level-3 heading
  Converge pass N — <date>, followed by the gaps with your verdicts and the added steps.
  A resumed run then sees which pass ran. `implement_steps` counts the added steps.
- A resumed run with two passes recorded carries out the steps the owner decided on and
  then goes to the Definition of Done, without a third pass. A run with one recorded pass
  that added steps still runs the second pass after them.

## Self-correction loop (mandatory for every step)

You take the commands from the `Automatic verification:` section of the given
plan step — you run exactly those, not approximations (for fast iteration on one
layer there is `<verify.command>` with a scope from `verify.scopes`).

```
1. Run all the step's verification commands.
2. Everything green → end of the loop, the step is done.
3. Something red:
   a. establish the cause: an implementation bug / a wrong assumption / a mismatch with
      the plan / a product defect the test rightly found;
   b. a mismatch with the plan → escalation (Expected / Found / Why it matters);
   c. a product defect (also in code from before this spec) → fix the product, if the fix
      fits within the plan's scope and the owner decisions; otherwise escalation.
      Never fit the test to the defect — no change of test data, assertions,
      selectors, timeouts or views just so that the error stops being visible;
   d. a bug → fix it and go back to 1. — run all the commands again
      (a fix can break what already passed).
4. The fourth iteration on the same error → escalation: what you tried (a list of attempts
   with results), a hypothesis of the cause, what you need. Do not guess any further.
```

**Gate:** you go on to the next step only when the current one's verification is green. A
test you suspect is flaky is still red, and a skipped test is not green.

## Guardrails

- Do not weaken, skip (`skip`) or change existing tests or their data
  to make them pass — a conflict with a test is an escalation (unless the plan explicitly
  provides for changing the test). A test red because of a product defect is a signal to fix
  the product, not the test.
- Do not touch files unrelated to the plan — "while at it" (formatting, refactors,
  typos outside the scope) does not exist.
- Secrets and real users' data never in code, logs, commits or tests.

## Handoff

- **Run on its own:** summarise what was done, the deviations, the converge passes with
  their gaps and verdicts, the verification result and the manual scenarios; the next
  stage is `/pipeline:final-review NNN` after `/clear`.
- **Under `/pipeline:ship`:** end with the RESULT block from the stage agent contract.
