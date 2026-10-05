# Roadmap

Tick an item in the same PR that delivers it, after green verification — the merge makes it
true, and the roadmap must not lie.

## Stage 1 — Standalone public repository

- [x] Import of the plugin 0.2.0 from the owner's private project repository (tag `pipeline--v0.2.0`)
- [x] Project scaffold: documents, configuration, dev tools and CI (the manual eval workflow was removed on 2026-09-20; `claude plugin eval` runs locally — `docs/DECISIONS.md`)
- [x] Post-import cleanup: the marketplace source declares the release tag, what the GitHub
      rulesets do and do not enforce is written down, project documents de-duplicated
      (each machine still needs the one-time marketplace re-registration from `CLAUDE.md`)

## Stage 2 — Rules the agent executes

- [x] Rules where the agent executes them, and install instructions that match reality:
      the metrics format in every stage skill plus `workflow_metrics.py --check`, the stage
      contract in `plugin/agents/*.md`, slimmed configuration and visual-artifact prose, and
      a git + HTTPS marketplace source pinned with `ref`
      (`specs/001-executable-rules-and-release-pinning/SPEC.md`)
- [x] 0.3.1: the checker runs without a permission prompt — stage skills call it through
      `PATH` and the allow rule is `Bash(workflow_metrics.py *)`, since permission rules do
      not substitute `${CLAUDE_PLUGIN_ROOT}` (`docs/DECISIONS.md`, 2026-09-21)
- [x] 0.3.1: releases reach consumers through the `stable` channel and a single
      `--scope user` install, updated without re-registering the marketplace
      (`docs/DECISIONS.md`, 2026-09-21)
- [x] 0.3.2: projects declare only the marketplace, not `enabledPlugins: true`, so no
      session installs a `--scope project` duplicate beside the user install
      (`docs/DECISIONS.md`, 2026-09-21)

## Stage 3 — A guard worth pointing at

The guard is the plugin's strongest part and the least visible one. Fix what is known to
leak, then document it.

- [x] 0.3.3 (patch): findings from the first full consumer run — `gh api -X DELETE`
      is blocked only on the owner's ground (the rest, e.g. Actions artifacts, passes), a
      refused compound command names the blocked parts, `final-review` takes the run link
      from `gh pr checks`, and only the orchestrator bumps `escalations`
- [x] 0.3.4 (patch): guard fixes (`specs/002-guard-hardening-and-docs/SPEC.md`)
      - a variable in a push refspec is resolved or blocked, like a path for `rm` —
        `B=main; git push origin $B` (also with `export` and `&&`) passes today; measured
        2026-09-21 on 0.3.2, server-side the `main` ruleset still stops it
      - read-only `git config core.hooksPath` (no value) is allowed
      - git aliases are refused: `git -c alias.*` and persistent alias writes
- [x] `plugin/docs/GUARD.md`: threat model, the three layers (guard → `pre-push` → GitHub
      rulesets) and what each covers, a table of commands a string `deny` rule lets through
      and the guard stops, fail-open by design, and the known limits (Alembic-only
      migrations, best effort rather than a sandbox) (`specs/002-guard-hardening-and-docs/SPEC.md`)
- [x] `plugin/README.md` in English (documentation only; skills stay Polish until Stage 8) (`specs/002-guard-hardening-and-docs/SPEC.md`)

## Stage 4 — Portfolio storefront

Documentation only, no behaviour change. The private consumer project stays unnamed
(`docs/DECISIONS.md`, 2026-09-17).

- [x] Root `README.md` rewritten for a reader who has never seen the project under the
      display name *Spec-Driven Workflow*: one-line pitch, a mermaid diagram of the
      pipeline and its three gates, the guard's refusal as a tested text block, *What sets
      it apart* (other tools plan, this plugin enforces; no competitor named), quickstart, badges (CI, licence,
      version), a *What's deliberately not here* section, links to `GUARD.md`, the
      metrics and the install guide. The claim is the command guard and the checked
      metrics, not hook-enforced gates as such — SpecForge and gate-oriented-sdd enforce
      approval gates with hooks too, but neither guards shell commands (checked
      2026-09-21) (`specs/003-portfolio-storefront/SPEC.md`)
- [x] *Requirements & opinions* in the root `README.md`: GitHub with `gh`, squash merges,
      rulesets, `python3` on the machine, Alembic-only migration guarding — who the
      plugin is for and who it is not for
- [x] `plugin/docs/INSTALL.md`: installation, the `stable` channel, updates, the one-time
      migration and the known traps (scope, `enabledPlugins`, commands stripping
      `.claude/settings.json`) moved out of `plugin/README.md`; both READMEs keep a short
      install and a link
- [x] `CONTRIBUTING.md` and `SECURITY.md` at the repository root
- [x] GitHub Releases for the six `pipeline--v*` tags, notes from `plugin/CHANGELOG.md`
      (the release procedure in `docs/CONVENTIONS.md` and `CLAUDE.md` already includes the
      GitHub Release step)
- [x] The GitHub *About* description and topics checked against the root `README.md`
- [x] Owner only, in the GitHub settings: the repository pinned on the owner's profile and
      a social preview image

## Stage 5 — A release gate to trust, and a guard that guards itself

Every minor release is gated on a green eval receipt, so the gate has to mean something
before the first minor ships.

- [x] Evals stable enough to gate on: `runs: 3` with a majority score, or sharper criteria —
      decided by measurement (was `docs/BACKLOG.md` P2; its trigger fires with this stage)
      (`specs/004-eval-gate-and-canary/SPEC.md`)
- [x] Behavioural evals for the stage skills, which have none today (the three cases cover
      `init` and the guard): `implement` escalates instead of weakening a failing test,
      `plan-review` escalates on a dependency the owner did not accept, `final-review`
      finds a planted defect and rejects a planted false positive
      (`specs/004-eval-gate-and-canary/SPEC.md`)
- [x] Pre-release canary, measured and documented: how to run an unreleased plugin in a
      consumer project beside the `--scope user` install without moving `stable`
      (`specs/004-eval-gate-and-canary/SPEC.md`)
- [x] 0.4.0: the guard protects configurable release-channel branches
      (`protectedBranches` in `.claude/workflow.json`), replacing the `deny` rules on
      pushes to `stable` in `.claude/settings.json` (`specs/005-guard-guards-itself/SPEC.md`)
- [x] 0.4.0: the guard blocks detaching the plugin (`claude plugin disable|uninstall`,
      `claude plugin marketplace remove`) — with a `--scope user` install one command
      removes the guard from every project on the machine
      (`specs/005-guard-guards-itself/SPEC.md`)
- [x] The owner moved Stage 8 ahead of Stage 6: the canary and the eval gate from this
      stage are what make the translation safe, and Stages 6–7 would otherwise rewrite
      Polish skills that get translated right after. The cost is two more releases before
      the pipeline improvements; stage numbers are kept (`docs/DECISIONS.md`, 2026-09-22)
      (`specs/004-eval-gate-and-canary/SPEC.md`)

## Stage 8 — English everywhere, Polish on request

The repository becomes English end to end; a consumer with `"language": "pl"` keeps Polish
specs, plans, reports and project documents. `language` governs what the pipeline writes
into the repository — specs, plans, project documents, PR descriptions; commit messages,
PR titles and branch names are English regardless; the conversation in the terminal
(questions, escalations, summaries) follows the Claude Code session language, not
`language`. Two releases, in this order — translating first would silently switch a
Polish consumer's plans to English, since today only `idea` names `language`. Each one
goes through the pre-release canary on a Polish consumer before `stable` moves.

- [x] 0.5.0: language made explicit, skills still Polish — every stage writes its
      artefacts and PR bodies in `language`, commits and PR titles in English, and talks
      to the owner in the session language; spec and plan always in the current
      `language`; `SPEC`/`PLAN` templates per language (`*.en.md`, `*.pl.md`) with a
      structure-parity test; section headings mapped across languages and finding
      severities as fixed English tokens, so older specs keep working; `language`
      limited to `en`/`pl`, default `en`; `/pipeline:init` asks for the language first
      and generates `CLAUDE.md` and `docs/*` in it from per-language templates
      (`specs/006-language-made-explicit/SPEC.md`)
- [x] 0.6.0: `idea` and `plan` read their template with `Read` instead of carrying both
      languages inline (0.5.0 owner decision C) — one source, one language in context, and
      the precondition for Polish living only in `*.pl.md`. A skill gets no free read of its
      own plugin's files (headless probe, 2026-09-23: refused from the skill's directory,
      the install cache and a `--plugin-dir` clone); the narrow allow rule
      `Read(~/.claude/plugins/cache/wcz-tools/pipeline/**)` lets the read through and
      nothing else. It needs the rule in `plugin/templates/settings.json` and the owner's
      user settings, a consumer-impact line for existing consumers, a guard warning when the
      rule is missing (a stage subagent cannot answer the prompt and would stall), and a
      separate rule for a `--plugin-dir` canary (`specs/006-language-made-explicit/PLAN.md`,
      deviation D1). The same read replaces the Polish and English headings the skills
      quote today: the section map moves out of `plugin/README.md` into a file of its own
      (`plugin/templates/sections.md`, the table alone; the README links to it, and the
      map-to-template parity test follows it), every stage reads it with `Read`, and a
      failed read stops the stage (`RESULT: ESCALATE`) — a missing template is visible, a
      missing map would silently miss `## Decyzje właściciela`. Lands before the
      translation, so the skills can drop the Polish headings when they are translated
      (`specs/007-read-templates-at-run-time/SPEC.md`)
- [x] 0.6.0: skills, agents and tests translated into English (`plugin/CHANGELOG.md` already
      is, since 0.3.4), with an eval case on `"language": "pl"`: a Polish SPEC whose
      `## Decyzje właściciela` accepts a new dependency, and `plan-review` approves the plan
      without escalating (the mirror of `plan-review-escalates-on-dependency`) — it fails if
      the section map is misread (the eval case landed with SPEC 007; `claude plugin eval`
      grants `Read` itself, so it does not prove the rule — PLAN 007 → Owner decisions;
      this item re-runs it on the translated skills); Polish survives only in the
      `*.pl.md` templates — SPEC, PLAN and the `init` documents — and in the section map
      (`specs/008-translate-skills-to-english/SPEC.md`)

## Stage 6 — A better pipeline

One spec through the pipeline itself. Lessons from GitHub Spec Kit (`converge`, test-first)
and 10xWorkflow (tests verified by breaking them).

- [x] 0.7.0, first and as its own spec: a prompt audit of the English skills and agents for
      Claude Opus 5.5 (`/claude-api prompt-audit`), with an eval run before the other items
      of this stage land — the new instructions below are then written on the audited
      text, and a regression points at either the audit or the additions, not both. The
      report comes first, then each accepted change on its own. The 0.6.0 translation
      stays one to one so that the eval gate proves parity; the audit is where the
      wording changes. Expected findings: emphasis in capitals, strategy hints the model
      follows unprompted (`implement`: read the full output, start from the first error)
      and the plan reviewer's "assume the plan has gaps", which invites made-up findings.
      The stage contract repeated in every agent and the exact git, test and status steps
      stay: the repetition is pinned by tests, and exact steps suit fragile operations
      (`specs/009-prompt-audit-for-opus-5-5/SPEC.md`)
- [x] 0.7.0: `implement` records every acceptance-criterion test failing before the change
      that makes it pass — a test that was never red proves nothing (`specs/010-test-first-and-converge/SPEC.md`)
- [x] 0.7.0: `implement` closes with a converge pass — a fresh subagent compares the code
      with the acceptance criteria, classifies gaps as missing / partial / contradicts /
      unrequested and adds steps, before the final review (68% of significant findings in
      the consumer's specs 014–022 surfaced only at final review) (`specs/010-test-first-and-converge/SPEC.md`)
- [x] 0.7.0: plan and review depth proportional to the change, instead of spec sizes — a
      four-step fix got a 349-line plan and three reviewers (decision row with the spec:
      no size tiers; small things keep the fast path) (`specs/010-test-first-and-converge/SPEC.md`)
- [x] 0.7.0: the final review reports at most five nits and states how many it left out;
      the cap applies when the report is merged, not in the perspectives' prompts — they
      report every finding with its severity, since a reviewer told to report less finds
      less (current Claude models follow severity filters literally) (`specs/010-test-first-and-converge/SPEC.md`)
- [x] Eval cases for the new behaviour: a test that was never red is caught, and the
      converge pass finds an acceptance criterion left unimplemented (`specs/010-test-first-and-converge/SPEC.md`)

## Stage 7 — A cheaper pipeline, measured

A cost audit on 2026-09-24 (`docs/DECISIONS.md`) priced every stage from the local session
transcripts — this repository's specs 001–010 and the consumer's 014–023, at Opus API rates
as a relative unit (the owner works on a subscription, where it is quota): the implementer
takes about 40% of a spec's cost, the final review with its perspectives 33–41%, the
planner 11–15% and the plan review 7–11%; a consumer spec costs about $14 at the median
($6–51), and the implementer alone ranges from $1.2 to $27 per spec. Most of the
implementer's cost is cache reads (52–69%) — one long context re-read on every turn — and
cache writes take 25–43% of the other stages, whose fresh subagents rebuild their context
from scratch. No stage is dropped: the plan review and the final review cost about the same
per significant finding, and a finding before code is the cheaper one to fix.

- [x] Transcripts kept for the baseline: `cleanupPeriodDays` raised to 365 in the owner's
      user settings and the transcripts of this repository and the consumer copied to an
      archive outside both repositories (2026-09-24; the default 30-day cleanup would have
      removed spec 001 within weeks)
- [x] 0.8.0: targeted reading in every stage — SPEC, PLAN and conventions in full;
      decisions, roadmap and domain documents searched by the feature's topic, with what
      was read listed (the consumer's documents are 271 KB, and every fresh subagent read
      them whole) (`specs/011-cost-metrics-and-stage-models/SPEC.md`)
- [x] 0.8.0: a `models` section in `.claude/workflow.json` that `/pipeline:ship` passes to
      each stage agent — a model per stage; without the section every stage inherits the
      session model and its effort, as before. Checked before the spec: the `Agent` tool
      takes no effort level (Claude Code 2.1.281), so effort stays a plugin default in the
      agents' frontmatter, which the comparison below sets. `/pipeline:init` writes the
      guess `"implement": "sonnet"` until the comparison measures the defaults
      (`specs/011-cost-metrics-and-stage-models/SPEC.md`)
- [x] 0.8.0: `deviations` split into `deviations_minor` and `deviations_major`; specs with
      the old key still pass `--check` (`specs/011-cost-metrics-and-stage-models/SPEC.md`)
- [x] 0.8.0: cost per stage from the local session transcripts, written into `metrics:`
      when a spec closes (transcripts are local and expire, so it cannot be computed later);
      the implement stage also records `converge_gaps`, and `workflow_metrics.py` reports
      the cost per significant finding of the plan review and the final review — the
      measure the audit used to keep every stage. The converge pass returns to the owner
      when it reports no gap over several specs (`specs/011-cost-metrics-and-stage-models/SPEC.md`)
- [x] 0.8.0, a candidate measured in the comparison below and off by default until it
      measures no worse (`"implement": {"chunked": true}`): `/pipeline:ship` runs the
      implementer in chunks, one per step group the planner marks in PLAN.md, each a fresh
      subagent that resumes from the ticked PLAN.md checkboxes as an interrupted run does
      today; a chunk ends only on a green, committed step at its group boundary, and hands
      the next one a note in `## Chunk notes` (decisions taken, traps, the running
      iteration count). A small plan is one group by the planner's judgement, with no
      threshold, since every chunk pays its cache writes again; the converge pass and the
      Definition of Done run in the chunk with the last group, as today
      (`specs/012-chunked-implementer/SPEC.md`)
- [x] Before/after comparison, closed on the data already recorded — no spec runs only to
      measure (`docs/DECISIONS.md`, 2026-10-05). The consumer never ran the planned
      no-`models` baseline: `/pipeline:init` wrote `"implement": "sonnet"`, so all nine of
      its specs (001–009) ran the implementer on Sonnet 5.5. Implementer cost per plan step,
      from `--record-cost` (0.8.2 backfilled the Sonnet 5.5 stages; 008 and 009 ran in cloud
      sessions, whose transcripts are not local, so their implementer cost is lost): in the
      consumer, chunked 86 / 72 / 83 cents (002–004, mean 80) against unchunked 56 / 64 /
      34 / 104 (001, 005–007, mean 64), with no fewer loop iterations or final-review
      findings — the chunked implementer costs about a quarter more and is removed in Stage
      10; in this repository, Opus 27 / 47 / 71 cents (010–012) against Sonnet 17 (013).
      Sonnet stays the implementer default; Opus at `low` effort for the checklist stages
      was never measured and stays in `docs/BACKLOG.md` (P3)
- [x] Cheaper eval runs, in `scripts/` (no plugin version bump): re-running only the
      failed cases merges their results into the receipt while the plugin fingerprint is
      unchanged; a session limit or another infrastructure error is recorded as an error,
      not a FAIL, and does not trigger the five-run measurement policy (twice between
      2026-09-23 and 2026-09-24 a session limit failed every remaining case and forced a
      full re-run); development runs pick the cases whose skill, agent or fixture changed,
      and only the release receipt needs the full suite (a full run costs about $3.5–4.6
      and the three `init` cases are a quarter of it)
      (`specs/013-cheaper-eval-runs/SPEC.md`)
- [ ] Write-up, linked from the root `README.md`: the guard as a shell analyser rather than
      a regex, the measured LLM-judge noise, the before/after numbers and cost per spec

## Stage 10 — Lessons from the first public consumer

Nine specs in the owner's public demo repository (001–009, 0.8.1, implementer on Sonnet 5.5)
and a written report from its spec 005 and its `/pipeline:init` run. Placed before Stage 9,
like Stage 8 before Stage 6, because every following spec runs on it. As few specs as
possible: one for the pipeline loop, one for bootstrapping — split because they share no
code, are verified differently (a pipeline run against a fresh-repository canary and the
`init` eval cases), and the second spec should already run on the first one's pipeline.

- [x] 0.8.2 (patch): a rate for `claude-sonnet-5-5` and a test that every `models.*` alias
      has one; the missing costs backfilled from the local transcripts (this repository's
      010–013, the consumer's 004, 005, 007); the guard's `Read`-rule notice no longer fires
      in a session started in a subdirectory (`backend/`)
- [x] 0.9.0, one spec — fewer rituals, more code in the pipeline loop
      (`specs/014-pipeline-loop-fewer-rituals/SPEC.md`):
      - **remove the converge pass**: 0 real gaps kept in the consumer's nine specs and in
        013, every gap it reported was rejected by the implementer as already decided, while
        the final review still found 1–14 `worth-fixing` findings per spec — it costs a
        subagent and finds nothing the compliance perspective does not
      - **remove the red-record column and its stub ritual**: implementers wrote code first
        and then stubbed it to record a red (consumer 007, 009 deviations), and the empty
        column itself became final-review findings (004 F13, 007 F5). Test-first stays as
        guidance; proof that a test tests something stays with the final review's tests
        perspective, which breaks the code (004 F8)
      - **remove the chunked implementer** (Stage 7 result above)
      - **metrics derived by code**: `workflow_metrics.py` reads every counter it can from
        the spec files — steps from checkboxes, deviations, findings from the report table,
        decisions and escalations from `## Owner decisions`; agents write only what needs
        judgement. Metrics then survive an escalated stage (consumer 005, implement ran as
        four agents and lost its counts)
      - **the spec lint in `--check`**: every AC has a row in the AC → steps matrix, every
        manual scenario says how the owner sees that it passed — a command, a query or a
        place in the UI with the expected result (consumer 005: AC22 had none)
      - **escalations with a kind** (`decision` | `permission` | `tooling`): only `decision`
        counts toward the third-time STOP; the metrics show the rest apart (consumer 005: 3
        of 4 escalations were tooling)
      - **dependencies the implementer can actually install**: a dependency the SPEC's
        owner decisions accept is added by the implementer as before (only an unaccepted one
        escalates; none is added beyond what the change needs). Each package-manager command
        runs as its own Bash call, never chained with a file edit, so the project's allow
        rules (`Bash(uv lock*)`, `Bash(uv sync*)`) match it and the auto-mode classifier is
        not asked — in consumer 005 one chained call was refused twice, and the owner had
        to run the install by hand
      - **a scripted close** for `ship`: `--record-cost`, push, `gh pr checks --watch`, a
        re-run of failed jobs and the flaky-retry check (attempt numbers) before the closing
        commit; "resume the closing step only" as a standard option after an escalation
        there (consumer 005: a whole reviewer run spent on the closing commit)
      - the `ship` start message lists the model of every stage; the metrics summary labels
        the cost as a lower bound while output tokens are undercounted (`docs/BACKLOG.md`)
      - a stage without the `Agent` tool (a cloud session) says in its report that the
        perspectives ran in one context — no restructuring (`docs/BACKLOG.md`, P3)
- [ ] 0.10.0, one spec — bootstrapping and the guard (from the consumer's `init` report):
      - a project in a subdirectory (`backend/`, later `frontend/`): CI
        `working-directory` (also for `setup-uv`), the Dependabot `directory`,
        `verify.command`, `format[].command` (`uv run --project backend …`) and the
        verification commands in `CLAUDE.md` and `docs/CONVENTIONS.md`, filled consistently
      - a CI template that is green on a new project: a minimal skeleton (pinned dev tools,
        a lock file, one smoke test — `pytest` exits 5 without tests) or a passing
        placeholder job; jobs named after layers (`backend`, `frontend`), and a note that a
        renamed job must be renamed in the ruleset
      - `NEW-PROJECT.md`: the first push before enabling the `pre-push` hook, the "scaffold
        through a PR" path (an empty initial commit on `main`), and the repository settings
        as files shipped with the plugin and applied with `gh api --input`: the ruleset,
        squash-only merges with PR title and body, `delete_branch_on_merge`,
        `allow_update_branch`, Dependabot alerts and security updates, private
        vulnerability reporting
      - the `settings.json` template: `ask` on `Edit(**/.claude/workflow.json)`, `deny` on
        detaching the plugin, `allow` for the stack's tools (`uv *`, `docker compose *`)
      - `production`: a warning when `hosts` stays empty, and the known domains and CLI
        offered when the owner names a hosting provider (Railway, Vercel, Fly, Render)
      - `<gitHooksDir>` substituted in the copied `pre-push` (`docs/BACKLOG.md` P3, its
        trigger has fired), `.ruff_cache/` in `.gitignore`, an optional README and licence
        question for a public repository, an optional ADR template
      - the guard: a guardrail file path in a heredoc fed to an interpreter (`python3 -`,
        `node -e`, `perl -e`) is refused (the consumer edited `.claude/workflow.json` that
        way); the once-per-session check warns when `alembic.ini` exists and
        `workflow.json` has no `migrations` section; a refused compound command suggests
        separate calls

## Stage 9 — Evidence

Material from real use, expected in a few weeks; listing in plugin catalogues waits for it
(`docs/BACKLOG.md`, Reach).

- [ ] Measured results from the private production consumer, anonymised: specs shipped,
      escalations per spec, share of significant findings caught before code
- [ ] Evidence from the owner's public demo repository, which uses the plugin: **ask the
      owner** for links to its specs, review reports and PRs when this stage starts, and
      link them from the root `README.md` — the only public proof of the pipeline on a
      product rather than on itself
