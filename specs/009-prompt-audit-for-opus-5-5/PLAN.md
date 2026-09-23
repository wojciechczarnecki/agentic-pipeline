# PLAN 009 — Prompt audit of the skills and agents for Claude Opus 5.5

## Owner summary

- **Approach:** The seven accepted findings of `AUDIT.md` are applied one commit each: first
  the sentence rewrites and removals (P2, P3, S1, S2, S3) and the new `idea` guardrails
  (R1), each with a pytest that pins it; then P1, which only lowers capitals, one commit
  per file (8 files, including `final-review`, which the audit's line list missed but AC1
  covers). A new pytest then keeps capitals-as-emphasis out of all 11 files with the
  SPEC's token allowlist (no extension needed). Last come version 0.7.0, the CHANGELOG and
  the documents.
- **Main risks:** a P1 commit that changes more than letter case (guarded by a
  lower-cased diff in every P1 step); the eval run (AC9) must happen after the last change
  to `plugin/`, or its fingerprint will not match.
- **New dependency:** no
- **Data migration:** no
- **Manual scenarios for the owner:** 1 — on the owner's command after the PR is open, the
  full `bash scripts/eval.sh` run and the committed receipt (AC9).

## Approach

**Order.** The findings that rewrite or remove whole sentences (P2, P3, S1, S2, S3) go
first, so the P1 commits that follow show nothing but letter-case changes (AC2), and no
capitals get lowered only to be deleted in a later commit. R1 adds new text (with the
allowed `GATE`) and goes before P1 on `idea`. The AC1 scanner comes after the last P1
commit, so every commit on the branch is green; that the check fails on the pre-audit text
is proven by a verification command that scans the files at the merge base, and for good
by a unit test on excerpts of the old wording.

**Variants considered for the AC1 check.** (a) Add the scanner first and let it go green
file by file — rejected: it leaves the branch red for eight commits, or needs a list of
"not yet clean" files that the P1 commits would edit, so those commits would no longer be
pure case changes. (b) Add the scanner last and prove the red state on the merge-base text
— chosen: every commit stays green and bisectable, which is what the per-finding commits
are for.

**Tests.** Two new files in `plugin/tests/`, following the style of
`plugin/tests/test_stage_skills.py` (`PLUGIN = Path(__file__).resolve().parents[1]`, a
`section()` helper that cuts a `## ` section out of a skill):

- `test_prompt_audit.py` — one or more tests per sentence-level finding (P2, P3, S1, S2,
  S3, R1). Assertions compare text with whitespace collapsed (`" ".join(text.split())`),
  because the skills are hard-wrapped. Where a later P1 commit lowers capitals in the same
  passage (the `implement` loop), the assertion compares lower-cased text so it survives
  P1.
- `test_prompt_style.py` — the AC1 scanner. Shape (precision needed for the allowlist):

  ```python
  PLUGIN = Path(__file__).resolve().parents[1]
  AUDITED = sorted([*PLUGIN.glob("skills/*/SKILL.md"), *PLUGIN.glob("agents/*.md")])
  ALLOWED = frozenset({"STOP", "RESULT", "DONE", "ESCALATE", "STATUS", "METRICS",
      "ESCALATION", "SUMMARY", "SPEC", "PLAN", "NNN", "AC", "ACs", "CI", "PR", "UI", "API",
      "CLI", "JSON", "HTTPS", "README", "CLAUDE", "GATE", "E2E", "URL", "TODO"})
  CAPITALS = re.compile(r"\b[A-Z]{3,}\b")

  def prose(text: str) -> str: ...        # drops fenced blocks (asserts they balance) and `code` spans
  def emphasis_words(text: str) -> list[str]: ...   # CAPITALS over prose(text), minus ALLOWED
  ```

  The code-span/fence stripping mirrors `strip_code` in `plugin/tests/test_readme.py`
  (copied, not imported: test modules do not import one another in this repository).

**Allowlist.** The current text, scanned outside code, has only these capital words beyond
emphasis: `STOP RESULT DONE ESCALATE METRICS ESCALATION SUMMARY SPEC PLAN NNN CLI API
README CLAUDE` (`STATUS` appears only inside the contract fence, and `E2E` is not matched
by `[A-Z]{3,}` because of its digit) — all on the SPEC's list, so the list is not extended
and `## Deviations` needs no allowlist entry. Two-letter tokens (`AC2`, `OK`, `CI`) are not
matched by `[A-Z]{3,}`. Two-letter emphasis inside a phrase (`IN FULL`, `LOOK AT`,
`BY ANY`, `LOOKING AT`) is lowered together with its phrase in P1.

**The `implement` loop.** The self-correction loop is a fenced block, which the AC1
scanner skips, yet the audit's P1 names capitals in it (`ALL`, `NEVER`, `AGAIN`). The P1
step for `implement` lowers them too, and `test_prompt_style.py` adds a test that runs
`CAPITALS` over that one fenced block, so the loop is covered as well.

**Exact texts.** P2, S2 and the two R1 bullets use the exact wording of `AUDIT.md` →
Findings → Action. The R1 bullets go into `idea/SKILL.md` → `## Guardrails` right after
the bullet "A SPEC with status `spec-ready` may not contain blocking questions …", in the
audit's order. Unchanged: the stage contract and escalation triggers (pinned by
`plugin/tests/test_stage_contract.py`), the configuration, language and section-map blocks
(pinned by `plugin/tests/test_stage_skills.py`), the frontmatter descriptions, templates,
eval graders and guard messages.

**Commits.** Finding commits name their id (AC8): `refactor: … (P2)` etc., P1 as
`refactor: lower emphasis in <file> (P1)`. The scanner commit is named for AC1 (not P1),
so that "P1 commits show only case changes" (AC2) stays literally true. Each commit holds
the step's files plus PLAN.md, per `plugin/skills/implement/SKILL.md`.

## AC → steps matrix

| AC | Steps | Proving test |
|----|-------|--------------|
| AC1 | 7–15 | `plugin/tests/test_prompt_style.py` (all tests); step 15's merge-base scan shows the pre-audit text fails |
| AC2 | 7–14 | lower-cased `diff` against the previous commit in each of steps 7–14; E2E check over `git log` |
| AC3 | 1 | `plugin/tests/test_prompt_audit.py::test_plan_review_role_*` |
| AC4 | 2 | `plugin/tests/test_prompt_audit.py::test_plan_review_status_heading_*` |
| AC5 | 3, 4 | `plugin/tests/test_prompt_audit.py::test_implement_loop_*`, `::test_implement_gate_*` |
| AC6 | 5 | `plugin/tests/test_prompt_audit.py::test_final_review_*` |
| AC7 | 6 | `plugin/tests/test_prompt_audit.py::test_idea_guardrails_*` |
| AC8 | 1–14 (commit messages) | E2E automatic: `git log --format=%s origin/main..HEAD` |
| AC9 | after the PR is open, on the owner's command (not part of `/pipeline:implement`) | `plugin/evals/last-run.json` green, fingerprint matching `plugin/` at the branch head |
| AC10 | 16, 17 | `plugin/tests/test_readme.py` (CHANGELOG section for the manifest version, consumer impact); `tests/test_documents.py::test_conventions_state_the_prompt_style`, `::test_decisions_record_the_prompt_style`, `::test_backlog_drops_the_idea_chaining_item`, `::test_roadmap_ticks_the_prompt_audit`; review of the CHANGELOG entries |
| AC11 | all | `bash scripts/check.sh` (E2E automatic) |

## Steps

- [x] 1. **P2 — the plan reviewer's role.** In `plugin/skills/plan-review/SKILL.md` replace
      the role paragraph (lines 9–12, "Role: a reviewer whose task is to FIND … (step 5).")
      with the audit text, verbatim: "Role: a reviewer with a fresh eye, looking for what
      would make the implementation go wrong before it becomes code — an AC without steps
      or a test, a broken decision, a step whose verification cannot run. You report what
      you find, with its severity, and what you checked and found sound. After the review
      it is you who decides whether the plan is ready for implementation — the owner steps
      in only when the decision is not yours (step 5)." (hard-wrapped at ~90 columns).
      Create `plugin/tests/test_prompt_audit.py` with the `PLUGIN`/`skill_text`/`section`
      helpers and `test_plan_review_role_*` tests: the file contains neither "Assume the
      plan has gaps" nor "your success is"; the role paragraph (text before the first
      `## `) contains, whitespace-collapsed, "an AC without steps or a test", "a broken
      decision", "a step whose verification cannot run", "with its severity", "what you
      checked and found sound" and "it is you who decides whether the plan is ready for
      implementation". Commit: `refactor: reword the plan reviewer's role (P2)`.
      files: `plugin/skills/plan-review/SKILL.md`, `plugin/tests/test_prompt_audit.py`
      Automatic verification: `uv run pytest plugin/tests/test_prompt_audit.py plugin/tests/test_stage_skills.py plugin/tests/test_stage_contract.py -q`
- [x] 2. **P3 — the status heading.** In `plugin/skills/plan-review/SKILL.md` change
      `## IMPORTANT — what the status triggers` to `## What the status triggers`; the
      paragraph under it stays byte for byte. Add `test_plan_review_status_heading_*`:
      `section("plan-review", "What the status triggers")` equals the pinned original
      paragraph (the four lines "`plan-approved` triggers the approval rule: … even if it
      seems obvious."), and no line starting with `#` contains `IMPORTANT`. Commit:
      `refactor: drop the emphasis heading in plan-review (P3)`.
      files: `plugin/skills/plan-review/SKILL.md`, `plugin/tests/test_prompt_audit.py`
      Automatic verification: `uv run pytest plugin/tests/test_prompt_audit.py plugin/tests/test_stage_skills.py -q`
- [x] 3. **S1 — the strategy hint in the loop.** In `plugin/skills/implement/SKILL.md`,
      in the fenced self-correction loop, delete sub-point `a.` ("read the FULL error
      output … cascade of the first);", two lines) and reletter `b.`–`e.` to `a.`–`d.`
      with their text unchanged (continuation lines keep their indentation). Add
      `test_implement_loop_*`, working on the lower-cased fenced block that follows
      `## Self-correction loop`: the sub-point letters are exactly `a b c d`
      (`re.findall(r"^\s+([a-z])\. ", loop, re.M)`); it contains neither "read the full
      error output" nor "start from the first"; `a.` starts "establish the cause", `b.`
      "a mismatch with the plan → escalation", `c.` "a product defect", `d.` "a bug → fix
      it and go back to 1."; and "never fit the test to the defect" is still there.
      Commit: `refactor: drop the strategy hint from the implement loop (S1)`.
      files: `plugin/skills/implement/SKILL.md`, `plugin/tests/test_prompt_audit.py`
      Automatic verification: `uv run pytest plugin/tests/test_prompt_audit.py plugin/tests/test_stage_skills.py -q`
- [x] 4. **S2 — the gate.** In `plugin/skills/implement/SKILL.md` replace the two gate
      lines with the audit text, verbatim: "**Gate:** you go on to the next step only when
      the current one's verification is green. A test you suspect is flaky is still red,
      and a skipped test is not green." Add `test_implement_gate_*`: the paragraph that
      starts with `**Gate:**`, whitespace-collapsed, equals that text exactly, and the file
      no longer contains "No exceptions". Commit: `refactor: state the implement gate
      plainly (S2)`.
      files: `plugin/skills/implement/SKILL.md`, `plugin/tests/test_prompt_audit.py`
      Automatic verification: `uv run pytest plugin/tests/test_prompt_audit.py -q`
- [x] 5. **S3 — the thoroughness line.** In `plugin/skills/final-review/SKILL.md` →
      `## Guardrails` delete the bullet "Green tests ≠ correct code — do not shorten the
      review for that reason."; the other four bullets stay. Add `test_final_review_*`:
      the file does not contain "Green tests ≠ correct code", and `## Guardrails` still has
      four bullets. Commit: `refactor: drop the thoroughness line from final-review (S3)`.
      files: `plugin/skills/final-review/SKILL.md`, `plugin/tests/test_prompt_audit.py`
      Automatic verification: `uv run pytest plugin/tests/test_prompt_audit.py plugin/tests/test_stage_skills.py -q`
- [x] 6. **R1 — `idea` does not chain or approve itself.** In
      `plugin/skills/idea/SKILL.md` → `## Guardrails`, right after the bullet "A SPEC with
      status `spec-ready` may not contain blocking questions …", insert the two audit
      bullets verbatim: "You end the stage at the handoff — `/pipeline:ship` and the later
      stages are started by the owner, never by `idea`, because GATE 1 is the owner's." and
      "You do not remove the `(assumption)` suffix or set `spec-ready` before the owner has
      answered on every such item — no answer, including in a session without
      `AskUserQuestion`, leaves the SPEC `spec-draft`." Add `test_idea_guardrails_*` on
      the whitespace-collapsed `## Guardrails` section: it contains "You end the stage at
      the handoff", "never by `idea`", "GATE 1 is the owner's", "You do not remove the
      `(assumption)` suffix or set `spec-ready` before the owner has answered on every such
      item" and "including in a session without `AskUserQuestion`, leaves the SPEC
      `spec-draft`". When hard-wrapping the new bullets (and the P2 and S2 texts), do not
      break a code span across two lines: the AC1 scanner strips code spans line by line.
      Commit: `feat: keep idea from chaining into ship or approving its own assumptions
      (R1)`.
      files: `plugin/skills/idea/SKILL.md`, `plugin/tests/test_prompt_audit.py`
      Automatic verification: `uv run pytest plugin/tests/test_prompt_audit.py plugin/tests/test_stage_skills.py plugin/tests/test_english_only.py -q`

Steps 7–14 are P1: letter case only, one file per step and per commit
(`refactor: lower emphasis in <file> (P1)`, `<file>` = the skill or agent name). A word at
a sentence start becomes capitalised (`READ the` → `Read the`), a word inside a sentence
or at the start of a lower-case list item becomes lower case. Each step uses the same
automatic verification, with `F` set to the step's file:

```bash
F=<the step's file>
# AC2: nothing but letter case changed against the previous commit — no output expected
bash -c 'diff <(git show HEAD:"$0" | tr "[:upper:]" "[:lower:]") <(tr "[:upper:]" "[:lower:]" < "$0")' "$F"
# AC1 for this file: no capital word outside code spans beyond the allowlist — no output expected
sed -e 's/`[^`]*`//g' "$F" | grep -oE '\b[A-Z]{3,}\b' | sort -u | grep -vxE 'STOP|RESULT|DONE|ESCALATE|STATUS|METRICS|ESCALATION|SUMMARY|SPEC|PLAN|NNN|ACs?|CI|PR|UI|API|CLI|JSON|HTTPS|README|CLAUDE|GATE|E2E|URL|TODO'
uv run pytest plugin/tests -q
```

- [x] 7. **P1 `plan`** — `plugin/skills/plan/SKILL.md`: "WHAT and WHY — you decide HOW",
      "IN FULL", "covering ALL", "EXACT commands", "LOOKING AT", "Do NOT implement".
      Automatic verification: the P1 block above with `F=plugin/skills/plan/SKILL.md`
- [x] 8. **P1 `plan-review`** — `plugin/skills/plan-review/SKILL.md`: "the SPEC ALONE",
      "EXACT commands", "(do NOT set `plan-approved`)". (`FIND` and `IMPORTANT` are gone
      after steps 1–2; `OK` is a verdict token and stays.)
      Automatic verification: the P1 block above with `F=plugin/skills/plan-review/SKILL.md`
- [x] 9. **P1 `implement`** — `plugin/skills/implement/SKILL.md`: "IN FULL", "LOOK AT",
      "REALLY performed", and inside the loop fence "Run ALL", "NEVER fit", "run ALL the
      commands AGAIN". (`FULL`/`FIRST` and `NOT` are gone after steps 3–4.) The AC1 grep
      above skips nothing inside the fence, so it also checks the loop.
      Automatic verification: the P1 block above with `F=plugin/skills/implement/SKILL.md`
- [x] 10. **P1 `final-review`** — `plugin/skills/final-review/SKILL.md`: "ITS OWN
      perspective", "Check EVERY finding". Not in the audit's line list, but AC1 covers every
      skill; the finding (P1) is the same.
      Automatic verification: the P1 block above with `F=plugin/skills/final-review/SKILL.md`
- [x] 11. **P1 `idea`** — `plugin/skills/idea/SKILL.md`: "is NOT to write", "IN FULL",
      "ALWAYS recommend", "option LABEL", "on WHY you", "VERIFY in the code", "SEPARATELY",
      "Do NOT design".
      Automatic verification: the P1 block above with `F=plugin/skills/idea/SKILL.md`
- [x] 12. **P1 `init`** — `plugin/skills/init/SKILL.md`: "write ONLY in", "BY ANY route",
      "do NOT ask and do NOT block", "do NOT rebuild", "READ the template's", "BOTH jobs",
      "stays ALWAYS", "ASK before", "you NEVER overwrite", "NEW answers".
      Automatic verification: the P1 block above with `F=plugin/skills/init/SKILL.md`, plus `uv run pytest plugin/tests/test_init_skill.py -q`
- [x] 13. **P1 `ship`** — `plugin/skills/ship/SKILL.md`: "do NOT plan, do NOT implement
      and do NOT review", "contains ONLY:", "a NEW agent". The stage contract fence stays
      untouched.
      Automatic verification: the P1 block above with `F=plugin/skills/ship/SKILL.md`, plus `uv run pytest plugin/tests/test_stage_contract.py -q`
- [x] 14. **P1 `implementer` agent** — `plugin/agents/implementer.md`: "LOOK AT". The
      other three agents have no emphasis and are not touched.
      Automatic verification: the P1 block above with `F=plugin/agents/implementer.md`, plus `uv run pytest plugin/tests/test_stage_contract.py plugin/tests/test_stage_skills.py -q`
- [x] 15. **AC1 — the scanner.** Create `plugin/tests/test_prompt_style.py` (shape in
      Approach) with:
      - `test_no_capitals_as_emphasis[<file>]`, parametrised over `AUDITED` (ids relative
        to `PLUGIN`): `emphasis_words(text) == []`;
      - `test_the_audited_set_is_complete`: `AUDITED` holds the 7 skills and 4 agents
        named in the SPEC, so a moved file cannot drop out of the check;
      - `test_the_scanner_flags_the_old_style`: excerpts of the pre-audit wording,
        e.g. "you do NOT go on to the next step", "## IMPORTANT — what the status
        triggers", "read the files IN FULL", yield `NOT`, `IMPORTANT`, `FULL`;
      - `test_the_scanner_ignores_code_and_tokens`: `` `NOT` ``, a fenced block with
        `ALWAYS`, "`RESULT: ESCALATE`", "the SPEC and the PLAN", "GATE 1", "AC2" yield `[]`;
      - `test_the_implement_loop_has_no_emphasis`: `CAPITALS` over the fenced block after
        `## Self-correction loop` in `implement`, minus `ALLOWED`, is empty.
      Commit: `test: keep capitals-as-emphasis out of skills and agents (AC1)`.
      files: `plugin/tests/test_prompt_style.py`
      Automatic verification:
      `uv run pytest plugin/tests/test_prompt_style.py -q` and the proof that the check
      fails on the pre-audit text (a non-empty result and exit 0 expected):

      ```bash
      uv run python - <<'EOF'
      import subprocess, sys
      sys.path.insert(0, "plugin/tests")
      from test_prompt_style import AUDITED, PLUGIN, emphasis_words
      base = subprocess.check_output(["git", "merge-base", "HEAD", "origin/main"], text=True).strip()
      hits = {}
      for path in AUDITED:
          rel = path.relative_to(PLUGIN.parent).as_posix()
          old = subprocess.check_output(["git", "show", f"{base}:{rel}"], text=True)
          if found := emphasis_words(old):
              hits[rel] = found
      print(hits)
      assert hits, "the check must fail on the pre-audit text"
      EOF
      ```
- [x] 16. **Version and CHANGELOG.** `plugin/.claude-plugin/plugin.json` → `"version":
      "0.7.0"`. In `plugin/CHANGELOG.md` add `## 0.7.0` above `## 0.6.1`: one intro
      paragraph (the skills and agents are reworded for Claude Opus 5.5 after a prompt
      audit; rules keep their words and reasons), the line `**consumer impact:** none — no
      configuration change; update as usual.`, and `### Changed` with one entry per group
      of findings: capitals lowered across skills and agents, with a test that keeps them
      out (P1); the `plan-review` role and heading (P2, P3); the `implement` loop and gate
      (S1, S2); the `final-review` thoroughness line removed (S3); the two `idea`
      guardrails (R1). Commit: `chore: bump the plugin to 0.7.0`.
      files: `plugin/.claude-plugin/plugin.json`, `plugin/CHANGELOG.md`
      Automatic verification: `uv run pytest plugin/tests/test_readme.py plugin/tests/test_english_only.py tests/test_documents.py -q`
- [ ] 17. **Documents.** `docs/CONVENTIONS.md` → `## Language`: after the bullet "A change
      to the skills' wording is a behaviour change …" add a bullet stating the rule for
      skill and agent text — a rule is stated at normal volume with its reason beside it,
      capitals are kept for contract tokens and identifiers, and
      `plugin/tests/test_prompt_style.py` enforces it with an explicit allowlist that grows
      only by identifiers (`docs/DECISIONS.md`, 2026-09-23). `docs/BACKLOG.md` → `## P2`:
      remove the Idea row "`idea` must not start `/pipeline:ship` …" (delivered by R1).
      `docs/ROADMAP.md` → Stage 6: tick the first item (`- [ ]` → `- [x]`; the link to this
      spec is already there). `docs/DECISIONS.md`: confirm the 2026-09-23 prompt-style row
      is present (added with the SPEC) — no edit. In `tests/test_documents.py`, after
      `test_roadmap_ticks_the_translation` and in its style (`# SPEC 009, AC10: …`), add:
      `test_conventions_state_the_prompt_style` (the `## Language` section of
      `docs/CONVENTIONS.md` names `test_prompt_style.py` and "normal volume"),
      `test_decisions_record_the_prompt_style` (a `docs/DECISIONS.md` row contains
      "SPEC 009" and "normal volume"), `test_backlog_drops_the_idea_chaining_item`
      (`docs/BACKLOG.md` no longer contains "`idea` must not start `/pipeline:ship`") and
      `test_roadmap_ticks_the_prompt_audit` (exactly one roadmap item contains
      `specs/009-prompt-audit-for-opus-5-5/SPEC.md`, and it starts with `- [x]`). Commit:
      `docs: record the prompt style and tick the audit (SPEC 009)`.
      files: `docs/CONVENTIONS.md`, `docs/BACKLOG.md`, `docs/ROADMAP.md`,
      `tests/test_documents.py`
      Automatic verification: `uv run pytest tests/test_documents.py -q` and `bash scripts/check.sh`

## Risks and traps

- **A P1 commit that is not only case.** Hand-editing forty spots invites a stray word
  change or a re-wrap. The lower-cased `diff` in steps 7–14 catches both; do not re-wrap
  lines in P1 (a shorter word leaves the line shorter, which is fine).
- **The tests of steps 1–6 vs P1.** P1 later lowers words near the pinned passages. The
  loop assertions (step 3) compare lower-cased text; the P2, P3, S2 and R1 texts contain no
  emphasis, so P1 does not touch them. Run `plugin/tests/test_prompt_audit.py` in every P1
  step (it is part of `uv run pytest plugin/tests`).
- **Pinned blocks.** The stage contract fence and escalation triggers in `ship` and the
  four agents, and the configuration/language/section-map blocks in six skills, must stay
  character-identical; none of them has emphasis, so no step edits them.
- **The eval receipt (AC9).** Its fingerprint covers `plugin/`, so it must be produced
  after the last change to `plugin/` — including any final-review fix. A red case is
  re-run alone with `--case` first; `plan-review-escalates-on-dependency` has a known
  flakiness (backlog P2 Evals). The spend ceiling is $10 (Owner decisions): pass
  `--max-cost-usd` accordingly. A `--case` re-run overwrites the receipt with a one-case
  result that still reads green — only a full-suite receipt is committed (Manual
  scenario 1).
- **Literal reading of R1.** The second R1 bullet names `(assumption)` only; the guardrail
  above it already extends the suffix to its Polish twin from the section map, so the
  verbatim audit text is kept rather than reworded.
- **CONVENTIONS still shouts.** `docs/CONVENTIONS.md` has capitals of its own (e.g. "BEFORE
  or TOGETHER"); project documents are out of this SPEC's scope and are not edited beyond
  the new bullet.

## End-to-end verification

### Automatic (performed by /pipeline:implement)

The change is prompt text; there is no running application. The end-to-end check is the
full verification plus the commit-shape checks:

1. `bash scripts/check.sh` — green (validate --strict when `claude` is on PATH, ruff,
   black, pytest over `plugin/tests` and `tests`).
2. AC8 — `git log --format=%s origin/main..HEAD` lists one commit each ending in `(P2)`,
   `(P3)`, `(S1)`, `(S2)`, `(S3)`, `(R1)` and eight ending in `(P1)` (plan, plan-review,
   implement, final-review, idea, init, ship, implementer).
3. AC2 over the whole P1 series — for every commit whose subject ends in `(P1)`:

   ```bash
   for c in $(git log --format=%H --grep='(P1)$' origin/main..HEAD); do
     for f in $(git diff-tree --no-commit-id --name-only -r "$c" | grep -v '^specs/'); do
       diff <(git show "$c^:$f" | tr '[:upper:]' '[:lower:]') <(git show "$c:$f" | tr '[:upper:]' '[:lower:]') \
         || echo "non-case change in $c $f"
     done
   done
   ```

   No output expected.
4. The step 15 merge-base scan — a non-empty result (the check fails on the pre-audit
   text).

Record the results in this section when done.

### Manual (performed by the owner)

1. **AC9, after the PR is open, on the owner's explicit command** (Owner decisions): run
   `bash scripts/eval.sh` (full suite, default model, with `--max-cost-usd` within the $10
   spend), confirm every case green, and commit `plugin/evals/last-run.json` on the PR
   branch (the agent may do the run and the commit once the owner commands it). A red case
   is re-run alone with `--case <name>` first; a regression is traced to its finding's
   commit and fixed on the branch. `eval.sh` writes `plugin/evals/last-run.json` on every
   run, so a `--case` run overwrites the full-suite receipt with a one-case receipt that
   is green and fingerprint-matching yet proves nothing about the other cases: never
   commit it — restore the file (`git checkout -- plugin/evals/last-run.json`). The
   committed receipt comes only from a full-suite run at the final branch head, with
   `cases_total` equal to the number of eval cases (9 today, as in the 0.6.0 receipt), so after a
   flake or a fix the full suite is run again. A full suite costs about $3.9 (the 0.6.0
   receipt), so the $10 ceiling covers two suites and one single-case re-run; if a further
   run is needed (e.g. the 5-run measurement of a failing case from the eval cost policy),
   stop and ask the owner before spending beyond $10. This cannot run in
   `/pipeline:implement`: it needs the owner's command and costs real money.

## Definition of Done

- [ ] all steps ticked
- [ ] `bash scripts/check.sh` fully green
- [ ] end-to-end verification (automatic) performed, result recorded here
- [ ] `docs/ROADMAP.md` updated; `docs/DECISIONS.md` / domain documents from the map
      in `CLAUDE.md`, if applicable
- [ ] spec status: `implemented`

## Owner decisions

_(appended by /pipeline:ship or a stage on escalation: date, stage, question, decision)_

## Review log

### 2026-09-24 — /pipeline:plan-review (under /pipeline:ship)

Anti-anchoring leads (from the SPEC alone): a scanner that goes red on the old text without
leaving the branch red; P1 edits that must not touch the pinned contract and configuration
blocks; sentence rewrites ordered before P1 so the P1 diffs stay case-only; `final-review`
has emphasis the audit's line list missed; the eval receipt as a manual, owner-gated step.
The plan matches all five.

Findings (severity counted before the fixes):

| Id | Severity | Finding | Change |
|----|----------|---------|--------|
| RV1 | `major` | Manual scenario 1 (AC9) says to re-run a red case alone with `--case`, but `scripts/eval.sh` rewrites `plugin/evals/last-run.json` on every run: a one-case run leaves a green, fingerprint-matching receipt for one case, which could be committed as the AC9 receipt. The spend split was not stated either. | Manual scenario 1 and the eval risk now say: never commit a `--case` receipt (restore the file), commit only a full-suite receipt from the final head with all 9 cases, re-run the full suite after a flake or fix, stop and ask before spending beyond $10. |
| RV2 | `minor` | AC10's documents parts had "review of the diff" as proof, while `tests/test_documents.py` pins the same kind of items per spec (SPEC 008, AC9). | Step 17 adds four document tests; the matrix names them. |
| RV3 | `minor` | The Allowlist paragraph listed `STATUS` and `E2E` as present outside code; `STATUS` is only inside the contract fence and `E2E` is not matched by `[A-Z]{3,}`. No effect on the allowlist. | Paragraph corrected. |
| RV4 | `minor` | The scanner strips code spans per line, so a code span wrapped across two lines in new text (P2, S2, R1) would expose its words to the scan. | Step 6 notes not to break a code span across lines. |

Checked and found sound (later stages need not repeat):

- Coverage: AC1–AC11 each have steps and a proving test or check; the matrix matches the
  steps. AC9 is correctly outside `/pipeline:implement` (owner's command, Owner decisions).
- Every capital word the plan lists per P1 step equals a simulation of the planned scanner
  over the current files (8 files with hits; `planner`, `plan-reviewer`, `reviewer` have
  none). Adding `final-review` to P1 is inside AC1, not a scope change.
- No test in `plugin/tests`, `tests` or the eval cases pins a capital word the audit
  lowers; the stage contract fences and the six configuration blocks contain no emphasis,
  so `test_stage_contract.py` and `test_stage_skills.py` stay green.
- The exact texts of P2, S2 and R1 match `AUDIT.md` → Action; the R1 insertion point
  exists in `idea/SKILL.md` → `## Guardrails`; the P3 paragraph and the S1/S3 targets are
  where the plan says.
- Ordering: no forward dependencies; the scanner commit last keeps every commit green and
  the merge-base scan proves the red state on the old text (AC1).
- The lower-cased diff (AC2) and the AC8 `git log` checks are runnable as written; the
  DECISIONS 2026-09-23 prompt-style row exists; version 0.6.1 → 0.7.0 is carried only in
  `plugin.json`; `test_readme.py` requires the `**consumer impact:**` line the plan adds.
- Owner summary: no new dependency, no data migration, one manual scenario — consistent
  with the SPEC's Owner decisions. Language: English, as `language: en`.

Decision: approved — no blocker, the one major is fixed in the plan itself, and no
dependency or migration is introduced, so the plan is ready for implementation.

## Deviations

_(filled in by /pipeline:implement — every deviation from the plan with its rationale)_

## Final review

_(filled in by /pipeline:final-review)_
