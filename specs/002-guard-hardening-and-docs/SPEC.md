---
status: implemented
stage_history:
  - "spec-draft — 2026-09-21"
  - "spec-ready — 2026-09-21"
  - "plan-draft — 2026-09-21"
  - "plan-approved — 2026-09-21"
  - "implemented — 2026-09-21"
metrics:
  started_at: 2026-09-21T17:56
  escalations: 0
  plan_steps: 8
  plan_review_blockers: 0
  plan_review_majors: 2
  plan_changes: 11
  implement_steps: 8
  implement_iterations: 0
  deviations: 1
---

# SPEC 002 — A guard worth pointing at: close the known leaks, then document it

## Goal

The command guard is the plugin's strongest claim and the least visible one: it leaks on
push refspecs built from variables, refuses a harmless read of `core.hooksPath`, and is
described only in a Polish README section. When this spec ships, the known leaks are
closed (release 0.3.4), `plugin/docs/GUARD.md` states in English what the guard defends,
what the other two layers cover and where the guard stops — with every command it cites
checked against the guard by a test — and `plugin/README.md` is in English.

## Context

- Finishes Stage 3 of `docs/ROADMAP.md`: its first item (0.3.3) is done; this spec covers
  the remaining three — the 0.3.4 guard fixes, `plugin/docs/GUARD.md` and the English
  `plugin/README.md`.
- The guard: `plugin/bin/guard` (a `sh` wrapper, fail-open without `python3`) and
  `plugin/bin/guard.py` (a shell analyser on `shlex`, 863 lines); its tests are
  `plugin/tests/test_guard.py` (675 lines, with a case-count regression check).
- Measured on 0.3.3 in this session (2026-09-21), `guard.evaluate` on each command:
  - allowed today, though they push to `main` or to an unknown target:
    `B=main; git push origin $B`, `export B=main && git push origin $B`,
    `B=main && git push origin ${B}`, `B=main; git push origin HEAD:$B`,
    `B=main; git push origin "$B"`, `git push origin $UNKNOWN`,
    `git push origin $(echo main)`, `` git push origin `echo main` ``,
    `E=; git push origin $E` (an empty value: the shell pushes the current branch),
    `B=feat/x git push origin $B` (a prefix assignment is invisible to the command's own
    arguments, so the shell sees an empty `$B` while the guard would read `feat/x`);
  - refused today, though read-only: `git config core.hooksPath`,
    `git config --global core.hooksPath`, `git config --file .git/config core.hooksPath`;
  - allowed today, and outside what a command-string analyser can close:
    `git -c alias.p=push p origin main`, a script written to a file and run
    (`bash /tmp/x.sh`), an interpreter (`python3 -c "subprocess.run(['git','push',…])"`).
- Removal targets (`rm`, `find -delete`) already resolve variables from the session
  environment and earlier assignments, not from the command's own prefix assignments, and
  refuse what they cannot resolve; `gh api -X DELETE` refuses an endpoint built from
  variables. Push refspecs are the one place that does neither.
- `plugin/README.md` (337 lines, Polish) is the single source of truth for the pipeline
  mechanics; `plugin/tests/test_readme.py` asserts Polish headings (`## Instalacja`,
  `### Strażnik komend`, `## Metryki workflow`) and Polish phrases (`brak sekcji`);
  `CLAUDE.md` points at `plugin/README.md` → Instalacja; the root `README.md` says the
  documentation is "currently in Polish". Stage skills and templates name the Polish PLAN
  heading `## Decyzje właściciela`, which the README quotes.
- `.claude/settings.json` holds this repository's `deny` rules (`git push` to `stable`,
  `gh pr merge`, `claude plugin disable|uninstall|…`) — the string rules GUARD.md compares
  the guard against.

## Context read

- `docs/ROADMAP.md` — Stage 3 has three open items (0.3.4 guard fixes; `plugin/docs/GUARD.md`
  with threat model, three layers, the deny-vs-guard table, fail-open, known limits;
  `plugin/README.md` in English, skills stay Polish until Stage 8). Stage 4 moves
  installation into `docs/INSTALL.md` and rewrites the root README, Stage 5 adds
  `protectedBranches` and blocks detaching the plugin — both stay out of this spec.
- `docs/PROJECT.md` — the guard is a functional requirement (protected branches,
  production, migrations, deletions, guardrail files); hooks run on plain `python3` with
  no network; the plugin stays project and domain agnostic.
- `docs/DECISIONS.md` — binding here: skills, agents and `plugin/README.md` stay Polish
  until translated (2026-09-17; this spec amends it for the README only); the migration
  module is deliberately Alembic-only (2026-09-20); the rulesets and what they do not
  cover (2026-09-17); `stable` kept off by `deny` rules, the guard protecting only
  `main`/`master` (2026-09-21); version grows with behaviour, patches need no eval receipt
  (2026-09-20); a rule nothing checks is not followed (SPEC 001 lesson, 2026-09-20).
- `docs/BACKLOG.md` — the positional `gh api -X DELETE` item (P3) and the migration
  generalisation (P3) stay deferred and are cited by GUARD.md as known limits; the
  `marketplace.json` guardrail item (P3) stays deferred.
- `docs/CONVENTIONS.md` — guard messages are English and name the rule and the way out;
  test mechanisms, not prose; one language per document; a behaviour change bumps the
  version and gets a `plugin/CHANGELOG.md` section; the Language section says
  `plugin/README.md` is Polish until translated — updated by this spec.
- `plugin/README.md` — the text being translated; its guard section is the source for
  GUARD.md.

## Scope

- Guard 0.3.4: push refspecs built from variables are resolved or refused; read-only
  `git config core.hooksPath` is allowed; `git -c alias.*` and persistent alias writes
  are refused.
- Release 0.3.4: version bump and a `plugin/CHANGELOG.md` section.
- `plugin/docs/GUARD.md` (English): threat model, the three layers, the deny-vs-guard
  table, fail-open by design, known limits — its command table checked against the guard
  by a test, its deny-side claims measured.
- `plugin/README.md` translated into English; its guard section becomes a summary with a
  link to GUARD.md; `test_readme.py` follows the English anchors with the same coverage.
- Follow-ups in the same PR: `CLAUDE.md` and root `README.md` references, `docs/CONVENTIONS.md`
  Language section, `docs/DECISIONS.md` rows, `docs/BACKLOG.md` entry for the evasions
  left open, `docs/ROADMAP.md` ticks.

## Out of scope

- `protectedBranches` / guarding `stable` in the guard and blocking plugin detachment —
  Stage 5 (0.4.0).
- `docs/INSTALL.md` and the rewritten root `README.md` — Stage 4; the installation section
  stays in `plugin/README.md`, translated.
- Translating skills, agents, templates, tests' Polish strings and `plugin/CHANGELOG.md`
  — Stage 8 (0.8.0). The 0.3.4 CHANGELOG section is written in Polish, like the rest of
  that file.
- Guarding scripts written to files, interpreters (`python3 -c`, `node -e`) and shell
  functions defined in earlier calls — documented as known limits in GUARD.md and entered
  in `docs/BACKLOG.md` (P3, with a trigger).
- Positional matching for `gh api -X DELETE` and a non-Alembic migration module — stay in
  `docs/BACKLOG.md` (P3) as they are.

## Requirements and acceptance criteria

All guard verdicts below are observable through `guard.evaluate` and the hook's exit code;
"refused" means exit code 2 with a reason on stderr, "allowed" means exit code 0. Unless
stated otherwise, the case runs on a feature branch with none of the named variables in
the process environment.

### Push refspecs built from variables

- [ ] AC1: A variable that resolves to `main`/`master` is refused with the existing
      push-to-main reason, in each form: `B=main; git push origin $B`,
      `B=main && git push origin $B`, `export B=main && git push origin $B`,
      `B=main; git push origin ${B}`, `B=main; git push origin HEAD:$B`,
      `B=main; git push origin "$B"`, `B=main; git push origin refs/heads/$B`.
- [ ] AC2: A refspec the guard cannot resolve is refused, and the reason names that
      refspec and asks for it to be spelled out: `git push origin $UNKNOWN`,
      `git push origin HEAD:$UNKNOWN`, `git push origin $(echo main)`,
      `` git push origin `echo main` ``, `false || B=feat/x; git push origin $B`.
- [ ] AC3: A prefix assignment does not resolve the same command's arguments:
      `B=feat/x git push origin $B` is refused (on `main` and on a feature branch alike),
      as `$B` stays unresolved for its own arguments.
- [ ] AC4: A variable that resolves to an empty value counts as no refspec:
      `E=; git push origin $E` is refused on `main` (it pushes the current branch) and
      allowed on a feature branch.
- [ ] AC5: A variable that resolves to an unprotected branch is allowed:
      `B=feat/002-x; git push origin $B`, `export B=feat/002-x && git push -u origin $B`,
      `B=feat/002-x; git push origin HEAD:$B`.
- [ ] AC6: A variable in the remote position with literal refspecs is allowed:
      `git push $REMOTE feat/002-x` (unresolved `$REMOTE`) and `R=origin; git push $R
      feat/002-x`; `git push $REMOTE main` stays refused.
- [ ] AC7: Every push case already in `test_guard.py` keeps its verdict.

### `core.hooksPath` reads

- [ ] AC8: Allowed: `git config core.hooksPath`, `git config --global core.hooksPath`,
      `git config --local core.hooksPath`, `git config --show-origin core.hooksPath`,
      `git config --file .git/config core.hooksPath`, and — as today —
      `git config --get core.hooksPath`, `git config get core.hooksPath`.
- [ ] AC9: Still refused with the `core.hooksPath` reason: `git config core.hooksPath x`,
      `git config core.hooksPath ""`, `git config --global core.hooksPath x`,
      `git config --file .git/config core.hooksPath x`, `git config set core.hooksPath x`,
      `git config --unset core.hooksPath`, `git config --unset-all core.hooksPath`,
      `git config unset core.hooksPath`, `git -c core.hooksPath=/dev/null push origin feat/x`.

### Git aliases

- [ ] AC10: An alias defined on the command line is refused, with a reason saying an alias
      cannot be verified and to run the git command itself:
      `git -c alias.p=push p origin main`, `git -c alias.x='!git push origin main' x`,
      `git -c Alias.P=push P origin feat/x` (the key is case-insensitive).
- [ ] AC11: Writing a persistent alias is refused with the same reason, in any scope:
      `git config alias.p push`, `git config --global alias.p push`,
      `git config set alias.p push`; reading one is allowed: `git config alias.p`,
      `git config --get-regexp alias`.
- [ ] AC12: Other `-c` keys are unaffected: `git -c user.name=x commit -m y` on a feature
      branch is allowed.

### Release 0.3.4

- [ ] AC13: `plugin/.claude-plugin/plugin.json` has version `0.3.4`; `plugin/CHANGELOG.md`
      opens with a `## 0.3.4` section (Polish, like the file) that lists AC1–AC12 as fixes
      and names the consumer impact (`wpływ na konsumenta`) — the refusals that are new.

### `plugin/docs/GUARD.md`

- [ ] AC14: `plugin/docs/GUARD.md` exists, is in English and has these sections: threat
      model (what the guard defends against — agent mistakes and shortcuts — and what it
      does not — deliberate evasion; it is best effort, not a sandbox); the three layers
      (guard → `pre-push` → GitHub rulesets) with, for each, what it covers, when it runs
      and how it is bypassed; the deny-vs-guard table; fail-open by design (missing
      `.claude/workflow.json`, invalid configuration, missing `python3` → a warning on
      stderr and exit 0); known limits.
- [ ] AC15: Known limits name at least: Alembic-only migrations; only `main`/`master` are
      protected branches (the `stable` channel rests on `deny` rules until Stage 5); the
      guard sees only the Bash tool, not Edit/Write; scripts written to files,
      interpreters and shell functions; `gh api -X DELETE` matched by segment name — each
      with its `docs/BACKLOG.md` entry or roadmap stage where one exists.
- [ ] AC16: The deny-vs-guard table has at least five rows; each row gives a command, the
      string `deny` rule it gets past, and the guard's reason. Every command in the table
      is refused by the guard — `plugin/tests` parses the table from GUARD.md and runs each
      command through the guard, so a guard change that lets a row through, or a row added
      without a refusal, turns the suite red.
- [ ] AC17: Every row's deny-side claim was measured with `claude -p --settings` holding
      that rule, and GUARD.md records the date and the Claude Code version of the
      measurement; a command the measurement shows the `deny` rule does catch is not in
      the table.
- [ ] AC18: GUARD.md names no consumer project or domain (`test_no_domain_references.py`
      covers it as a file under `plugin/`).

### `plugin/README.md` in English

- [ ] AC19: `plugin/README.md` contains no Polish text outside code spans and code blocks
      (a test: no Polish diacritics outside backticks and fences); quoted literals that
      skills and templates produce — e.g. `## Decyzje właściciela` — stay verbatim inside
      code spans.
- [ ] AC20: The README keeps its sections (installation, commands and agents, project
      configuration, formatting, guard, pipeline mechanics with statuses, `RESULT`
      contract and escalation triggers, workflow metrics with `--check`, changelog); status
      names, `RESULT` fields, metric keys, configuration keys and their defaults are
      unchanged.
- [ ] AC21: The guard section is a summary of a few sentences with a link to
      `docs/GUARD.md` and still states the Alembic-only migration scope with
      `migrations.command` and `migrations.localHosts`; a test asserts the link.
- [ ] AC22: `test_readme.py` asserts the English anchors with the same coverage as today
      (every configuration key with its default, the migrations row, installation content,
      every metric counter, the guard's migration scope); `CLAUDE.md` points at the English
      installation heading; the root `README.md` no longer says the documentation is in
      Polish.

### Project documents

- [ ] AC23: `docs/DECISIONS.md` gains rows for: `plugin/README.md` in English ahead of the
      skills (amending 2026-09-17); push refspecs resolved like removal paths and refused
      when unresolvable; aliases refused; GUARD.md's command table checked by a test and
      its deny side measured. `docs/CONVENTIONS.md` → Language reflects the English README.
- [ ] AC24: `docs/BACKLOG.md` gains a P3 Guard entry for scripts in files, interpreters
      and shell functions, with a trigger (e.g. the first session seen reaching a guarded
      action through one of them).
- [ ] AC25: The three open Stage 3 items in `docs/ROADMAP.md` are ticked with a link to
      this spec; `bash scripts/check.sh` is green.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|---|---|---|
| One spec for the rest of Stage 3 | separate specs for 0.3.4, GUARD.md and the README | GUARD.md describes the guard after the fixes, and the English README's guard section links to it instead of duplicating it — split, the three would have to be reconciled across PRs |
| An unresolvable push refspec is refused | resolving known variables only, letting the rest through | Removal paths and `gh api -X DELETE` endpoints already work this way, and a push cannot be taken back; the cost is a refusal that asks to spell the refspec out |
| Shell semantics for expansion: prefix assignments do not count for the command's own arguments, an empty value disappears | expanding with every assignment in sight | `B=feat/x git push origin $B` and `E=; git push origin $E` push the current branch in a real shell; the guard must judge what the shell runs |
| `git -c alias.*` and persistent alias writes refused; scripts, interpreters and functions documented as limits | documenting aliases only; trying to close every evasion | Aliases are as cheap to block as `-c core.hooksPath`; scripts and interpreters cannot be analysed from a command string, and the guard is best effort by definition, with `pre-push` and the rulesets behind it on `main` |
| GUARD.md's command table is parsed and checked by a test; its deny side measured with `claude -p --settings` | hand-copied cases in `test_guard.py`; deny behaviour inferred from documentation | A document nothing checks drifts (SPEC 001 lesson); `deny` matching is Claude Code's behaviour, not ours, and may have changed (e.g. compound commands split before matching) |
| README guard section: summary + link | full translation beside GUARD.md | One place for the rules; two copies drift |

## Owner decisions

- No new dependencies (runtime or dev) and no data migrations — accepted up front as the
  shape of this spec.
- A one-off measurement of `deny` rules with `claude -p --settings` in the implementer's
  session, on the subscription (no API console) — accepted.
- Scope: the whole rest of Stage 3; unresolvable refspecs refused; aliases blocked, other
  evasions documented and backlogged; GUARD.md table checked by a test; README guard
  section as summary + link — all chosen by the owner on 2026-09-21.
- Approved on 2026-09-21: a variable remote with literal refspecs passes (AC6); persistent
  alias writes are refused (AC11); the deny-vs-guard table has at least five rows (AC16).

## Open questions (non-blocking)

- None.
