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
- [ ] 0.6.0: skills, agents and tests translated into English (`plugin/CHANGELOG.md` already
      is, since 0.3.4), with an eval case on `"language": "pl"`: a Polish SPEC whose
      `## Decyzje właściciela` accepts a new dependency, and `plan-review` approves the plan
      without escalating (the mirror of `plan-review-escalates-on-dependency`) — it fails if
      the section map is misread (the eval case landed with SPEC 007; `claude plugin eval`
      grants `Read` itself, so it does not prove the rule — PLAN 007 → Owner decisions;
      this item re-runs it on the translated skills); Polish survives only in the
      `*.pl.md` templates — SPEC, PLAN and the `init` documents — and in the section map

## Stage 6 — A better pipeline

One spec through the pipeline itself. Lessons from GitHub Spec Kit (`converge`, test-first)
and 10xWorkflow (tests verified by breaking them).

- [ ] 0.7.0, first and as its own spec: a prompt audit of the English skills and agents for
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
- [ ] 0.7.0: `implement` records every acceptance-criterion test failing before the change
      that makes it pass — a test that was never red proves nothing
- [ ] 0.7.0: `implement` closes with a converge pass — a fresh subagent compares the code
      with the acceptance criteria, classifies gaps as missing / partial / contradicts /
      unrequested and adds steps, before the final review (68% of significant findings in
      the consumer's specs 014–022 surfaced only at final review)
- [ ] 0.7.0: plan and review depth proportional to the change, instead of spec sizes — a
      four-step fix got a 349-line plan and three reviewers (decision row with the spec:
      no size tiers; small things keep the fast path)
- [ ] 0.7.0: the final review reports at most five nits and states how many it left out;
      the cap applies when the report is merged, not in the perspectives' prompts — they
      report every finding with its severity, since a reviewer told to report less finds
      less (current Claude models follow severity filters literally)
- [ ] Eval cases for the new behaviour: a test that was never red is caught, and the
      converge pass finds an acceptance criterion left unimplemented

## Stage 7 — A cheaper pipeline, measured

- [ ] 0.8.0: targeted reading in every stage — SPEC, PLAN and conventions in full;
      decisions, roadmap and domain documents searched by the feature's topic, with what
      was read listed (the consumer's documents are 271 KB, and every fresh subagent read
      them whole)
- [ ] 0.8.0: a `models` section in `.claude/workflow.json` that `/pipeline:ship` passes to
      each stage agent — a model and an effort level per stage; `/pipeline:init` writes the
      defaults the comparison below measured; without the section every stage inherits the
      session model and its effort, as today. On Claude Opus 5.5 the first candidate for a
      stage is the same model at `low` or `medium` effort (its default is `medium`), and
      a cheaper model only when that measures worse; whether an agent's frontmatter or
      the `Agent` tool accepts an effort level is checked before the spec is written
- [ ] 0.8.0: `deviations` split into `deviations_minor` and `deviations_major`; specs with
      the old key still pass `--check`
- [ ] 0.8.0: cost per stage from the local session transcripts, written into `metrics:`
      when a spec closes (transcripts are local and expire, so it cannot be computed later)
- [ ] Before/after comparison of model and effort per stage: a baseline of 2–3 consumer
      specs on 0.7.0 with every stage on the session model at its default effort, then
      3–5 specs with the candidates — Opus at `low` effort for the stages that follow a
      checklist or a script, Opus at `low` or Sonnet for the implementer — and the chosen
      defaults — not the 9 specs before Stage 6, which changes the metrics by itself;
      the result goes into the root `README.md`
- [ ] Write-up, linked from the root `README.md`: the guard as a shell analyser rather than
      a regex, the measured LLM-judge noise, the before/after numbers and cost per spec

## Stage 9 — Evidence

Material from real use, expected in a few weeks; listing in plugin catalogues waits for it
(`docs/BACKLOG.md`, Reach).

- [ ] Measured results from the private production consumer, anonymised: specs shipped,
      escalations per spec, share of significant findings caught before code
- [ ] Evidence from the owner's public demo repository, which uses the plugin: **ask the
      owner** for links to its specs, review reports and PRs when this stage starts, and
      link them from the root `README.md` — the only public proof of the pipeline on a
      product rather than on itself
