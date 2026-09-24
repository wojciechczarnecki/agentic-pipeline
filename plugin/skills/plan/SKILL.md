---
name: plan
description: Pipeline stage 2 — a technical implementation plan for a feature based on SPEC.md (status spec-ready). Writes PLAN.md with steps and exact verification commands.
argument-hint: <spec number or slug, e.g. 001>
---

# /pipeline:plan — SPEC → implementation plan

Role: architect. The SPEC says what and why — you decide how. The result is a plan that
another agent will carry out in a fresh session without guessing: every step has a defined
feedback signal (exact verification commands), because `/pipeline:implement` builds its
self-correction loop on them.

The plan has two readers: the **agents** of the later stages (the whole content — detailed,
unambiguous) and the **owner** (only `## Owner summary` — they read it on escalation and
with the final review report; they do not approve the whole plan).

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

- Input: `<docs.specsDir>/NNN-<slug>/SPEC.md` with status `spec-ready`.
- Output: `<docs.specsDir>/NNN-<slug>/PLAN.md` committed on the lane branch;
  spec status → `plan-draft`.

## Steps

1. **Find the spec.** The argument gives the number/slug; without an argument list
   `<docs.specsDir>/*/SPEC.md` with status `spec-ready` and ask the owner which one to take.
2. **Precondition:** `status: spec-ready`. Any other status → STOP; explain which pipeline
   stage is missing. Check the branch (`git branch --show-current`): you work on the lane
   branch `feat/NNN-<slug>`; if it does not exist (e.g. the SPEC was committed to `main`) —
   create it: `git switch main && git pull --ff-only && git switch -c feat/NNN-<slug>`
   (in parallel work: a worktree in the directory from `worktree.dir`).
3. **Gather context:** the SPEC in full (including `## Owner decisions`);
   `<docs.conventions>`; `<docs.decisions>`; domain documents
   from the document map in the project's `CLAUDE.md` (under the conditions in the map); the
   code of the area — read the files the plan will change in full (no limit/offset). Note
   the existing patterns to reuse with concrete paths (e.g. pagination in a specific API
   module, shared test fixtures, error handling in the API client).
4. **Design the approach:** minimal, following the conventions, covering all
   ACs. Where a real choice exists, consider ≥2 variants; write the chosen one into the plan
   + one sentence on why.
5. **Write PLAN.md** from the template loaded for the current `language` (the
   "PLAN.md template" section), in the language from `language` — also when SPEC.md is in
   another language (e.g. written before `language` changed); you do not translate or change
   the SPEC. Steps small (≤ ~1 h of work) and closed: each has an `Automatic verification:`
   section with exact commands (test paths,
   not a vague "add tests") — this is the contract for the self-correction loop of
   `/pipeline:implement`. Each step that delivers an AC writes and runs its proving test
   before the product change, so that `/pipeline:implement` can record the test red
   before the change makes it pass. An order without "forward" dependencies; a data
   migration always
   as a separate step. Split the end-to-end verification into automatic (done by the agent)
   and manual (done by the owner) — only what cannot be
   automated goes into the manual one. When `verify.scopes` has a UI scope and the change
   touches the interface — plan in the automatic verification `<verify.command> <UI scope>`
   and looking at the visual artifacts and updating the review scenario required by
   `<docs.conventions>`.
6. **AC → steps matrix:** every AC must have steps that deliver it and a test that
   proves it. An AC impossible to cover → escalation (a gap in the SPEC); do not patch the
   SPEC yourself. The fourth column stays empty for `/pipeline:implement`, which records
   the red run there. You mark a row `manual` (the owner checks it by hand) or
   `n/a — <reason>` (for example `n/a — kept behaviour`) only when no test can be red
   before the change.
7. **Fill in `## Owner summary`** at the end, when the plan
   is ready. The "new dependency" and "data migration" flags must be true — on them
   depends whether the plan review can approve it without the owner.
8. **Closing the stage:** in SPEC.md `status: plan-draft` + an entry in `stage_history`; in
   the `metrics:` block set `started_at` and `escalations: 0` (if missing;
   `date +%Y-%m-%dT%H:%M`) and `plan_steps`.
   The flat `metrics:` block: integer counters, times `%Y-%m-%dT%H:%M`; before reporting
   success `workflow_metrics.py --check <spec-dir>`.
   A red you cannot fix from your own artifacts = `RESULT: ESCALATE` (on its own:
   STOP with a question) with the names of the missing keys; you do not invent a value you
   did not measure. Commit (`docs: add PLAN NNN <slug>`). Do not implement anything.

## PLAN.md template

You load the template with the `Read` tool — one file, chosen by the current `language`,
not by the language of the SPEC:

- `pl` → `${CLAUDE_PLUGIN_ROOT}/templates/PLAN.pl.md`;
- `en`, a missing key or any other value → `${CLAUDE_PLUGIN_ROOT}/templates/PLAN.en.md`.

You load only that one file. You do not translate the template or merge it with the other
one — the PLAN has exactly its headings. A failed read of the template → you follow the
"Section map" section (stop with the message; you do not rebuild the template from memory).

## Guardrails

- Do not change the content of the SPEC (apart from the `status` field, `stage_history` and
  the `metrics` block).
- Do not add scope beyond the SPEC (gold-plating) — write "while at it" ideas
  as proposals for `<docs.backlog>` in the stage summary, not as plan steps.
- Code in the plan only where precision requires it (signatures, the shape of a schema) —
  the plan is not the implementation.

## Handoff

- **Run on its own:** the plan is ready (status `plan-draft`); the next stage is
  `/pipeline:plan-review NNN` after `/clear` — the reviewer is to assess the plan with a
  fresh eye.
- **Under `/pipeline:ship`:** end with the RESULT block from the stage agent contract.
