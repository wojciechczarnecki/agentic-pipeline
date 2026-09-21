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

- [ ] 0.3.3 (patch): guard fixes
      - a variable in a push refspec is resolved or blocked, like a path for `rm` —
        `B=main; git push origin $B` (also with `export` and `&&`) passes today; measured
        2026-09-21 on 0.3.2, server-side the `main` ruleset still stops it
      - read-only `git config core.hooksPath` (no value) is allowed
      - `gh api -X DELETE` on repository settings unrelated to merges or `main` is allowed
- [ ] `plugin/docs/GUARD.md`: threat model, the three layers (guard → `pre-push` → GitHub
      rulesets) and what each covers, a table of commands a string `deny` rule lets through
      and the guard stops, fail-open by design, and the known limits (Alembic-only
      migrations, best effort rather than a sandbox)
- [ ] `plugin/README.md` in English (documentation only; skills stay Polish until Stage 8)

## Stage 4 — Portfolio storefront

Documentation only, no behaviour change. The private consumer project stays unnamed
(`docs/DECISIONS.md`, 2026-09-17).

- [ ] Root `README.md` rewritten for a reader who has never seen the project: one-line
      pitch, a mermaid diagram of the pipeline and its three gates, *Why not Spec Kit?*
      (it plans, this plugin enforces), quickstart, badges (CI, licence, version), a
      *What's deliberately not here* section, links to `GUARD.md` and the metrics
- [ ] Demo recording: the guard refusing a push to `main` with its reason, and a condensed
      `/pipeline:ship` run
- [ ] Measured results from the private production consumer, anonymised: specs shipped,
      escalations per spec, share of significant findings caught before code
- [ ] GitHub Releases for the `pipeline--v*` tags; `CONTRIBUTING.md`, `SECURITY.md`

## Stage 5 — A release gate to trust, and a guard that guards itself

Every minor release is gated on a green eval receipt, so the gate has to mean something
before the first minor ships.

- [ ] Evals stable enough to gate on: `runs: 3` with a majority score, or sharper criteria —
      decided by measurement (was `docs/BACKLOG.md` P2; its trigger fires with this stage)
- [ ] Pre-release canary, measured and documented: how to run an unreleased plugin in a
      consumer project beside the `--scope user` install without moving `stable`
- [ ] 0.4.0: the guard protects configurable release-channel branches
      (`protectedBranches` in `.claude/workflow.json`), replacing the `deny` rules on
      pushes to `stable` in `.claude/settings.json`
- [ ] 0.4.0: the guard blocks detaching the plugin (`claude plugin disable|uninstall`,
      `claude plugin marketplace remove`) — with a `--scope user` install one command
      removes the guard from every project on the machine

## Stage 6 — A better pipeline

One spec through the pipeline itself. Lessons from GitHub Spec Kit (`converge`, test-first)
and 10xWorkflow (tests verified by breaking them).

- [ ] 0.5.0: `implement` records every acceptance-criterion test failing before the change
      that makes it pass — a test that was never red proves nothing
- [ ] 0.5.0: `implement` closes with a converge pass — a fresh subagent compares the code
      with the acceptance criteria, classifies gaps as missing / partial / contradicts /
      unrequested and adds steps, before the final review (68% of significant findings in
      the consumer's specs 014–022 surfaced only at final review)
- [ ] 0.5.0: plan and review depth proportional to the change, instead of spec sizes — a
      four-step fix got a 349-line plan and three reviewers (decision row with the spec:
      no size tiers; small things keep the fast path)
- [ ] 0.5.0: the final review reports at most five nits and states how many it left out

## Stage 7 — A cheaper pipeline, measured

- [ ] 0.6.0: targeted reading in every stage — SPEC, PLAN and conventions in full;
      decisions, roadmap and domain documents searched by the feature's topic, with what
      was read listed (the consumer's documents are 271 KB, and every fresh subagent read
      them whole)
- [ ] 0.6.0: a `models` section in `.claude/workflow.json` that `/pipeline:ship` passes to
      each stage agent; `/pipeline:init` writes the implementer on Sonnet; without the
      section every stage inherits the session model, as today
- [ ] 0.6.0: `deviations` split into `deviations_minor` and `deviations_major`; specs with
      the old key still pass `--check`
- [ ] 0.6.0: cost per stage from the local session transcripts, written into `metrics:`
      when a spec closes (transcripts are local and expire, so it cannot be computed later)
- [ ] Before/after comparison of the implementer on Sonnet: a baseline of 2–3 consumer
      specs on 0.5.0 with every stage on the session model, then 3–5 specs with the new
      defaults — not the 9 specs before Stage 6, which changes the metrics by itself;
      the result goes into the root `README.md`

## Stage 8 — English everywhere, Polish on request

The repository becomes English end to end; a consumer with `"language": "pl"` keeps Polish
specs, plans, reports and questions. Two releases, in this order — translating first would
silently switch a Polish consumer's plans to English, since today only `idea` names
`language`. Each one goes through the pre-release canary on a Polish consumer before
`stable` moves.

- [ ] 0.7.0: language made explicit, skills still Polish — every stage writes artefacts,
      questions, escalations and PR bodies in `language`; `SPEC`/`PLAN` templates per
      language (`*.en.md`, `*.pl.md`) with a structure-parity test; section anchors and
      finding severities independent of language, with a fallback for older specs;
      default `language` becomes `en`
- [ ] 0.8.0: skills, agents, tests and `plugin/CHANGELOG.md` translated into English, with
      an eval case on `"language": "pl"`; Polish survives only in the `*.pl.md` templates
