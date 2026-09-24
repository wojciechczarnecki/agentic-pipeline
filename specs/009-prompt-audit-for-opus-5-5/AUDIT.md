# Prompt audit — skills and agents for Claude Opus 5.5

Produced on 2026-09-23 with `/claude-api prompt-audit` (guide `shared/prompt-audit.md`,
Claude Code 2.1.281), during `/pipeline:idea` for SPEC 009. The owner's decision on each
finding is recorded in `SPEC.md` → `## Owner decisions`. This report is the input to the
SPEC. It is not changed afterwards.

## Assumptions

- **Scope:** `plugin/skills/*/SKILL.md` (7 skills) and `plugin/agents/*.md` (4 agents).
  Out of scope: eval graders (`plugin/evals/*/graders/criteria.md`), which are prompts to
  the judge, and changing them would move the gate this audit is measured by; the
  templates (`plugin/templates/`), which are document skeletons and not instructions; the
  guard's messages.
- **Target model:** Claude Opus 5.5 (`claude-opus-5-5`), named in `docs/ROADMAP.md`. Effort
  is not set by the plugin (Claude Code's session setting applies); per-stage effort is
  Stage 7.
- **Provenance:** almost all the text comes from the 0.2.0 import (2026-09-17, written for
  earlier models in Polish). SPEC 008 (0.6.0) translated it one to one, so the emphasis and
  the strategy hints are there on purpose, not added by the translation. Later additions
  (0.3.x–0.6.0) are the language, section-map and metrics rules, and each of them came
  with a measured failure recorded in `docs/DECISIONS.md`.
- **No API request code:** the plugin makes no Messages API calls, so Group 1b (API
  scaffolds) and Group 4's API fossils do not apply.

## Summary

11 files inventoried. The findings: Group 1a (pressure language) 3, Group 1c
(over-specification) 3, re-baselining (add) 1, and 6 flags. The three findings with the
most impact:

1. **P2 — `plan-review` "Assume the plan has gaps".** The model is told that its success is
   pointing out gaps, so a sound plan still gets findings. Opus 5.5 follows this literally,
   and its measured strength in review is catching real bugs with fewer false alarms.
2. **P1 — capitals as emphasis in about 40 places.** When everything is marked critical,
   no mark stands out, and current models over-apply shouted rules.
3. **R1 — `idea` has no guardrail against chaining into `/pipeline:ship` or approving its
   own assumptions.** This failure was seen on the 0.6.0 canary, and the backlog trigger for
   it is this audit.

Checked and left alone (keep list): the stage contract repeated in five files and the
`Language` / `Section map` blocks repeated in six skills (working redundancy, pinned by
`test_stage_contract.py` and `test_stage_skills.py`); exact git, test, status and metrics
steps (fragile operations); the `implement` test-integrity rules and the escalation
triggers (prohibitions against demonstrated failures, covered by
`implement-escalates-on-failing-test`); role lines that carry context (`idea`, `implement`,
`ship`); the frontmatter `description` fields (routing text); `STOP`, `RESULT`, `ESCALATE`
and the other contract tokens, which are identifiers.

## Findings

| Id | Location | Evidence | Pattern | Why obsolete for Opus 5.5 | Confidence | Action |
|---|---|---|---|---|---|---|
| P1 | `plan/SKILL.md:9,69,72,101`; `implement/SKILL.md:60,86,90,111,114-115,121,123,129`; `agents/implementer.md:15`; `plan-review/SKILL.md:9,89`; `ship/SKILL.md:9,86,129`; `idea/SKILL.md:10,72,88,89,91,95,111,133`; `init/SKILL.md:21,33,51,73,75,117,121,124,126,130` | `IN FULL`, `ALL`, `NEVER fit the test`, `do NOT go on`, `LOOK AT`, `REALLY performed`, `ALWAYS recommend`, `VERIFY`, `You write ONLY in`, `BY ANY route`, `you NEVER overwrite` … | 1a pressure language | Current models follow the system prompt closely, and capitals make them over-apply a rule and act rigidly in grey areas. Each rule already carries its reason beside it, so the reason, not the volume, has to carry the weight. | High | rewrite: the same words in normal case. Every rule and its reason stay, and so do contract tokens (`STOP`, `RESULT: ESCALATE`, `NNN`, `SPEC`, `PLAN`, `AC`) |
| P2 | `plan-review/SKILL.md:9-12` | "Role: a reviewer whose task is to FIND the problems before they become code. Assume the plan has gaps — your success is pointing them out, not rubber-stamping the plan." | 1a pressure + 1c grader vocabulary ("your success is") | It tells the model that finding problems is how it succeeds, so it produces findings on a sound plan. Opus 5.5 reviews with fewer false alarms when it is asked for the real requirement. | High | rewrite: "Role: a reviewer with a fresh eye, looking for what would make the implementation go wrong before it becomes code — an AC without steps or a test, a broken decision, a step whose verification cannot run. You report what you find, with its severity, and what you checked and found sound. After the review it is you who decides whether the plan is ready for implementation — the owner steps in only when the decision is not yours (step 5)." |
| P3 | `plan-review/SKILL.md:109` | `## IMPORTANT — what the status triggers` | 1a pressure (heading) | A heading that only raises the volume. The paragraph under it already gives the reason ("from that moment `/pipeline:implement` edits … without asking"). | Medium | rewrite: `## What the status triggers`; paragraph unchanged |
| S1 | `implement/SKILL.md:114-115` | "a. read the FULL error output — do not skim; with many errors start from the FIRST (the next ones are often a cascade of the first);" | 1c strategy coaching | Current models do this unprompted. Removing it changes neither what is allowed nor how success is measured, which is the guide's test for a strategy hint. The roadmap named it in advance. | High | remove sub-point a; renumber b–e → a–d |
| S2 | `implement/SKILL.md:129-130` | "**Gate:** you do NOT go on to the next step with the current one's verification red. No exceptions, no "it is probably flaky", no skipping tests." | 1a pressure + 1c prohibition list | The gate itself is load-bearing (the core contract of `implement`). The run of "no exceptions / no … / no …" is emphasis written for a model that talked itself past a red test. | Medium | rewrite: "**Gate:** you go on to the next step only when the current one's verification is green. A test you suspect is flaky is still red, and a skipped test is not green." |
| S3 | `final-review/SKILL.md:151` | "Green tests ≠ correct code — do not shorten the review for that reason." | 1a "be thorough, do not stop early" | Current models are thorough by default, and the three perspectives and the check of each finding in step 3 already set the depth of the review. | Medium | remove |
| R1 | `idea/SKILL.md` → `## Guardrails` | *(missing)* | keep list #11: re-baselining adds text | 0.6.0 canary (2026-09-23, headless): `idea` set `spec-ready` with five unapproved assumptions, then ran `/pipeline:ship` to the final review. `docs/BACKLOG.md` P2 (Idea) names this audit as its trigger. | High | add two guardrails: "You end the stage at the handoff — `/pipeline:ship` and the later stages are started by the owner, never by `idea`, because GATE 1 is the owner's." and "You do not remove the `(assumption)` suffix or set `spec-ready` before the owner has answered on every such item — no answer, including in a session without `AskUserQuestion`, leaves the SPEC `spec-draft`." |
| G1 | `plan-review/SKILL.md:16-18` | "first read the SPEC ALONE (without opening the plan) and note 3–5 points on how you would tackle it yourself" | 1c method choreography | A deliberate technique against anchoring: the model would not do it unprompted, and it serves the fresh-eye purpose of the stage. It is kept except for the capitals (P1). | Low | flag |
| G2 | `plan/SKILL.md:72-74` | "Where a real choice exists, consider ≥2 variants" | 1c strategy | The output requirement (the chosen variant + why) is a contract, and "≥2" is method. The model's own plan usually covers it. | Low | flag |
| G3 | stage contract, 5 files | "SUMMARY: <≤ 10 lines; …>" | 1f numeric ceiling | This format is consumed by the orchestrator, whose context has to stay light (`ship`). It is a format requirement with a reason, not verbosity control. | Low | flag |
| G4 | `init/SKILL.md:54-57` | "Claude Code treats files in `.claude/` as sensitive and asks for consent … only in a session started with `--permission-mode bypassPermissions`" | 2 volatile specifics | A behaviour claim about Claude Code with no verification date. The `init` eval cases still pass on it. | Low | flag — re-measure when `init` next changes |
| G5 | `init/SKILL.md:67-70` | "Move the templates with the shell … a read with a tool may be blocked there" | 2 volatile specifics | Since 0.6.0 the stages read plugin files with `Read` behind an allow rule, but `init` runs before that rule exists (it writes the rule). So the claim is still true for `init`, and the two reads only look inconsistent. | Low | flag |
| G6 | `ship/SKILL.md` | the orchestrator as a model session | 4 LLM executor for a deterministic plan | Status dispatch is deterministic, but escalations, the owner gate and re-runs are judgment. It could only become code outside Claude Code. | Low | flag — out of scope |

## Proposed diff

One hunk per finding, so that each can be taken separately. P1 is split into one hunk per
file. The exact text of every hunk is in the Action column above. This report fixes what
the plan implements: `/pipeline:plan` writes the hunks for the accepted findings.
