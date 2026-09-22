---
status: plan-draft
stage_history:
  - "spec-draft — 2026-09-22"
  - "spec-ready — 2026-09-22"
  - "plan-draft — 2026-09-22"
metrics:
  started_at: 2026-09-22T11:21
  escalations: 0
  plan_steps: 12
---

# SPEC 004 — A release gate to trust

## Goal

A minor or major release is gated on a green eval receipt (`docs/DECISIONS.md`,
2026-09-20), but the gate means little today: three cases at `runs: 1` judged by an LLM,
none of them covering the stage skills that make up the pipeline, and no way to try an
unreleased plugin in a real project before `stable` moves. This spec makes the gate worth
trusting before the first minor release (0.4.0, SPEC 005) goes through it: the suite
covers the stage skills, its verdict is stable on unchanged code, and the release
procedure includes a measured pre-release canary. It works when a behavioural regression
in `implement`, `plan-review` or `final-review` turns the receipt red, and two runs on the
same `plugin/` agree.

## Context

- Stage 5 of `docs/ROADMAP.md` is split in two, by the owner's decision: this spec takes
  eval stability, the stage-skill evals and the canary; SPEC 005 (a separate
  `/pipeline:idea`) takes the guard 0.4.0 items (`protectedBranches`, blocking plugin
  detachment). 0.4.0 is a minor release, so it is tagged only through the gate this spec
  hardens.
- Eval suite today: `plugin/evals/` holds `guard-blocks-main-push` (with `scaffold.sh`),
  `init-keeps-manual-edits`, `init-without-questions`, all `runs: 1`, one LLM grader each
  (`graders/criteria.md`), prompts and criteria in Polish. Last receipt
  `plugin/evals/last-run.json`: 3/3 green on 0.3.0, $1.4575 — about $0.5 per run.
- Gate mechanics: `scripts/eval.sh` runs `claude plugin eval plugin/ --scaffold
  --allow-tools Bash Write Edit --trust-plugin --no-publish --ablation none` and writes the
  receipt (`plugin_fingerprint`, `cases_total`, `cases_passed`, `green`, `cost_usd`) from
  `aggregates.casesPassed == casesTotal`; `scripts/git-hooks/pre-push` refuses a
  `pipeline--vX.Y.0` tag without a receipt whose fingerprint matches the tagged `plugin/`,
  whose `cases_total` equals the number of `case.yaml` files at the tag, and which is
  green. Tested in `tests/test_release_gate.py`.
- `claude plugin eval` (Claude Code 2.1.272): `--runs <n>` overrides `case.runs` (default
  3), `--threshold` (default 1.0), `--model`, `--max-cost-usd`, `--case`, `--json`. Each run
  is a full agent session on the owner's credential; the grader defaults to haiku. Inside
  an eval run `AskUserQuestion` does not exist and writes to `.claude/` are blocked
  (`docs/DECISIONS.md`, 2026-09-20; `init-*` criteria).
- Evals run only locally, on demand, before a minor or major tag — never in CI, never per
  PR, never for a patch.
- Release procedure: `docs/CONVENTIONS.md` → Releases, commands in `CLAUDE.md` → Commands.
  Consumers follow `stable` with a single `--scope user` install
  (`plugin/docs/INSTALL.md`).

## Read context

- `docs/ROADMAP.md` — Stage 5 lists eval stability ("decided by measurement"), stage-skill
  evals, the canary, the guard 0.4.0 items and a question to the owner on Stage 8 vs
  Stage 6. The owner answered here: Stage 8 moves ahead of Stage 6; this spec delivers the
  first three items and the answer, SPEC 005 the two 0.4.0 items.
- `docs/PROJECT.md` — non-functional: behaviour changes are released as tagged semver
  versions; the plugin stays project-agnostic, so eval fixtures name no consumer.
- `docs/DECISIONS.md` — 2026-09-17 (eval never a PR gate), 2026-09-20 (eval local and
  on demand, no workflow; `init-question-cap` deleted because a case that cannot pass is no
  signal; minor/major tags gated on the receipt checked by `pre-push`, patches exempt,
  fingerprint instead of sha), 2026-09-21 (`stable` channel and `--scope user` install,
  measured with an isolated `CLAUDE_CONFIG_DIR` and a local marketplace — the method the
  canary measurement reuses; plugin name and tag prefix permanent).
- `docs/BACKLOG.md` — P3 "eval as a blocking CI gate" stays deferred (cost; its trigger has
  not fired). The P2 eval-stability item the roadmap mentions is already promoted into
  Stage 5.
- `docs/CONVENTIONS.md` — version grows with behaviour (skills, agents, hooks, guard,
  templates), not with evals, docs or tests; repository rules are tested in the root
  `tests/`; the eval command and its sandbox requirement (`bubblewrap`, `socat`); release
  procedure the canary step joins.
- `plugin/README.md` — the `RESULT` contract and escalation triggers the stage-skill evals
  grade against; no change expected.

## Scope

- Four behavioural eval cases for the stage skills, in English:
  - `implement` escalates instead of weakening, skipping or deleting a failing test;
  - `plan-review` escalates on a dependency the owner did not accept;
  - `final-review` (report mode) finds a planted defect;
  - `final-review` (report mode) does not report a planted false positive — correct code
    that looks suspicious.
- A stability measurement of the suite and a per-case `runs` setting derived from it.
- A receipt that counts a multi-run case by majority, and records the model the suite ran
  on.
- A measured pre-release canary procedure, as a mandatory step of a minor or major release.
- The roadmap reordered: Stage 8 ahead of Stage 6.
- `docs/DECISIONS.md` rows for the three decisions below.

## Out of scope

- The guard 0.4.0 items (`protectedBranches`, blocking `claude plugin disable|uninstall`,
  `marketplace remove`) — SPEC 005, through its own `/pipeline:idea`.
- Translating the three existing eval cases into English — Stage 8 (skills, agents and
  tests translated).
- Eval cases for `idea`, `plan`, `ship` and `init`'s other paths — added when a regression
  there is seen; no backlog item until then.
- Eval in CI — stays in `docs/BACKLOG.md` P3 with its trigger.
- Fixing a stage skill that a new case shows misbehaving — that is a behaviour change with
  its own version and changelog; it is escalated to the owner, not fixed in this spec.

## Requirements and acceptance criteria

Stage-skill evals

- [ ] AC1: `plugin/evals/` holds one case for each of the four behaviours in Scope; each
      case's prompt, grader criteria and scaffold comments are in English, and its
      fixture (repository, SPEC, PLAN) is built by a `scaffold.sh` and names no consumer
      project (`plugin/tests/test_no_domain_references.py` stays green).
- [ ] AC2: each new case fails on a transcript showing the wrong behaviour: its grader
      criteria name the wrong behaviour explicitly (for `implement`: the test weakened,
      skipped, marked `xfail` or deleted, or the assertion changed to match the code), so
      a case cannot pass on a transcript that merely avoids the subject.
- [ ] AC3: each new case passes on the released stage skills, measured on the default
      model (see AC7).

Stability and cost

- [ ] AC4: every new case is run at least 5 times on an unchanged `plugin/` and passes in at
      least 4 of them; a case below 4 of 5 gets sharper criteria or a rewritten fixture and
      is measured again, and a case still below 4 of 5 is escalated rather than shipped.
- [ ] AC5: a case that passed 5 of 5 keeps `runs: 1`; a case that passed 4 of 5 gets
      `runs: 3`. The three existing cases keep `runs: 1` unless one fails in any run during
      this spec, which triggers the same 5-run measurement for it.
- [ ] AC6: the receipt counts a case with several runs as passed when a majority of its
      runs passed (2 of 3) and as failed otherwise (1 of 3); `tests/test_release_gate.py`
      proves both on a fixture result file, with no model involved.
- [ ] AC7: the receipt records the model the suite ran on, and the `pre-push` hook refuses
      a minor or major tag whose receipt was produced with a `--model` override; a test in
      `tests/test_release_gate.py` covers it.
- [ ] AC8: two consecutive full runs of `bash scripts/eval.sh` on the same `plugin/` are
      both green; the second run's receipt is committed.
- [ ] AC9: every eval invocation during this spec carries `--max-cost-usd`, and their total
      (drafting included) stays at or below $15; reaching the ceiling is an escalation. The
      measured pass counts per case, the total cost and the Claude Code version go into the
      `docs/DECISIONS.md` row.
- [ ] AC10: `docs/CONVENTIONS.md` states the resulting cost policy: `runs: 3` only for a
      case measured below 5 of 5, drafting on `--model sonnet` allowed, receipts only on
      the default model.

Canary

- [ ] AC11: the canary is measured in a sandbox — an isolated `CLAUDE_CONFIG_DIR`, a local
      marketplace on a `stable`-like branch with a `--scope user` install of the released
      version, and a throwaway consumer project — and the measurement shows: which copy of
      the plugin a canary session loads (the unreleased one, by a visible marker such as
      the version), that the `--scope user` install and the channel branch are unchanged
      afterwards, and how to return to the released version. The owner's real install and
      projects are not touched.
- [ ] AC12: the canary procedure (commands, how to confirm which copy loaded, how to go
      back) is a mandatory step of a minor or major release in `docs/CONVENTIONS.md` →
      Releases, before the tag, and appears in `CLAUDE.md` → Commands; patches are exempt,
      as for the eval receipt.

Roadmap and decisions

- [ ] AC13: `docs/ROADMAP.md` ticks Stage 5's eval-stability, stage-skill-evals and
      canary items and the Stage 8 question, each referencing this spec; the two 0.4.0
      items stay unticked. Stage 8 is placed after Stage 5 and before Stage 6, keeping the
      stage numbers (references such as "until Stage 8" in append-only `docs/DECISIONS.md`
      must stay valid), and the release versions of Stages 8, 6 and 7 are renumbered to
      follow 0.4.0 in the new order.
- [ ] AC14: `docs/DECISIONS.md` gains rows for: Stage 8 ahead of Stage 6 (with the owner's
      reasons), the measured eval stability policy (AC9's numbers), and the canary as a
      release step with its measured mechanism.
- [ ] AC15: no version bump and no `plugin/CHANGELOG.md` entry — evals, receipt tooling
      and documents are not plugin behaviour (`docs/CONVENTIONS.md` → Releases).
- [ ] AC16: `bash scripts/check.sh` is green.

## Decisions and rejected alternatives

| Decision | Rejected alternatives | Rationale |
|---|---|---|
| Stage 5 split: evals and canary here, guard 0.4.0 in SPEC 005, evals first | one spec for all of Stage 5; guard first | Two risk profiles — paid, variable measurement vs deterministic code under pytest; 0.4.0 is the first minor and must pass a gate that already means something |
| Stage 8 moves ahead of Stage 6 | order unchanged | Stages 6–7 would rewrite Polish skills that are translated right after; the canary and eval gate from this spec are what make the translation safe. Cost: two releases before the pipeline improvements |
| New eval cases written in English; the existing three stay Polish until Stage 8 | Polish for consistency; translating the existing three now | Follows the Stage 8 decision; translating existing cases changes what they measure and belongs with the skills' translation |
| Lean cost policy: 5-run measurement for new or failing cases, `runs: 3` only where a case is measured below 5 of 5; ceiling $15 | `runs: 3` everywhere (~$35 measurement, ~$10 per release) | Deterministic cases gain nothing from repeats; the `init` cases are the expensive ones; the gate costs about $4–6 per minor release |
| Stable enough = each case ≥ 4 of 5 runs, and two consecutive gate runs agree | 100% of 5 runs; `runs: 3` majority without a per-case threshold | An LLM-graded case rarely reaches 100%; without a per-case threshold a flaky case hides behind the majority |
| Drafting a case on `--model sonnet`, measurement and receipts on the default model | everything on the default model; the gate on Sonnet | Consumers work on the session model, so the gate must measure it; drafting is iteration on the case, not evidence |
| Canary measured in a sandbox by the implementer | on the owner's private consumer, run by the owner | The method already used for the `stable` channel measurements; leaves the owner's install and projects untouched |
| Canary is a mandatory step of minor/major releases, not enforced by a mechanism | optional instruction; mandatory for patches too | Nothing can check that a plugin was used in another repository; patches stay exempt like the eval receipt |

## Owner decisions

- No new dependency and no data migration (none needed: `claude plugin eval` is part of
  Claude Code, and `bubblewrap`/`socat` are already required by `scripts/eval.sh`).
- Eval spend: the implementer runs the evals itself, every call with `--max-cost-usd`,
  $15 in total for this spec including drafting; reaching it is an escalation — accepted.
- `--model sonnet` accepted for drafting cases only.

## Open questions (non-blocking)

- none
