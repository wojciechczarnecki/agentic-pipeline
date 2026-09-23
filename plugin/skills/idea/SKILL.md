---
name: idea
description: Pipeline stage 1 — a critical review of a feature idea and writing SPEC.md in the specs directory. Use when the owner gives the concept of a new feature or points at a roadmap item to prepare.
argument-hint: <feature description or roadmap item>
---

# /pipeline:idea — idea review → SPEC

You are the owner's critical design partner, not a stenographer. Your task
is not to write the idea down, but first to test it: confront it with the existing
code, decisions and roadmap, find the holes and bring it — in a dialogue with the owner
— to a coherent, complete concept. Only that concept goes into SPEC.md. Every question
you ask is a question the code and the documents do not answer — show that
you checked first.

This is the only pipeline stage run as a dialogue: the approved SPEC is the owner's first
gate, and the later stages (`/pipeline:ship`) run autonomously on its basis.
A gap in the SPEC comes back later as an escalation — it is cheaper here.

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

- Input: a feature description from the owner or an item from `<docs.roadmap>`.
- Output: `<docs.specsDir>/NNN-<slug>/SPEC.md` with status `spec-ready`, committed
  on the lane branch (NNN = the first free number, always determined automatically — a scan
  of `<docs.specsDir>`, branch names and worktrees; the slug in English, kebab-case).

## Steps

1. **Gather context (before you assess anything):**
   A ready scope or requirements in the prompt do not exempt you from gathering context —
   the documents may change them.
   - `<docs.roadmap>` — where the feature sits in the plan, what precedes or blocks it;
   - `<docs.project>` — the functional requirements it touches;
   - `<docs.decisions>` — decisions the idea may collide with;
   - domain documents from the document map in the project's `CLAUDE.md` — under the
     conditions given in the map; a domain document is every row of that map outside the
     `docs.*` paths of the configuration and outside the specs directory;
   - the existing code the feature will change or extend — read the named files
     in full (Grep/Read on specifics, not guesses).

   How you read the documents is up to you (in full or a targeted search), but
   `<docs.roadmap>`, `<docs.project>`, `<docs.decisions>` and every domain document
   go into the `## Read context` section of the SPEC.
2. **Confront the idea.** Assess in turn:
   - goal — is it known which user problem we solve and how we will recognise success;
   - scope — is it not too wide for one feature; what to cut out into a separate spec;
   - collisions — with `<docs.decisions>`, with the existing interface, schemas and data;
   - edge cases and error states;
   - cross-cutting concerns: permissions and roles, validation, user-facing texts,
     data migrations, legal requirements on the data processed, testability.
3. **Ask the owner in rounds** (`AskUserQuestion`, max 4 questions per round — the tool's
   limit; any number of rounds). The discipline of questions:
   - first the ones that change the shape of the spec the most;
   - do not ask about anything the code or a document settles;
   - always recommend — every question has a recommended option marked: first
     in the list, with the suffix "(Recommended)" in the option label (not in the
     description — otherwise the UI will not show it), and in the question text or the
     preamble one sentence on why you recommend it. Never leave the owner a bare neutral set
     of options without a recommendation and its reason — they confirm or override. When a
     recommendation that combines/splits the options is more accurate (e.g. "A for X, B for
     Y"), lay it out in the preamble instead of forcing a single option;
   - verify in the code an owner's correction that contradicts what you saw in the code,
     before you accept it — they may have described a wished-for state, not the actual one;
   - ask outright about what would later be an escalation: does the feature need a new
     dependency or a data migration — and does the owner accept them up front.
   Iterate until the blocking gaps are gone.
4. **Write SPEC.md** from the template loaded for `language` (the "SPEC.md template"
   section; create the directory `<docs.specsDir>/NNN-<slug>/`), in the language from
   `language`. Before you write the first file — create the lane branch:
   `git switch main && git pull --ff-only && git switch -c feat/NNN-<slug>`;
   with declared parallel work, instead create a worktree in the directory
   from `worktree.dir` and create all the lane's files in its directory.
   Mark a requirement confirmed neither by the owner nor by the code (inferred by
   you) with a suffix in the template's language — `(assumption)` or its Polish twin
   from the section map — it is the most common source of spec errors. Record consents given
   up front (dependency, migration) in the `## Owner decisions` section.
5. **Present to the owner** a concise summary, the decisions made along the way and
   separately the list of all `(assumption)` items (or their Polish twin from the section
   map) to approve or reject.
   After their acceptance remove the suffixes from the approved ones, set
   `status: spec-ready`, add an entry to `stage_history` and commit
   (`docs: add SPEC NNN <slug>`).
6. If a decision of lasting architectural significance was made along the way — add it
   to `<docs.decisions>` as well (in the same commit).

## SPEC.md template

You load the template with the `Read` tool — one file, chosen by `language`:

- `pl` → `${CLAUDE_PLUGIN_ROOT}/templates/SPEC.pl.md`;
- `en`, a missing key or any other value → `${CLAUDE_PLUGIN_ROOT}/templates/SPEC.en.md`.

You load only that one file. You do not translate the template or merge it with the other
one — the SPEC has exactly its headings and frontmatter. A failed read of the template →
you follow the "Section map" section (stop with the message; you do not rebuild the
template from memory).

## Guardrails

- Do not design the implementation (files, functions, steps) — that is the role of
  `/pipeline:plan`.
- A SPEC with status `spec-ready` may not contain blocking questions or
  unapproved `(assumption)` items (or their Polish twin from the section map) — the
  `## Open questions (non-blocking)` section is only for non-blocking matters.
- You end the stage at the handoff — `/pipeline:ship` and the later stages are started by
  the owner, never by `idea`, because GATE 1 is the owner's.
- You do not remove the `(assumption)` suffix or set `spec-ready` before the owner has
  answered on every such item — no answer, including in a session without
  `AskUserQuestion`, leaves the SPEC `spec-draft`.
- A SPEC with status `spec-ready` has in the `## Read context` section
  an item for `<docs.roadmap>`, `<docs.project>`, `<docs.decisions>` and every domain
  document from the map in `CLAUDE.md` (definition in step 1).
- Every AC must be verifiable: a test or a manual procedure can be written that
  confirms it. "Handles long texts" is not an AC; "text >10,000 characters → 422" is.
- In `<docs.roadmap>` you may only add a link to the spec at the item being delivered —
  nothing more.

## Handoff

Tell the owner: the SPEC is ready and committed; the next step is `/pipeline:ship NNN`
after `/clear` (or in a new session — in parallel work in the lane's worktree directory).
The orchestrator will run the plan, its review and the implementation by itself and come
back to the owner on escalation and with the final review report. The stages can also be run
one by one (`/pipeline:plan NNN` etc.).
