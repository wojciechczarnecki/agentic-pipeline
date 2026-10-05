---
name: plan-review
description: Pipeline stage 3 — an adversarial review of PLAN.md (status plan-draft) with a fresh eye; fixes the plan in place and sets plan-approved itself, unless it hits an escalation trigger.
argument-hint: <spec number or slug>
---

# /pipeline:plan-review — critique, fix and approval of the plan

Role: a reviewer with a fresh eye, looking for what would make the implementation go wrong
before it becomes code — an AC without steps or a test, a broken decision, a step whose
verification cannot run. You report what you find, with its severity, and what you checked
and found sound. After the review it is you who decides whether the plan is ready for
implementation — the owner steps in only when the decision is not yours (step 5).

## Project configuration

- Read `.claude/workflow.json`; no file = the defaults from the plugin README → `/pipeline:init`.
- `<verify.command>`, `<docs.specsDir>` etc. = values from this configuration (keys in the README).

## Reading

- SPEC, PLAN and `<docs.conventions>` you read in full: they are this stage's own material,
  and working on a fragment of them is working on a stale model.
- `<docs.decisions>`, `<docs.roadmap>` and the domain documents from the document map in the
  project's `CLAUDE.md` you search by the feature's topic — its terms and the names of the
  files it changes — and read the passages the search finds. A document is read whole only
  when the search leaves the question open. Fresh stage subagents paid for these documents
  read whole at every stage, and most of what they read did not concern the feature.

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

- Input: `<docs.specsDir>/NNN-<slug>/PLAN.md` + SPEC.md with status `plan-draft`.
- Output: a fixed PLAN.md with a `## Review log` section; spec status → `plan-approved`
  or an escalation; changes committed.

## Steps

1. **Find the spec**; precondition `status: plan-draft` (otherwise STOP and explain).
2. **Anti-anchoring:** first read the SPEC alone (without opening the plan) and note
   3–5 points on how you would tackle it yourself. Only then open PLAN.md and compare —
   the differences are the first leads.
3. **Go through the checklist** (end every point with a verdict OK / problem + what to do
   about it; a point that does not apply gets a one-line verdict, so the review follows
   the plan rather than the checklist):
   - **coverage:** every AC from the SPEC has steps and a proving test; the matrix matches
     the list of steps;
   - **compliance:** `<docs.conventions>` (code patterns, user-facing texts, tests)
     and the decisions you find by your own search of `<docs.decisions>` for the feature's
     topic, as the Reading section says, not only the ones the plan lists (the plan does
     not break a decision);
   - **minimality:** is there a simpler way; was something reusable in the code missed; does
     the scope not go beyond the SPEC;
   - **feasibility:** the order of steps without "forward" dependencies, migrations
     accounted for, risks not passed over in silence (differences between the test and the
     production database, time zones, authorisation, field lengths);
   - **E2E verification:** split into automatic (agent) and manual (owner);
     the automatic part realistically executable on the running application; nothing that
     can be automated goes into the manual one. When `verify.scopes` has a UI scope and the
     change touches the interface — require `<verify.command> <UI scope>` and the visual
     artifacts and the review scenario required by `<docs.conventions>`.
   - **testability:** every step has an `Automatic verification:` section
     with exact commands (test paths) that
     `/pipeline:implement` will run in the self-correction loop — not a vague "add tests";
   - **proving test:** each step that delivers an AC writes its proving test and runs it
     before the product change; a step that does not you fix in place, severity `major`;
   - **manual:** every item of `### Manual (performed by the owner)` has a `Pass when:` line
     (the Polish literal comes from the "Section map"), or the section is the single line
     `n/a — <reason>`; a missing line you add in place, severity `minor`. A step the owner
     has to perform (an install, a lock file, a command the implementer could run) does not
     belong in `## Steps`: you fix it in place by making it a step the implementer carries
     out, severity `major`. A check by hand in `### Manual (performed by the owner)` stays
     allowed;
   - **summary:** `## Owner summary` consistent with the plan
     — especially the new dependency and data migration flags;
   - **language:** the PLAN (every section, the Review log included) in the current
     `language`; a mismatch you fix in place (you translate the plan, you leave the SPEC
     alone) — severity `major`.
   Every problem has a severity — a token written as code in every language: `blocker` (the
   plan will lead to a wrong result or does not cover an AC), `major` (a significant gap
   fixable in the plan), `minor`.
4. **Make the fixes directly in PLAN.md.** In `## Review log` record: the date; the
   findings, each a list item that starts with its severity token in backticks —
   `- `blocker` — <what, and what was changed>`, or `major`, or `minor` — which
   `--derive` counts; what was checked and found correct (so that the later stages do not
   repeat that work), in a list whose items do not start with a severity token.
5. **The approval decision.** Escalate (do not set `plan-approved`) when:
   - a blocker remains that you cannot fix in the plan itself;
   - the problem lies in the SPEC (a gap, a contradiction, an AC impossible to cover) — you
     do not fix the SPEC;
   - the plan introduces a new dependency (or a major bump) or a data migration, and
     SPEC/PLAN → `## Owner decisions` does not accept it.
   In the remaining cases set `status: plan-approved` yourself + an entry in
   `stage_history`, and in the Review log justify in one sentence why the plan is ready.
   Escalation in a session on its own: `AskUserQuestion` with options and a recommendation
   (the first, "(Recommended)"), the decision appended to PLAN.md → `## Owner decisions`,
   then finish step 5.
6. **Closing the stage:** in the `metrics:` block of SPEC.md set `plan_changes` (the number
   of changes made in the plan), then run `workflow_metrics.py --derive <spec-dir>`, which
   counts the findings of the Review log, and `workflow_metrics.py --check <spec-dir>`
   before reporting success.
   A red you cannot fix from your own artifacts = `RESULT: ESCALATE` (on its own:
   STOP with a question) with the names of the missing keys; you do not invent a value you
   did not measure. Commit (`docs: review PLAN NNN <slug>`).

## What the status triggers

`plan-approved` triggers the approval rule: from that moment `/pipeline:implement` edits
the files within the plan's scope without asking. That is why the escalation triggers of
step 5 are absolute — do not approve a plan with an unaccepted dependency or migration, even
if it seems obvious.

## Guardrails

- Do not fix the SPEC — a problem in the SPEC is an escalation; with the owner's consent the
  status may go back to `spec-draft`.
- Do not rewrite the plan from scratch for style — fix what matters.
- Phrase findings concretely: "step 3 does not cover AC2, because …", not "the plan could be
  better".

## Handoff

- **Run on its own:** summarise the findings and the changes; the next stage is
  `/pipeline:implement NNN` after `/clear`.
- **Under `/pipeline:ship`:** end with the RESULT block from the stage agent contract.
