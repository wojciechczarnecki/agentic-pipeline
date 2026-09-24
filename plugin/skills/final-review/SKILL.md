---
name: final-review
description: Pipeline stage 5 — the final code review of the feature branch (status implemented). Report mode — three independent perspectives as parallel subagents and a findings report; apply mode — fixes per the owner's decisions, opening the PR, green CI and only then status done.
argument-hint: <spec number or slug> [report|apply]
---

# /pipeline:final-review — the final review of a feature

Role: the final reviewer. The code was made in another session — you assess it with a fresh
eye, from three perspectives that do not see one another's conclusions. You fix only after
the owner's decision: this is the second human gate in the pipeline.

Modes: **`report`** (the default) and **`apply`**. In a session on its own you run both in
turn with the owner's question in between; in `/pipeline:ship` each mode is a separate run.

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

- Input: `<docs.specsDir>/NNN-<slug>/` with status `implemented`; the feature branch.
- Output of `report`: the report in `## Final review` in PLAN.md (committed).
- Output of `apply`: the accepted fixes made, an open PR with green CI, spec status →
  `done` (only after green CI).

## Report mode

1. **Precondition** `status: implemented`. `git fetch origin`; the material:
   `git diff --stat origin/main...HEAD` (the full diff and the full versions of the files
   are read by the perspectives).
2. **Three perspectives — in parallel**, as separate subagents (the `Agent` tool, all
   three in one message). Each gets: the spec path, the diff command, its own
   perspective and the finding format. It does not get the others' conclusions or your
   hypotheses. The review always runs all three perspectives, for a small change as for a
   large one: independence is the method, and three readers of a small diff cost little.
   Each perspective reports every finding with its severity, because a reviewer told to
   report less finds less.
   - **Compliance with the SPEC/PLAN:** for every AC the evidence — the file/test that
     delivers it (the AC → evidence matrix); the plan's steps ticked with good reason;
     `## Deviations` justified; nothing outside the scope got into the branch; every AC
     row of the AC → steps matrix has its red record in the fourth column or a `manual` /
     `n/a` mark (a matrix without the fourth column, from a plan carried out before 0.7.0,
     is not a finding).
   - **Quality and maintainability:** the `/code-review` skill on the diff (bugs, edge
     cases, security); on top of that compliance with `<docs.conventions>` (code patterns,
     user-facing texts only through the mechanism named there, style and line length limit)
     and consistency with the existing patterns (pagination, dependencies, error handling,
     test structure).
   - **Tests:** are the key paths and edge cases covered (authorisation errors, missing
     resource, validation, empty lists, duplicates, length limits)? are the assertions
     concrete — not just the status code where the content matters? do the interface tests
     use the same text keys as the code? When `verify.scopes` has a UI scope and the change
     touches the interface — require in PLAN.md an entry on `<verify.command> <UI scope>`
     and on the visual artifacts looked at and the review scenario required by
     `<docs.conventions>`.
   The finding format from a perspective:
   `[blocker|worth-fixing|nit] file:line — scenario (input → wrong behaviour) — fix`.
   Severities are tokens written as code in every language, like metric keys.
3. **Merge and verify.** Merge duplicates. Check every finding yourself in the code —
   reject the false ones with a one-sentence reason. Set the final severity by the real
   risk. Then the report keeps at most five `nit` findings, the ones with the highest risk
   or maintenance cost; the rest are left out and only counted, in the sentence
   `Left out: N nit findings` (also with N = 0, so the line is always there). A long list
   of nits buries the findings that matter, and the count keeps the report honest.
4. **Write the report** in `## Final review` in PLAN.md: the date; the AC → evidence matrix;
   the findings with ids `F1…Fn` (severity, file:line, scenario, fix); the rejected ones
   with a reason; the `Left out: N nit findings` sentence. The report's length follows the
   findings: a review with none is the matrix and one line. In the `metrics:` block of
   SPEC.md: `final_review_blockers`, `final_review_worth_fixing`, `final_review_nits`;
   `final_review_nits` counts the reported nits, not the left-out ones, so the `--check`
   balance holds.
   The flat `metrics:` block: integer counters, times `%Y-%m-%dT%H:%M`; before reporting
   success `workflow_metrics.py --check <spec-dir>`.
   A red you cannot fix from your own artifacts = `RESULT: ESCALATE` (on its own:
   STOP with a question) with the names of the missing keys; you do not invent a value you
   did not measure. Commit (`docs: add final review of NNN <slug>`).
5. **Decisions:**
   - a session on its own → show the findings table and ask the owner (`AskUserQuestion`,
     in the session language; recommendation: accept `blocker` and `worth-fixing`, reject
     `nit`); record the decisions in PLAN.md → `## Owner decisions` and go on
     to apply mode;
   - `/pipeline:ship` → end with the RESULT block; its SUMMARY carries the findings table
     and the `Left out: N nit findings` sentence; the decisions are collected by the
     orchestrator.

## Apply mode

1. **Take the decisions** from PLAN.md → `## Owner decisions` (the entry
   on the final review).
   No entry → escalation, do not guess.
2. **Fixes:** make the accepted ones, repeat the full verification (`<verify.command>`), add
   to the report what was fixed (id → change). In the `metrics:` block: `findings_accepted`,
   `findings_rejected`; a finding deferred to `<docs.backlog>` counts as
   `findings_rejected` (reason: "backlog"), otherwise the `--check` balance does not add up.
3. **PR** — the spec status stays `implemented`:
   - `<docs.roadmap>` ticked, `<docs.decisions>` if applicable; `<docs.backlog>`
     updated: new items with a priority and a trigger, delivered ones removed,
     items whose trigger has fired listed in the report for the owner;
   - commit (`fix: address final review of NNN <slug>`, and with no code changes —
     `docs: record final review of NNN <slug>`), `git push`;
   - the PR already exists (`gh pr view --json url`, e.g. when resuming after an escalation)
     → do not create a second one; otherwise
     `gh pr create --base main --title "<type>: <English message after the squash>" --body-file <file>`
     — the PR title in English in the commit format (type + imperative mood), because after
     the squash it becomes the commit message; the PR description in the language from
     `language`, the description file in the scratchpad; the description: the goal (from the
     SPEC), the main changes, the verification result, the spec metrics, the manual
     scenarios to check before the merge; the footer per the session's instructions.
4. **Wait for CI** — always; in a repository without branch protection you are the only
   gate: `gh pr checks <nr> --watch`. A red job → the self-correction loop
   from `/pipeline:implement` (commit, push, waiting again; the 4th iteration on the same
   error = escalation). A product defect found by a test whose fix goes beyond the
   accepted decisions → escalation; never fit a test or test data to the defect.
   On escalation the status stays `implemented`, and the PR is not reported as ready to
   merge. **A test green only after a retry (flaky)** does not block the PR, but it does not
   vanish: add it to `<docs.backlog>` (the test name, the CI run number, the symptom, the
   trigger) and list it in the report. The entry goes into the closing commit of step 5 —
   otherwise the trace is lost after the merge.
5. **Closing — only with green CI:** `status: done` + an entry in `stage_history`;
   `metrics.finished_at` (`date +%Y-%m-%dT%H:%M`). Before `done` run
   `workflow_metrics.py --check <spec-dir>` — while it ends with an error, `done` does not
   happen; a red that cannot be fixed = `RESULT: ESCALATE`. A counter measured as zero you
   record as `0` — that is a measurement, not an invented value.
   Commit (`docs: close SPEC NNN <slug>`), `git push`, `gh pr checks <nr> --watch` again
   — the PR's last commit must have green CI as well. A red after the status commit alone is
   instability, not a defect: re-run the run (`gh run rerun <id> --failed`), do not revert
   the status.
6. Give the PR link, the CI status and the link to the run with the visual artifacts
   (`gh pr checks <nr> --json name,workflow,link` — `link` leads to the run); when
   you edit the PR description, include the same there. The owner does the merge.

## Guardrails

- In report mode you fix nothing — the report first, changes after the decision.
- `done` means "a PR with green CI waits for the merge" — you do not set it earlier.
- Do not report cosmetic nits as blockers — the severity has to match the real risk.
- You do not merge the PR (also enforced by this plugin's command guard).

## Handoff

- **Run on its own:** the PR link + a reminder of the manual scenarios;
  the squash merge is done by the owner, the next feature starts with `/pipeline:idea`.
- **Under `/pipeline:ship`:** end with the RESULT block from the stage agent contract.
